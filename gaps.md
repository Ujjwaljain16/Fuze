# Gaps — Needs Your Input

Tracking things found during the production-readiness audit (2026-09-15) that were
**not** fixed automatically, because they need a decision, credentials, or context
only you have. Everything else confirmed during the audit was fixed directly in
the code (see conversation / commit history for details).

**Scope honesty check:** the audit that produced items #3-#7 below covered specific
areas of `backend/` (auth/CORS/SSRF, DB query patterns + gevent concurrency,
background-job/SSE/scraper reliability) via 3 targeted agent passes + my own direct
reading, cross-verified by the existing test suite. It did **not** cover everything.
See §8 for what's still completely unaudited — don't read "audit done" as "codebase
proven correct."

---

## 1. HF Space restart is failing with a 503

**What happened:** clicking "Restart this Space" on
`huggingface.co/spaces/Ujjwaljain16/fuze-backend` returns:
```
503 — Something went wrong when restarting this Space.
Request ID: Root=1-6aa840f5-0f7ab0a30227e2f4360b22d9
```

**Why I can't diagnose this further myself:** the actual crash/build reason is in
the Space's private build+container logs, which only render in the HF UI when
you're logged in. I have no credentials to view them.

**Leading suspect:** the Space is still running the *old* code. One of the bugs
fixed this session was that `create_app()` ran `alembic upgrade head` from
*every* supervisord-launched process (gunicorn + 2 RQ workers) concurrently on
every boot — a real race (lock contention / duplicate-DDL errors) that could
crash-loop the container on startup. HF's restart endpoint returning a bare 503
instead of actually restarting is consistent with the container repeatedly
failing to come up.

**What I need from you:**
- Open the **Logs** tab on the Space (Build logs + Container logs) and check what's
  actually failing. Paste the relevant error back if it's unclear.
- Decide whether to push the fixes from this session to the Space now (see #2
  below) — if the migration race is indeed the cause, deploying the fix should
  resolve it.

---

## 2. Nothing from this session has been pushed yet

All fixes are committed locally to `main` conceptually but **not yet committed
or pushed** — you hadn't confirmed you wanted that. Until you do, the live HF
Space and Vercel frontend are still running the old, buggier code (including the
CORS-bypass and make_response bugs).

**What I need from you:** say "commit and push" (or similar) when ready. Pushing
to `main` will trigger `.github/workflows/sync-to-hf-space.yml`, which copies
`backend/`, `Dockerfile`, etc. to the HF Space git repo and triggers a rebuild.

---

## 3. API-key Fernet encryption key derivation is weak, but fixing it live is risky

**File:** `backend/services/multi_user_api_manager.py:79-80`

Per-user Gemini API keys are encrypted with a Fernet key derived as
`SHA256(SECRET_KEY)`. Fernet itself is sound (random IV, HMAC-authenticated), but:
- the key has no KDF (HKDF/PBKDF2) and no context separation from other uses of
  `SECRET_KEY` (e.g. Flask session signing)
- rotating `SECRET_KEY` silently breaks decryption of every already-stored
  encrypted API key (falls back to the shared default `GEMINI_API_KEY`, not a
  crash, but a silent behavior change)

**Why I didn't fix it:** switching the derivation (e.g. to HKDF with a fixed
`info` string) makes all *already-encrypted* keys in the production DB
undecryptable, since the new code would derive a different key than what
encrypted them. Fixing this safely needs a migration plan:
- **Option A:** decrypt-with-old-key-on-read, re-encrypt-with-new-key-on-write,
  rolled out gradually (no downtime, no forced re-entry).
- **Option B:** versioned key derivation (store a `key_version` per encrypted
  value, support decrypting old versions indefinitely).
- **Option C:** simplest — do nothing now, since per-user Gemini keys aren't
  highly sensitive (scoped, revocable, not financial/PII), and just note it as a
  known limitation.

**What I need from you:** pick A, B, or C (or say "not a priority").

---

## 4. Synchronous Gemini call sits on the recommendation request path

**File:** `backend/ml/intent_analysis_engine.py:169-173`, called from
`unified_recommendation_orchestrator.py:2473`

