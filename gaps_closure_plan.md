# Gaps Closure Plan — Decisions, Not Options

This replaces the "what do you think?" framing in `gaps.md` with actual calls.
Philosophy behind every decision below: **ship what's reversible and testable
now; isolate what's genuinely risky (schema/data migrations, image-permission
changes, major dependency bumps) into its own verified cycle; don't scale the
architecture ahead of real traffic data.** Fuze today is one small Postgres +
one small Redis + a 2-vCPU container — the right move at this scale is
correctness and defense-in-depth, not premature horizontal scaling.

Status legend: ✅ done this pass · 🔜 next deploy cycle · 📅 scheduled, not
blocking · ⏸ deliberately not doing.

---

## Phase 0 — done in this pass (code-only, test-covered, zero infra risk)

**1. Fernet key derivation (gaps.md #3) → Option A+B hybrid, implemented.** ✅

Old: `Fernet(SHA256(SECRET_KEY))` — no KDF, no context separation from other
`SECRET_KEY` uses. Decision: **HKDF-SHA256 with a fixed `info` string
(`"fuze-api-key-encryption-v1"`) as the primary key, old SHA256 key kept as a
read-only fallback.** `backend/services/multi_user_api_manager.py`:
- `encrypt_api_key` always writes with the new HKDF key.
- `decrypt_api_key` tries the new key first, falls back to the legacy key.
- `get_user_api_key`'s DB-lookup path now **opportunistically re-encrypts**
  any value it had to decrypt with the legacy key, saving it back under the
  new key immediately. No forced migration script, no downtime, no batch job
  — every key converges to the new scheme the next time its owning user's
  recommendation path touches it, and anything genuinely dead just keeps
  working via the legacy fallback indefinitely.

Why this beat plain Option C ("do nothing"): the fix is small, fully
backward-compatible, and removes the actual weakness (no KDF, no context
separation) at zero migration cost — there's no reason to accept a known
weakness when the safe fix is this cheap. Why not full Option B (versioned
`key_version` field): over-engineering for two key generations; the
try-new-then-legacy fallback *is* a de facto 2-version scheme without a new
DB column.

**2. Three dead recommendation endpoints (gaps.md #13) → removed.** ✅

`/api/recommendations/unified`, `/unified-project/<id>`, `/project/<id>` all
called `get_unified_engine()`, which imports a module
(`unified_recommendation_engine`) that doesn't exist anywhere in the repo —
guaranteed 500 on every call, confirmed zero callers in `frontend/` or
`BookmarkExtension/` via grep. Decision was always going to be removal (dead,
unowned, untested public API surface is a liability, not an asset) —
executed rather than re-flagged.

**3. Dead Playwright fallback in `dynamic_fetcher.py` (gaps.md #14) → removed.** ✅

Confirmed the Playwright browser binary is never installed in the Dockerfile
(`playwright install chromium` never runs — pip only installs the Python
package). That fallback branch has therefore never once succeeded in the
deployed container; every call fell through to `StealthFetcher` anyway.
Decision: **remove**, not "pay ~300MB+ image size to fix a fallback of a
fallback." Camoufox (Scrapling's primary path, already working) covers
dynamic rendering; StealthFetcher remains as the one real fallback.

All three verified against the existing test suite (198 backend tests) —
see verification note at the end of this document.

---

## Phase 1 — next deploy cycle (needs a real Docker build + smoke test to ship)

**4. Non-root container user (gaps.md #8) → yes, do it, but not blind.** 🔜

Decision is yes: running gunicorn + both RQ workers as root in
`supervisord.conf` removes a layer of defense-in-depth against exactly the
threat model this app has (Camoufox/Playwright parsing arbitrary HTML from
user-supplied bookmark URLs — if that stack ever has an RCE, root-in-container
turns it into full container compromise instead of a contained one).

Why this isn't in Phase 0 with the others: it's not purely a code change. It
touches file ownership across `/app` and — critically — the camoufox browser
cache is fetched into `/root/.cache/camoufox` in the Dockerfile's builder
stage. Switching to a non-root `USER` changes `$HOME`, which changes where
camoufox looks for that cache; get this wrong and every scrape silently falls
back to a broken or re-downloading browser instead of the one already baked
into the image. This is exactly the kind of thing that looks safe in a code
review and breaks in the running container — the same category of bug as the
missing `alembic.ini` and the `mcp`/`playwright` resolution failure found
earlier this session, both of which were invisible until a real `docker
build` was run.

**Concrete plan for next session with Docker Desktop up:**
```dockerfile
# in the runtime stage, after all COPYs, before HEALTHCHECK/CMD
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /home/appuser/.cache \
    && cp -r /root/.cache/camoufox /home/appuser/.cache/camoufox \
    && chown -R appuser:appuser /app /home/appuser
USER appuser
ENV HOME=/home/appuser
```
Also drop `user=root` from `supervisord.conf`'s `[supervisord]` section (port
7860 is unprivileged, no capability needed to bind it). Then: real `docker
build .`, `docker run` it, hit `/health/liveness`, and actually trigger one
scrape to confirm camoufox still resolves its cache — that last check is the
one code review can't substitute for. Ship only after that passes.

**5. Retest the 2-gunicorn-worker config under load (gaps.md #6/#13).** 🔜

The Phase 3 load test that found and fixed the Redis-pool-exhaustion mass
logout ran against the *old* 1-worker config; the bump to 2 workers (matching
the Space's confirmed 2-vCPU `cpu-basic` tier) was never independently
retested. Decision: re-run `scripts/locustfile.py` at the same 25/75
concurrent-user tiers against the 2-worker build (can piggyback on the same
Docker build session as item 4) before calling this "verified." Expectation
going in: 2 workers should roughly halve the 75-user median-latency
degradation seen in the original test (2-5s), since CPU-bound work now has
two processes instead of one — but "should" isn't "confirmed," so confirm it.

---

## Phase 2 — architecture changes to a working feature (needs its own PR, not a drive-by)

**6. Synchronous Gemini call on the recommendation path (gaps.md #4) → move to async precompute + cache.** 📅

Decision: **don't leave this inline, and don't just add a timeout band-aid —
precompute intent analysis asynchronously.**
- New RQ job, keyed on a hash of the content being analyzed (title + description
  + technologies + user_interests, same inputs `intent_analysis_engine.py`
  already uses), writes its result to Redis with a long TTL (e.g. 24h).
- `unified_recommendation_orchestrator.py`'s call site
  (line ~2473) changes from "call Gemini inline, block until it returns" to
  "read cache; on hit, use it; on miss, enqueue the RQ job and proceed
  immediately using the existing non-LLM heuristic path for *this* request."
  The next request with the same context hash gets the LLM-enhanced result
  from cache — no request ever blocks on Gemini again.
- Why this over a client-side timeout: a timeout just changes *how often* you
  eat a 1-3s stall, and under a timeout you still throw away a slow-but-would-
  have-succeeded Gemini call. Precompute-and-cache removes the dependency
  from the request path entirely, which is the actually-correct fix for "an
  external API's latency/availability shouldn't gate our response time" —
  the same principle already applied to cache invalidation and content
  analysis earlier this session.
- Scope note: this is real, scoped work (one new RQ job type, one cache read/
  write, one branch in the orchestrator) — not a rewrite. Estimate: half a day
  including tests.

**7. LinkedIn batch-extract, ~7.5 min worst case (gaps.md #5) → convert to RQ job + polling.** 📅

Decision: **yes, do the RQ-job-with-polling redesign**, matching the pattern
`bookmark_processing_service.py` already uses (this session's own async-
cache-invalidation and content-analysis fixes prove the pattern is sound and
already load-bearing elsewhere in this codebase). Concretely:
- `POST /api/linkedin/batch-extract` becomes: validate the up-to-10 URLs,
  enqueue one RQ job per URL (or one job that processes all 10 with the
  existing 3-strategy/15s-timeout logic unchanged internally), return
  `202 {job_ids: [...]}` immediately.
- New `GET /api/linkedin/batch-extract/status?job_ids=...` polls RQ job
  status/results, same shape as how bookmark processing status is already
  surfaced.
- Frontend polls every ~2s until all jobs report `finished`/`failed`.
- This is a genuine feature-parity change (nothing about strategy count,
  timeout, or the 5/min rate limit changes) — just moves it off the
  synchronous request path, so it's safe to ship independently of any other
  Phase 2 item.

---

## Phase 3 — scheduled maintenance, explicitly not blocking anything above

**8. torch 2.7.1 / transformers 4.53.0 major-version CVE fixes (gaps.md #10).** 📅
Decision: bump in a **dedicated cycle with a before/after embedding-output
diff**, not opportunistically. Plan: pin the new versions in a branch, rerun
the golden-dataset MRR/NDCG@10 regression suite that already exists for
recommendation quality, and diff a fixed sample of embedding vectors
before/after (cosine similarity should be ~1.0 for identical inputs if the
model's numerical behavior didn't meaningfully shift). Ship only if both
checks pass. Not urgent enough to block current deploys — these are
inference-time CVEs in a model-serving library the app fully controls the
inputs to (no untrusted user data reaches torch directly), not a network-
facing attack surface.

**9. `react-router-dom` v6→v7 (gaps.md #10).** 📅
Decision: schedule as its own migration PR (it fixes a real moderate
open-redirect, but v7's API changes — data routers, changed lazy-loading
patterns — mean a mechanical version bump risks silently breaking navigation).
Not blocking: the actual open-redirect surface it patches is already closed
at the application layer by this session's `getSafeInternalRedirect()` fix
(Phase item in `gaps.md` §12), so the CVE is defense-in-depth, not an open hole.

**10. `vite` 4→8 / `vitest` ecosystem major bump (gaps.md #10).** 📅
Decision: schedule, low priority. Both vulnerabilities are dev-server-only
(arbitrary requests to `vite dev`, `vitest --ui`) — real risk only to a
developer's machine on an untrusted network, never shipped to end users.
Bundle with item 9's test cycle since both touch the frontend toolchain.

**11. `pytest` 8→9 (gaps.md #10).** 📅
Decision: piggyback on whichever of the above lands first. Dev-only, trivial,
no urgency on its own.

---

## Infra / outside code — decided posture, not deferred indefinitely

**12. HF Space "Flagged as abusive" (gaps.md #1) → appeal, but don't gate "production-ready" on it.** 📅
Decision: keep the support-ticket appeal alive (cheap, no downside, and the
technical blockers genuinely are fixed and CI-verified now) — but **stop
treating HF Spaces' opaque, unappealable-on-a-timeline moderation flag as the
production target.** A moderation decision entirely outside our control is a
single point of failure no amount of code quality fixes it. Recommended
concrete next step: stand up the same Docker image (this repo already builds
it correctly end-to-end, verified) on a small VPS — Hetzner CX22 (~€4/mo,
2vCPU/4GB, comfortably fits this workload) or Fly.io's free/hobby tier are
both good fits for a Flask+gunicorn+Postgres-external+Redis-external app —
and point the frontend's API base URL there. Keep the HF Space around as a
free mirror if/when the flag clears; don't wait on it to call this project
deployed.

**13. Container root user → same as item 4 above** (cross-referenced, not a
separate decision).

**14. DB connection pool sizing (gaps.md #7) → no action, monitoring only.** ⏸
With the unbounded-query fixes already shipped this session, 5+10 overflow
is very likely adequate at current scale. Decision: don't touch it
speculatively — watch for `QueuePool timeout` in logs during the Phase 1
retest (item 5) and raise it only if that actually shows up. Tuning a number
with no evidence it's wrong is exactly the kind of premature optimization
this plan is trying to avoid elsewhere.

**15. `start.sh` soft-fail migration behavior → leave as-is.** ⏸
Already a considered tradeoff (serve on a possibly-stale-but-compatible
schema rather than crash-loop on one bad migration). Revisit only if a real
migration failure is ever observed in production logs — no change to make
today.

---

## What this plan deliberately does *not* add

No new caching layer, no read replica, no message broker beyond the existing
Redis+RQ, no move off Flask/gunicorn, no Kubernetes. At current traffic (a
personal/early-stage bookmark tool, single small Postgres instance) every one
of those would be solving a scaling problem that doesn't exist yet at the
cost of operational complexity that very much does. The correct "scalability"
work at this stage is what's actually in this plan: bounded queries (already
done), connection pool headroom (verify, don't guess), no synchronous external
calls on hot paths (Phase 2), and a deployment target that isn't a single
opaque moderation flag away from being offline (item 12). Revisit the bigger
infrastructure question if/when real usage data says otherwise — not before.

---

## Verification note

Phase 0 changes (Fernet HKDF migration, dead-endpoint removal, dead
Playwright-fallback removal) were run against the existing 198-test backend
suite before being considered done — see the immediately preceding
conversation turn for the pass/fail result.