Every cache-miss call to `/unified-orchestrator`, `/task/<id>`, `/subtask/<id>`
makes a live external LLM call *inline* in the request handler before content
fetching even starts. This isn't a bug — it's a product/latency tradeoff: it
directly ties that request's response time (and success) to Gemini's latency
(commonly 1-3s+) and availability.

**Options:**
- Leave as-is if 1-3s recommendation latency is acceptable.
- Pre-compute/cache intent analysis asynchronously (RQ job, keyed on a content
  hash) so the request path only ever reads a cached result.
- Add an aggressive client-side timeout with a fast heuristic fallback so a slow
  Gemini call can't dominate response time.

**What I need from you:** is current recommendation latency actually a problem
in practice? If yes, which option.

---

## 5. LinkedIn batch-extract can take up to ~7.5 minutes per request

**File:** `backend/blueprints/linkedin.py:280-307`

Batch extraction loops sequentially over up to 10 URLs; each goes through up to
3 scraping strategies sequentially with a 15s timeout each. Worst case is ~7.5
minutes for one HTTP request. gevent's cooperative model means this doesn't
freeze *other* users, but it's a bad UX/timeout profile for the calling client,
and the "5 per minute" rate limit doesn't prevent overlapping in-flight calls.

**Why I didn't fix it:** the real fix (run strategies concurrently with
short-circuit on first success, or move the whole batch to an RQ job with a
status-poll endpoint) is a meaningful architecture change to a working feature,
not a bug fix — didn't want to make that call unilaterally.

**What I need from you:** is this endpoint used in a way where 7-minute worst
case is actually hit/felt? If yes, I'd recommend the RQ-job-with-polling
approach (matches the pattern already used for bookmark processing).

---

## 6. gunicorn worker count (`--workers 1`) wasn't changed

**File:** `supervisord.conf:8`

Currently 1 gunicorn worker (gevent, 1000 connections) handles all HTTP traffic.
This is a single point of failure — any code path that escapes gevent's
cooperative model (a genuinely blocking call, an unpatched library) can freeze
*all* traffic until the 2000s timeout.

**Why I didn't change it:** the right worker count depends on the Space's actual
RAM (each worker that loads the SentenceTransformer model + other ML state adds
real memory pressure) and CPU allocation, which I don't know for your specific
HF Space tier. Blindly bumping to 2-3 workers without knowing available RAM
risks OOM-killing the container instead.

**What I need from you:** what's the Space's hardware tier (cpu-basic vs
upgraded)? I can size worker count properly once I know the RAM ceiling.

---

## 7. DB connection pool sizing (5 + 10 overflow) — likely fine now, but unverified under real load

**File:** `backend/run_production.py` (`SQLALCHEMY_ENGINE_OPTIONS`)

This was flagged as a potential bottleneck *combined with* the unbounded
queries (#5/#6 from the audit, now fixed — see recommendations.py and
unified_recommendation_orchestrator.py). With those queries capped, 15 total
connections is probably adequate, but this wasn't load-tested.

**What I need from you:** nothing urgent — just flagging that if you run the
Locust load test (`scripts/locustfile.py`) or the benchmark script
(`scripts/benchmark_internal.py`) you already had in progress, watch for
`QueuePool timeout` errors specifically, which would indicate this needs
raising.

---

## 8. Confirmed, unfixed, found while answering "is it really prod-ready now?"

**Containers run as root.** `supervisord.conf:2` has `user=root` — gunicorn and
both RQ workers all run as root inside the container. Not exploitable on its own,
but it removes a layer of defense-in-depth: if a dependency in the scraping stack
(Playwright/Camoufox parsing arbitrary HTML from user-supplied bookmark URLs)
ever has an RCE, root-in-container is strictly worse than a dropped-privilege
user. Fix is mechanical (add a non-root `USER` in the Dockerfile + adjust file
ownership) but touches the whole runtime image, so I flagged rather than changed
it blind.

**What I need from you:** OK to add a non-root user to the Docker image? (Low
risk, but worth a deploy+smoke-test cycle since it changes file permissions
throughout `/app`.)

---

## 9. Areas never audited this session at all

Listed so "audit done" isn't mistaken for "everything's been checked":

- **Frontend** (`frontend/`, React/Vite) and the **Chrome extension**
  (`BookmarkExtension/`) — zero review. Given the git history shows real
  frontend auth bugs already fixed (401 loops, token sync, OAuth callback
  issues), this is not a low-risk area to leave unchecked.
- `blueprints/tasks.py`, `projects.py`, `profile.py`, `feedback.py`,
  `search.py`, `dashboard.py` — only touched incidentally, not systematically
  reviewed the way `bookmarks.py`/`recommendations.py`/`linkedin.py`/`events.py`
  were.
- `ml/engines/*` and most of `services/*` beyond what came up during the
  reliability pass.
- The Alembic migration files themselves (`backend/alembic/versions/`) — never
  checked for schema drift against `models.py` or for irreversible/unsafe
  migration patterns.
- **No dependency vulnerability scan.** `requirements.txt` was never run through
  `pip-audit` or `safety` — there could be packages with known CVEs.
- **No real load test.** The audit reasoned about scaling architecturally
  (gevent concurrency model, connection pool sizing, query patterns); nothing
  was actually load-tested. `scripts/locustfile.py` still only hits
  `/api/health` as a placeholder.
- All verification this session ran against **SQLite in-memory**, not real
  Postgres+pgvector — Postgres-specific behavior (JSONB columns, the raw DDL in
  `ensure_pipeline_columns`/`ensure_token_families_table`, real connection
  concurrency) was reasoned about, not exercised.
- No CI security-scanning gate, no dependency pinning/lockfile beyond
  `requirements.txt`, no measured test coverage number.

**What I need from you:** which of these matters most to tackle next? My
suggested order if you want to keep going: (1) frontend auth flow audit, given
the history of real bugs there, (2) `pip-audit` run (cheap, fast, high
signal-to-noise), (3) wire the Locust script to real heavy endpoints and
actually run it against a staging-like environment.

**Update 2026-09-15 (later same day):** items (1) and (2) are now in progress/done
— see §10 and §11.

---

## 10. Dependency vulnerability scan — done, most fixed, two deliberately deferred

Ran `pip-audit` on `requirements.txt` (117 known CVEs across 17 packages) and
`npm audit` on `frontend/` (32 vulnerabilities). Fixed what's safe, left what
needs a dedicated cycle:

**Backend — upgraded to patched versions (verified: full 198-test suite +
app-boot smoke test pass after the bump):**
`click` 8.2.1→8.3.3, `filelock` 3.18.0→3.20.3, `Flask` 3.1.1→3.1.3, `h2`
4.2.0→4.4.1, `idna` 3.10→3.15, `lxml` 6.0.0→6.1.1, `lxml_html_clean`
0.4.2→0.4.5, `pillow` 11.3.0→12.3.0, `PyJWT` 2.10.1→2.13.0, `python-dotenv`
1.1.1→1.2.2, `requests` 2.32.4→2.33.0, `soupsieve` 2.7→2.8.4, `urllib3`
2.5.0→2.7.0, `Werkzeug` 3.1.3→3.1.6.

**Backend — deliberately NOT upgraded, needs your call:**
- `torch` 2.7.1 and `transformers` 4.53.0 have multiple CVEs with fixes only in
  major-version bumps (torch→2.8-2.13, transformers→5.x). These are tightly
  coupled to the pinned `sentence-transformers==5.0.0` embedding pipeline — a
  blind bump risks silently changing embedding output or breaking model
  loading, which would degrade recommendation quality without an obvious error.
  Needs a dedicated upgrade+re-benchmark cycle (compare embedding outputs
  before/after), not a drive-by version bump.
- `pytest` 8.3.4→9.0.3 is a major bump. Left alone since it's dev/test tooling
  only (not shipped to production) — low urgency, but flagging so it doesn't
  silently stay stale forever.

**Frontend — fixed via `npm audit fix` (no `--force`), verified: build +
21-test suite pass after:** resolved 23 of 32 vulnerabilities (rollup, tar, ws,
and others) via compatible in-range bumps.

**Frontend — deliberately NOT force-upgraded, needs your call:**
- `react-router-dom` 6.30.1→7.18.3 fixes a moderate-severity open-redirect bug,
  but v6→v7 is a real breaking API change for a routing library — needs an
  actual migration pass through the app's routes, not `--force`.
- `vite` 4.5.14→8.3.0 and the `vitest`/`@vitest/*` ecosystem →5.x fix a
  moderate dev-server-only vulnerability (arbitrary requests to the dev server)
  and a couple of critical-rated issues in `vitest`'s UI mode — but these are
  **build/test tooling, not shipped to end users' browsers**, so the actual
  production risk is low (mainly a threat to a developer's machine while running
  `npm run dev`/`vitest --ui` on an untrusted network). Still a real 4-major
  version jump for `vite`, needs its own test cycle.

**What I need from you:** OK to schedule the torch/transformers re-benchmark
and the react-router-dom v7 migration as their own follow-up work? They're
real fixes but not "quick and safe" like the rest.

---

## 11. Important caveat on all local test verification this session

The local `venv` used for every smoke test and `pytest` run this session is
**not a clean stand-in for the production Docker image** — `pip install`
surfaced dependency conflicts with packages like `google-meet-api`,
`llama-index-llms-gemini`, `mcp`, and `pinecone-plugin-assistant`, none of
which are in `requirements.txt` or the Dockerfile. This venv is a shared local
dev environment with extra tooling installed alongside this project's actual
dependencies.

Practically: everything I verified (198 backend tests, app boot, CORS/SSRF
behavior) almost certainly still holds in the real Docker build, since it only
exercises this project's own code against its own pinned versions — but the
*actual* production build has never been built and tested by me this session
(the Docker multi-stage build itself was never run locally, only reasoned
about from the Dockerfile).

**What I need from you:** if you want real confidence before your next deploy,
run `docker build .` locally (or let the HF Space rebuild do it) and watch for
build failures — the wheel-building stage (torch, camoufox fetch, etc.) is the
part most likely to behave differently in a truly clean environment than in my
already-populated local venv.

---

## 12. Phase 1 + Phase 2 (audit, then fix/verify) — done, all actionable findings fixed

Three more targeted agent audits ran, covering what §9 flagged as unaudited:
frontend auth/security, the six backend blueprints not covered in the first
pass, and `ml/engines/` + Alembic migrations. Every confirmed, actionable
finding was fixed and verified (198 backend tests + 21 frontend tests +
`vite build` all green after). No new items need your input from this batch —
listed here for the record, not because anything is still open:

**Frontend:**
- `javascript:`/`data:` URLs could be rendered as real `<a href>` links for
  bookmark/result URLs across 6 pages (Bookmarks, Dashboard, ProjectDetail,
  Recommendations, SaveContent, ShareHandler) — combined with the JWT living
  in `localStorage`, that's a stored-XSS-to-account-takeover path. Added
  `frontend/src/utils/urlSafety.js` (`getSafeHref`) and applied it at all 10
  call sites. (Backend already rejects `javascript:` server-side on bookmark
  creation via `security_middleware.py`'s XSS pattern check — confirmed, not
  a gap — this was purely a rendering-layer risk.)
- The SSE connection (`/api/realtime/stream`) authenticated via the raw JWT
  access token in the URL query string (EventSource can't send headers) —
  leaks into access logs/browser history for the token's full lifetime.
  Replaced with a short-lived (30s), single-use ticket: new
  `backend/utils/stream_tickets.py` + `POST /api/realtime/stream-ticket`
  (normal header-authenticated), frontend now mints a ticket before opening
  the EventSource instead of sending the real token.
- OAuth callback accepted tokens from the query string as well as the
  fragment (query-string tokens leak via Referer headers), and didn't scrub
  the URL on the error path. Now fragment-only, and `replaceState` runs
  unconditionally before any branching.
- **Update:** the `?redirect=` param turned out to be a real UX bug, not dead
  code — `Login.jsx` never read it, so sharing content while logged out sent
  the user through login and dumped them on `/dashboard`, silently losing the
  URL they were trying to save. Wired it up: `Login.jsx` now honors
  `?redirect=` after a successful login, through a new
  `getSafeInternalRedirect()` helper (in `urlSafety.js`) that only allows
  same-app relative paths — rejecting `/login?redirect=https://evil.tld` or
  `//evil.tld`-style open-redirect attempts, which matter here since a login
  link is exactly what someone would click from an email/DM without checking
  closely. Verified the existing `ShareHandler.jsx` nested-query-string
  construction (`redirect=/share?url=...`) actually parses correctly via
  `URLSearchParams` (confirmed in a standalone Node check, not just reasoned
  about) so no change was needed there. Not extended to the Google OAuth
  login path (`Login.jsx` → Supabase → `OAuthCallback.jsx` always lands on
  `/dashboard`) since carrying the redirect target through an external
  OAuth round-trip needs its own sessionStorage-based mechanism — a real but
  narrow gap (logged-out + share + specifically-Google-sign-in) not worth
  the added complexity today; flagging rather than fixing blind.
- Not fixed, informational only (no security impact): backend API base URL
  is hardcoded independently in 3 files (`api.js`, `background.js`,
  `popup.js`) instead of one shared config — a maintainability smell (risk of
  URL drift between them), not a bug.

**Remaining backend blueprints (tasks/projects/profile/feedback/search/dashboard):**
No IDOR issues found (every by-ID endpoint correctly checks ownership).
Fixed: unbounded task/subtask list queries (added defensive `.limit(500)` in
3 places); `change_password`/`set_password`/`update_username` had no
endpoint-specific rate limit (fell back to the generic 50/min default) despite
`change_password`/`set_password` re-verifying `current_password` as a
step-up control — added tight limits (`5 per 15 minutes` on the password
endpoints, matching `login`; `10 per hour` on username changes).

**ML engines + Alembic migrations:**
Fixed: `alembic/env.py` used an undefined `sa.text(...)` on every single
migration run (silently swallowed by a bare except — the statement-timeout
protection it was meant to provide had never actually worked); the
duplicate-cleanup `DELETE` in migration `0004` now logs exactly which row ids
and how many get deleted (doesn't change what's deleted — that already ran in
production — just makes it auditable going forward for fresh environments);
`ensure_case_insensitive_indexes()` in `models.py` now uses `CREATE UNIQUE
INDEX CONCURRENTLY` instead of a plain blocking index build; fixed a
`models.py`/migration schema-drift mismatch on `idx_saved_content_user_unanalyzed`
(model was missing the `WHERE extracted_text IS NOT NULL...` partial-index
clause that's actually in the DB, causing Alembic to see phantom drift);
`SmartEngine.generate()` now scores each candidate in its own try/except
instead of one bad candidate aborting the whole batch silently.

---

## 13. Phase 3 (real load test) — one severe bug found and fixed, confirmed with real traffic

Stood up a disposable, faithful replica of production: real Postgres+pgvector
and Redis (Docker containers), the actual `gunicorn --workers 1 --worker-class
gevent` command from `supervisord.conf` (not `flask run` -- gunicorn/gevent
don't run on Windows at all, so this required a Linux container), seeded 10
users x 40 bookmarks each, minted real JWTs (bypassing the login rate limiter,
which a shared-IP Locust run would otherwise just measure instead of real
throughput), and wired `scripts/locustfile.py` to the actual heavy endpoints
(`/api/bookmarks`, `/api/dashboard/summary`, `/api/search/text`,
`/api/search/semantic`, `/api/recommendations/unified-orchestrator`,
`/api/health`) with real auth.

**Found and fixed: Redis pool exhaustion cascaded into mass user logout under
load.** At 75 concurrent users, ~38% of authenticated requests started failing
with `401 Token has been revoked` -- for tokens that were never revoked. Root
cause: `run_production.py`'s `check_if_token_revoked` JWT-blocklist check
failed **closed** (`except Exception: return True`). The Redis client pool
(20 connections, shared by caching + rate limiting + this check) got exhausted
under concurrent load, so `.exists()` calls started throwing, and every
throw got treated as "yes, this token is revoked." Fixed to fail open (a
Redis hiccup should degrade revocation enforcement, not cause a mass outage)
and raised the pool to 50 connections. Re-tested at the same 75 users
afterward: **0 failures across 595 requests.**

**Found: three recommendation endpoints are permanently dead code.**
`/api/recommendations/unified`, `/unified-project/<id>`, and `/project/<id>`
all return 500 every single time -- `get_unified_engine()` imports a
top-level `unified_recommendation_engine` module that doesn't exist anywhere
in the codebase (superseded by `ml/unified_recommendation_orchestrator.py`,
used correctly by `/unified-orchestrator`, the only recommendation endpoint
the frontend actually calls -- confirmed via grep across `frontend/` and
`BookmarkExtension/`). Zero current user impact since nothing calls these,
but it's broken public API surface with zero test coverage that let it slip
through unnoticed.

**What I need from you:** remove these three dead endpoints, or reimplement
them against the working orchestrator? Given zero current usage, my lean is
removal, but that's your call.

**Honest performance numbers** (bounded by this laptop's constrained local
Docker VM -- ~3.8GB, shared CPU -- not the real HF Space hardware, so treat
the *shape* of the finding as transferable, not the exact numbers): at 25
concurrent users, all working endpoints stayed sub-100ms median with 0%
failures. At 75, median latency climbed to 2-5s -- consistent with the
single-gunicorn-worker architecture already flagged in §6, and part of why
§14 below bumps worker count.

**Also found and fixed while setting up the test environment** (surfaced by
actually running real infra for the first time this session, not something I
went looking for): Alembic's migration chain couldn't complete against a
genuinely fresh Postgres database (`assert self._transaction is not None`
inside `autocommit_block()`, migration `0003`'s `CREATE INDEX CONCURRENTLY`)
-- would have blocked disaster recovery or any new environment setup. Fixed
in `alembic/env.py` (run the whole migration connection under AUTOCOMMIT
isolation, and explicitly close out SQLAlchemy 2.0's "autobegin" transaction
before Alembic's own machinery takes over). This was later confirmed to be a
*live*, not theoretical, bug -- see §14.

---

## 14. Deployment hardening — two more critical, previously-undiscovered bugs found; several fixes applied

Reviewed `Dockerfile`, `supervisord.conf`, `start.sh`, and the CI workflows
end to end, and verified changes by actually building the real Docker image
(not just reading it) -- which is exactly how both critical bugs below were
found. Neither was visible from code review alone.

**CRITICAL, confirmed: `alembic.ini` was never copied into the Docker image.**
Neither the `Dockerfile` nor `sync-to-hf-space.yml` (which pushes files to the
HF Space's own git repo) ever copied `alembic.ini` -- only `backend/`,
`wsgi.py`, `app.py`, `start.sh`, `supervisord.conf`. Since `alembic.ini`'s own
`script_location = %(here)s/backend/alembic` requires the file to physically
exist at `/app` for Alembic to find the migrations directory at all, **every
`alembic upgrade head` invocation in `start.sh` has likely been silently
failing on every single container boot**, caught by its own `|| echo
"Warning: ... continuing startup..."` fallback. This means the automatic
migration step has probably never actually run in the deployed Space -- the
current production schema (at revision `0010`) almost certainly got there via
some other, out-of-band process (someone running `alembic upgrade head`
manually against the production `DATABASE_URL`). Fixed: `COPY alembic.ini .`
added to both the `Dockerfile` and `sync-to-hf-space.yml`.

**Direct consequence of the above fix, needs your attention on the next
deploy:** once this ships, `start.sh` will run **real migrations against
production for the first time**, on the next boot. All migrations in this
codebase use idempotent (`IF NOT EXISTS`) DDL, and I verified the full chain
(`0001`→`0010`) runs cleanly against a fresh Postgres end-to-end with the
`env.py` fix from §13 -- so this should be a fast no-op against an
already-migrated database. But "first real run against prod" is exactly the
kind of thing worth watching the deploy logs for, rather than assuming.

**CRITICAL, confirmed: the actual production `requirements.txt` could not be
resolved by pip at all**, independent of the `alembic.ini` bug. Two separate,
real conflicts, found by actually running `pip install -r requirements.txt`
fresh (not just reasoning about pins):
1. `scrapling[all]` depends on `mcp>=1.24.0` with no upper bound. Pip's
   resolver backtracked through dozens of `mcp`/`mcp-types` releases trying to
   reconcile it against the rest of the file -- confirmed to still be
   backtracking after several minutes with no end in sight (an
   effectively-hung install, not a fast, clean failure). Fixed by pinning
   `mcp==1.24.0` (scrapling's own declared floor), which collapsed resolution
   to seconds.
2. Our own pin `playwright==1.53.0` directly conflicts with
   `scrapling[fetchers]==0.3.14`'s requirement of `playwright==1.56.0` exactly
   -- a real `ResolutionImpossible`, not a backtracking issue. This likely
   explains the "Scrapling not installed" fallback warnings that showed up
   repeatedly throughout this session's local testing: the scrapling install
   may have been silently failing in every environment, all along. Fixed by
   bumping our pin to `playwright==1.56.0`.

After both fixes, verified `pip install --dry-run -r requirements.txt`
resolves the complete, unmodified file cleanly (exit 0, ~190 packages, no
backtracking). **Confirmed with a real, complete, unmodified `docker build .`
(not `--dry-run`, not a trimmed requirements set): both stages built
successfully end-to-end** -- builder stage 2.18GB, final runtime image
1.94GB, `alembic.ini` verified present via the build log's
`COPY alembic.ini .` step completing. **Before the `mcp`/`playwright` fixes,
this exact build failed after 428 seconds with `resolution-too-deep`** --
reproduced directly, not inferred. So: any attempt to rebuild the HF Space,
including the restart that hit the 503 earlier in this session, was doomed
regardless of every other fix here, until this landed.
(One loose end: I didn't get to `docker run` the final image to check
`/health/liveness` responds before Docker Desktop itself crashed under the
sustained build load on this machine -- worth a quick manual check after you
pull these changes, though a failed `HEALTHCHECK` command would only affect
container-restart behavior, not whether the app actually serves traffic.)

**Other hardening applied:**
- Added a Docker `HEALTHCHECK` (was entirely missing) -- checks
  `/health/liveness` (process alive, not DB/Redis reachability -- a transient
  external dependency blip shouldn't cause Docker to restart an otherwise-
  healthy container; that's what `/health/readiness` + orchestration-level
  traffic routing is for).
- Bumped `gunicorn --workers 1` → `--workers 2` in `supervisord.conf`,
  matching the HF Space's confirmed `cpu-basic` hardware (2 vCPU, verified via
  the Spaces API earlier this session). No `--preload`: each worker
  independently creates its own DB/Redis connections after fork, avoiding the
  documented gunicorn+gevent gotcha where preloading can leave forked workers
  sharing connection file descriptors that were never gevent-monkey-patched in
  that worker. **Not independently load-tested with 2 workers** this
  session (the Phase 3 rig only tested 1 worker) -- the change itself is a
  well-understood, standard default, but I'm flagging the gap in verification
  rather than implying it was benchmarked.
- Added `.github/workflows/docker-build.yml` -- actually builds the image in
  CI on changes to `Dockerfile`/`requirements.txt`/`backend/**`/etc., and
  asserts `alembic.ini` is present in the built image. This is the check that
  would have caught both critical bugs above automatically, before they ever
  reached production.
- Added a `.dockerignore` (was missing). Less critical than initially
  suspected -- BuildKit (Docker Desktop's default builder) already lazily
  transfers only what's actually referenced by `COPY` instructions, so the
  large untracked directories (`frontend/node_modules`, `venv/`, `.git/`)
  weren't being fully sent to the daemon regardless. Still good hygiene.
- Added a "verify production build" step (`npm run build`) to
  `frontend-ci.yml`. Previously only `css-lint.yml` ran the build check, and
  it only triggers on `*.css` file changes -- a JS/JSX-only change (exactly
  what `frontend-ci.yml` triggers on) could break the production build with
  no CI workflow ever noticing.
- Fixed a `$?`-checks-the-wrong-command bug in `db-keepalive.yml` and
  `redis-keepalive.yml`'s "Report status" steps -- `$?` inside a new
  `run:` block never reflects the previous step's exit code in GitHub
  Actions, so these always printed "✅ successful" regardless of whether the
  actual ping failed. (The job still correctly shows failed overall, since
  the ping step itself exits non-zero independently -- this only fixed the
  misleading per-step log message.)

**Confirmed real, deliberately not changed (needs your decision):**
- The Playwright fallback in `scrapers/fetchers/dynamic_fetcher.py` has
  likely never worked in the deployed container either: `playwright` the
  Python package is installed, but its browser binary
  (`playwright install chromium`) is never fetched anywhere in the
  Dockerfile -- Playwright manages browser binaries in a cache separate from
  pip. So `p.chromium.launch()` in that fallback path would always throw,
  silently falling through to the next fetcher. Two options, both real
  tradeoffs: (a) add `playwright install chromium` to the Dockerfile --
  makes the fallback actually work, at the cost of ~300MB+ more image size
  (the "camoufox bloat" you flagged, but for a different browser engine);
  (b) remove the Playwright fallback code entirely, since it's a dead,
  currently-inert code path anyway and camoufox (used by scrapling's
  primary `DynamicFetcher`/`StealthyFetcher` path) already covers dynamic
  rendering -- leaner image, no functional regression since it never
  actually worked. Your call.
- `start.sh`'s migration-failure handling (`|| echo "Warning: ...
  continuing startup..."`) still soft-fails rather than blocking container
  startup. I left this as-is: hard-failing risks turning one bad migration
  into a total outage/crash-loop, versus the current "serve on a possibly-
  stale-but-compatible schema" posture, which is a defensible tradeoff many
  production systems make deliberately. Worth revisiting once real
  migrations are actually running (per the note above) and you've seen how
  it behaves in practice.

---

## 15. Real benchmarks (`scripts/benchmark_internal.py`) wired up

Was a stub benchmarking the near-empty `project` table's embedding column
with a self-referential subquery that didn't reflect any real query the app
runs. Rewrote to use the actual production ANN query from
`backend/ml/recommendation/retrieval.py`'s `fetch_ann_candidates()` (cosine
distance via the HNSW index on `saved_content.embedding`, scoped to a real
user -- exactly how the recommendation pipeline queries it), plus the real
paginated bookmark-list query, real `embedding_utils.get_embedding()`
end-to-end latency (cache + model/fallback), and a Redis benchmark using a
realistic ~1.5KB payload size (a serialized bookmarks page) instead of an
arbitrary 1KB string. Now writes a `benchmark_results.json` file (timestamped,
p50/p95/p99) instead of only printing, so runs are comparable over time --
e.g. before/after an index change or a Postgres tier upgrade.
`scripts/locustfile.py` was already wired to real HTTP endpoints in Phase 3
(§13).

**Caveat:** unlike the Phase 3 Locust rig, I did not stand up a live
Postgres+Redis to actually run `benchmark_internal.py` end-to-end this
session (Docker Desktop crashed under load before I got to it -- see §16). It
imports the real `create_app()`/`get_embedding()`/query patterns and passed a
syntax check, but "compiles and imports cleanly" isn't the same as "produced
real numbers." Run it yourself once you have a target DB (`python
scripts/seed_loadtest_data.py` from Phase 3 already gives you seeded users +
embedded content to point `--user-id` at) to get the first real reading.

---

## 16. New HF Space creation — blocked on payment, reverted to reusing the existing Space

You asked me to create a new Space as a full production-backend replacement,
with the existing `fuze-backend` disabled once it worked. What happened:

1. Fetched `huggingface.co/new-space/agents.md` (HF's own agent-instructions
   page) to see how to do this programmatically. It described `hf auth
   login` (device-code flow) then `hf repo create`.
2. The installed `hf` CLI (huggingface_hub 0.35.1) didn't support the
   browser device-code flow the page described -- only `--token` (a
   Personal Access Token you generate yourself). I won't handle a raw token
   on your behalf, so I asked you to run `hf auth login` yourself in your
   own terminal; you did, and `hf auth whoami` confirmed `Ujjwaljain16`
   without me ever seeing the token.
3. `hf repo create fuze-backend-v2 --repo-type space --space_sdk docker`
   failed with **`402 Payment Required`**: Docker Spaces on free `cpu-basic`
   now require an HF PRO subscription (~$9/mo). This is a real HF platform
   policy, not something in our control -- the existing `fuze-backend` was
   presumably created before this policy took effect, or under different
   terms.
4. Asked you how to proceed (subscribe to PRO / switch to a free-tier demo
   SDK / reuse the existing Space). You chose to reuse the existing Space.

**Net effect:** no new Space was created (the 402 means nothing was ever
provisioned -- no cleanup needed). All the fixes in this session (§13's
migration race, §14's `alembic.ini` + `mcp`/`playwright` resolution fixes,
CORS, SSRF, the 401-cascade fix, etc.) apply to `fuze-backend` and are the
actual path to getting it working again.

**What I need from you:** nothing further on this specific item -- just
flagging that if you ever do want a genuinely separate full-backend Space
later (e.g., a staging environment), it'll need HF PRO, since Docker SDK is
a hard requirement for this architecture (Gradio/Streamlit/static can't run
Postgres/Redis/RQ workers).
