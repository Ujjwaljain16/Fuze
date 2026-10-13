# Operations

How to keep Fuze's data safe and its pipeline healthy in production.

## Repository secrets and variables

Add these under GitHub, Settings, Secrets and variables, Actions. A workflow whose required
secret is missing fails with an error naming it.

| Secret | Used by | Notes |
|---|---|---|
| `DATABASE_URL` | `db-keepalive.yml`, `backup-db.yml` | Supabase **session pooler** URI (`...pooler.supabase.com:5432`). GitHub runners have no IPv6, so the direct `db.<ref>.supabase.co` host is unreachable. The transaction pooler (port 6543) breaks `pg_dump`. |
| `BACKUP_PASSPHRASE` | `backup-db.yml`, `restore-drill.yml` | At least 20 characters, random. Keep a copy in a password manager: without it every backup is useless. After a rotation, older artifacts still need the old passphrase. |
| `BACKUP_DATABASE_URL` | `backup-db.yml` | Optional. Overrides `DATABASE_URL` for the dump only, e.g. when `DATABASE_URL` must stay on the transaction pooler. |
| `SUPABASE_URL` | `db-keepalive.yml` | Optional. `https://<project-ref>.supabase.co`. |
| `SUPABASE_ANON_KEY` | `db-keepalive.yml` | Optional. The anon (or publishable) key. It already ships in the frontend bundle. Without both Supabase secrets the REST ping is skipped. |
| `REDIS_URL` | `redis-keepalive.yml` | Upstash `rediss://` URL. |
| `HF_TOKEN` | `sync-to-hf-space.yml` (required, write access), `uptime-monitor.yml` (optional) | The runtime API answers without a token while the Space is public. |
| `CODECOV_TOKEN` | `backend-ci.yml` | Optional. Coverage upload never fails the build. |
| `GITHUB_TOKEN` | all issue-reporting steps, `restore-drill.yml`, `keep-workflows-enabled.yml` | Provided automatically. Each job asks for only the permissions it needs (`issues: write`, `actions: read`/`write`). |

| Variable | Used by | Default |
|---|---|---|
| `HF_SPACE_URL` | `sync-to-hf-space.yml` smoke test, `uptime-monitor.yml` | `https://ujjwaljain16-fuze-backend.hf.space` |
| `SUPABASE_PG_MAJOR` | `restore-drill.yml` service image | `15`. Set it to `17` when Supabase upgrades the project. |
| `BACKUP_PG_DUMP_ARGS` | `backup-db.yml` | Empty. Extra `pg_dump` flags, e.g. `--schema=public` if Supabase-managed schemas ever fail to dump (`permission denied`). |

These are **not** GitHub secrets. No workflow reads them; they belong to the hosts:

- Hugging Face Space secrets: `SENTRY_DSN` (optional), plus the app's own `DATABASE_URL`,
  `REDIS_URL`, `SECRET_KEY`, `JWT_SECRET_KEY` and the rest listed in `docs/DEPLOYMENT.md`.
- Vercel environment variables (read at build time): `VITE_SENTRY_DSN`, `VITE_ENVIRONMENT`,
  and optionally `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT` for source map uploads.

## Backups

Supabase takes daily backups on paid plans only, so `backup-db.yml` takes our own every night
at 02:30 UTC (and on demand from the Actions tab):

- `pg_dump --format=custom --no-owner --no-privileges` of the whole database, using the
  pg17 client (`pgvector/pgvector:pg17`). That client can dump Supabase on Postgres 15 or 17.
- Piped straight into `gpg --symmetric --cipher-algo AES256` with `BACKUP_PASSPHRASE`.
  **Anyone signed in to GitHub can download a public repository's artifacts**, so only the
  encrypted file is kept. The dump holds users' saved content, password hashes and encrypted
  Gemini keys.
- Before upload, the job checks that the file decrypts and lists as a pg_dump archive with
  `alembic_version` data. It is kept as the artifact `fuze-db-backup` (`fuze-db.dump.gpg` +
  `SHA256SUMS`) for **30 days**. A failed night opens or updates an issue.
- Before a migration that drops or rewrites data, run the workflow by hand first. For anything
  older than 30 days, download an artifact and keep it somewhere else (it stays encrypted).

## Restoring from a backup artifact

You need `gh`, `gpg`, Docker and the backup passphrase.

```bash
# 1. Pick a backup and download it (or use the Artifacts box on the run's page).
gh run list --workflow backup-db.yml --status success --limit 10
gh run download <run-id> --name fuze-db-backup --dir backup
(cd backup && sha256sum --check SHA256SUMS)

# 2. Decrypt (gpg asks for BACKUP_PASSPHRASE). Delete fuze.dump when you are done.
gpg --output fuze.dump --decrypt backup/fuze-db.dump.gpg

# 3. Look inside: server version, objects, row data present.
docker run --rm -v "$PWD:/work" pgvector/pgvector:pg17 pg_restore --list /work/fuze.dump | less
# Which schema the dump expects pgvector in ("public" or Supabase's "extensions"):
docker run --rm -v "$PWD:/work" pgvector/pgvector:pg17 \
  sh -c 'pg_restore --schema-only --file - /work/fuze.dump | grep -m1 -oE "[a-z_]+\.vector\("'
```

To restore into a Supabase project (a fresh one, or the old one after a disaster):

```bash
# 4. In the target database, enable pgvector in the schema found above (SQL editor):
#      create extension if not exists vector with schema extensions;   -- or: schema public
# 5. Restore the application schema. Supabase's own schemas (auth, storage, ...) already
#    exist in every project and are not restored. --clean replaces existing app tables.
docker run --rm -e TARGET_URL -v "$PWD:/work" pgvector/pgvector:pg17 \
  sh -c 'pg_restore --dbname "$TARGET_URL" --schema=public --no-owner --no-privileges --clean --if-exists /work/fuze.dump'
# 6. A new project grants its API roles access to new tables by default. Take it back again
#    (what migration 0013 did); RLS without policies already hides the rows:
#      revoke all on all tables in schema public from anon, authenticated;
#      revoke all on all sequences in schema public from anon, authenticated;
# 7. Point DATABASE_URL at it (HF Space secret and the GitHub secret) and restart the Space.
#    start.sh runs `alembic upgrade head`, and /health/readiness reports "schema": "current".
```

Set `TARGET_URL` to the target's session-pooler URI in your shell first, and use the pg17
client: a pg_restore older than the pg_dump can't read the archive. When restoring into
Postgres 15 with that client, one `unrecognized configuration parameter "transaction_timeout"`
error is expected and harmless.

## Restore drill

A backup you have never restored is a hope, not a backup. `restore-drill.yml` runs every
Sunday at 05:00 UTC (and on demand). It:

- downloads the newest successful `backup-db.yml` artifact and fails if it is more than 72
  hours old;
- verifies the checksum, decrypts it, and restores the `public` schema into a
  `pgvector/pgvector:pg15` service container (`SUPABASE_PG_MAJOR`), creating pgvector where
  the dump expects it;
- fails on any `pg_restore` error other than the harmless `transaction_timeout` one;
- requires `alembic current` to equal the repository's head;
- requires `alembic_version`, `users`, `projects`, `saved_content`, `tasks` and
  `bookmark_events` to exist (row counts go to the job summary), and `users` to be non-empty.

A failure opens or updates the issue "Weekly restore drill is failing". If a migration shipped
after the newest backup was taken, the head check fails until the next night's backup. Run
`backup-db.yml` and then the drill by hand to clear it.

## Migrations

- `start.sh` runs `alembic upgrade head` on every boot and refuses to start if it fails. Each
  revision runs in its own transaction, so a failure leaves the database at the last good revision.
- `/health/readiness` returns 503 until the database is at the head this build expects.
- Every revision has a working downgrade except 0001 (it would drop every table). CI checks that
  `downgrade 0001` followed by `upgrade head` lands on exactly the schema in `models.py`.
- To roll back a bad release: deploy the previous image, then `alembic downgrade <its head>`.
  If data was destroyed, restore a backup instead.

## Database connections

Production reaches Postgres through the Supabase session pooler. In session mode every connection
in an app pool holds one pooler connection, and the pooler caps connections per database (the
"Pool Size" under Database settings → Connection pooling; it depends on the compute size). Each
process has its own SQLAlchemy pool, so the worst case is:

```
total = Σ over processes (pool_size + max_overflow)  must stay below the pooler's pool size
```

| Process (`supervisord.conf`)         | Count | Settings (defaults)                                  | Connections |
|--------------------------------------|-------|------------------------------------------------------|-------------|
| gunicorn workers (`gunicorn.conf.py`) | 2     | `DB_POOL_SIZE` 5 + `DB_MAX_OVERFLOW` 5               | 2 × 10 = 20 |
| RQ workers (`rq_worker`, `rq_worker_high`) | 2 | `DB_WORKER_POOL_SIZE` 2 + `DB_WORKER_MAX_OVERFLOW` 1 | 2 × 3 = 6   |
| **Total**                            |       |                                                      | **26**      |

- `backend/worker.py` sets `FUZE_PROCESS_ROLE=worker`, which selects the `DB_WORKER_*` pair; every
  other process uses the web pair. `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` never size worker pools.
- RQ runs each job in a forked work horse with its own copy of the pool, so while a job runs a
  worker program can hold up to twice its pool (the reconciler thread in the parent plus the horse).
  Budget `2 × 3` per RQ program if the margin is thin: 20 + 12 = 32.
- Migrations at boot use a separate, short-lived connection (`NullPool`); scripts run by hand
  (`scripts/*.py`) open their own pool too.
- If the total exceeds the pooler's limit, lower the settings (for example `DB_POOL_SIZE=3`,
  `DB_MAX_OVERFLOW=2` gives 2 × 5 = 10 for the web workers) rather than adding gunicorn or RQ
  processes. A request that can't get a connection waits `DB_POOL_TIMEOUT` (20 s) and then fails.

## Pipeline health

- Bookmarks move through `scrape_status` and `embedding_status`. Anything stuck is picked up by the
  reconciler in the default RQ worker every 5 minutes (see `services/pipeline_reconciler.py`).
- Once a day the same loop deletes `bookmark_events` rows older than `BOOKMARK_EVENTS_RETENTION_DAYS`
  (default 30, `0` keeps them forever), 5000 rows per statement.
- `GET /api/health/queue` (with `X-Internal-Token: $INTERNAL_HEALTH_TOKEN`) shows queue depth,
  failed jobs and active workers.
- Useful queries:

```sql
-- what the pipeline is waiting on
select scrape_status, embedding_status, count(*) from saved_content group by 1, 2 order by 3 desc;
-- fetches that gave up
select id, url, scraped_at from saved_content where scrape_status in ('FAILED_FETCH', 'BLOCKED', 'DISALLOWED');
```

## Embedding model

The Docker image ships with `BAAI/bge-small-en-v1.5` in `HF_HOME=/app/.cache/huggingface`, and
runs with `HF_HUB_OFFLINE=1`, so containers never download a model. If you change
`EMBEDDING_MODEL_NAME` or set `SEARCH_RERANK_ENABLED=true`, add that model to the download step in
the `Dockerfile` (or run with `HF_HUB_OFFLINE=0`). Otherwise it fails to load: embedding work raises
`EmbeddingUnavailable` and bookmarks stay unembedded, and the reranker stays off. There is no silent
fallback, because vectors from another model would sit next to real ones and break every
similarity score. Hash vectors are used only when `DISABLE_EMBEDDINGS=true` opts into them for
local development.

## LLM provider (Gemini or OpenAI-compatible)

By default every LLM call goes to Google Gemini with the user's own key (or a shared system key
within a daily allowance). A free Gemini key can be as small as 20 requests a day, which a bulk
import uses up in minutes. Fuze reads Google's "retry in 6h52m" answer and stops calling that key
until it resets (`core/gemini_quota.py`); the analysis simply waits.

For a deployment that should not depend on per-user Gemini keys, set an OpenAI-compatible provider
(CloseRouter, OpenRouter, a local server):

| Variable | Meaning |
|---|---|
| `LLM_PROVIDER` | `openai_compat` turns it on; anything else (default `gemini`) leaves Gemini |
| `LLM_BASE_URL` | e.g. `https://api.closerouter.dev/v1` (https only, `http://localhost` allowed) |
| `LLM_API_KEY` | the provider key; set it as a host secret, never in git |
| `LLM_MODEL` / `LLM_FALLBACK_MODEL` | model ids as the provider names them; the fallback is tried on a 404 |
| `LLM_JSON_MODE` | `true` sends `response_format: json_object` (not every model accepts it) |
| `LLM_MAX_TOKENS` | output budget per call, default 4096. Models that think first spend 500-700 hidden tokens of it, so a limit near 1024 cuts replies off |

With it on, all analysis, Ask, intent and explanation calls use it, users are not asked for a Gemini
key, and the cooldown applies to the provider key: a 429 (using `Retry-After`) or a 402 (empty
balance) pauses calls instead of failing every bookmark. Users' page text is sent to the provider,
so use one you trust with it. A partly set configuration (a missing URL, key or model) is reported
at startup and Fuze stays on Gemini.

## Error tracking (Sentry)

Both halves report to Sentry only when a DSN is configured. Without one, nothing is imported or sent.

- **Backend.** Set `SENTRY_DSN` as a *Space secret* on Hugging Face (Settings, Variables and
  secrets), not a GitHub secret. `core/sentry_setup.py` initialises sentry-sdk in the web
  process (`run_production.py`, tag `component=web`) and in every RQ worker process (`worker.py`,
  `component=worker`), with the Flask, RQ and SQLAlchemy integrations.
  - Environment: `APP_ENV` (`core.app_env.app_env()`).
  - Release: `GIT_SHA` if set, otherwise `backend/RELEASE`. HF can't take build args from the
    sync, so `sync-to-hf-space.yml` writes the deployed commit SHA there on each deploy that
    changes code. Without either, events carry no release.
  - Privacy: `send_default_pii=False`, so there are no request bodies, user IPs or RQ job
    arguments. `Authorization`, `Cookie`, `Set-Cookie`, `X-Api-Key`, `X-Internal-Token` and
    `X-CSRF-Token` are replaced with `[Filtered]` in every event and transaction, in any letter case.
  - `SENTRY_TRACES_SAMPLE_RATE` (default `0.1`) sets performance tracing.
- **Frontend.** `frontend/src/main.jsx` calls `Sentry.init` only when `VITE_SENTRY_DSN` is set,
  with `VITE_ENVIRONMENT` as the environment (default `production`). Session replay masks all
  text and blocks media, and `Authorization` is filtered. Vite inlines these at build time, so
  set them in the Vercel project's environment variables and redeploy.
  - The CSP in `frontend/vercel.json` allows `*.ingest.sentry.io` and `*.ingest.us.sentry.io`
    only. A DSN in another region (for example `ingest.de.sentry.io`) needs its host added to `connect-src`.
  - `vite.config.js` uploads source maps only when `SENTRY_AUTH_TOKEN`, `SENTRY_ORG` and
    `SENTRY_PROJECT` are set at build time. The build sets `sourcemap: false`, so stack traces
    stay minified until that is turned on.
- Tests never report: `tests/conftest.py` removes `SENTRY_DSN` before the app is imported.

## Redis command budget

Upstash's free plan allows 500,000 commands a month and then rejects every command until the month rolls
over ("max requests limit exceeded"). That is about 16,000 a day, so anything that polls is expensive.

What used to use it: RQ's scheduler woke every second per worker (two commands each time, about 170,000 a
day for each one that held a queue's lock), and the pipeline reconciler asked Redis four questions about
every stuck bookmark on every five-minute pass (over 100,000 a day with a backlog and the Gemini key out of
quota). Now:

- No RQ scheduler. The reconciler's pass moves due retries back onto their queues
  (`move_due_retries`), so retries can be late by up to one interval (5 minutes). `worker.py` and
  `scripts/windows_test_worker.py` start workers without one.
- The reconciler reads all attempt counters with one `MGET` and asks about a job or a user only for a
  bookmark that is actually due. A pass over 150 stuck bookmarks costs under 10 commands
  (`test_an_idle_pass_over_a_big_backlog_costs_a_handful_of_redis_commands`).
- Workers renew their idle registration every 30 minutes instead of every 7.

Check the rate with a read-only sampler (it sees every client: Space, workers, your laptop):

```
python scripts/redis_usage.py --seconds 300
```

It prints commands a day, the monthly projection against the limit and the top commands. With nobody using
the app it should project well under 100,000 a month. Local runs share the production Redis, so a worker
left running on your laptop counts too: stop it when you are not testing.

## Keeping the free tiers alive

Every production service is on a free tier that is paused, archived or put to sleep when idle.
Each failing keep-alive opens (or comments on) a GitHub issue, since nobody watches scheduled runs.

| Service | Inactivity limit | What keeps it alive |
|---|---|---|
| Supabase Postgres | Paused after about 7 days of low activity. Restore it from the dashboard; a warning email arrives a week before. | `db-keepalive.yml` every 6 hours: a SQL `SELECT 1` through `DATABASE_URL`, plus a request to `$SUPABASE_URL/rest/v1/` with the anon key, so the API gateway sees traffic too (any 2xx/401/403/404 counts; skipped if the two secrets are unset). The nightly backup also reads the whole database. |
| Upstash Redis | Archived after 14 days without commands (older Upstash docs said 30). Upstash keeps a backup, but you get a new database and must update `REDIS_URL`. | `redis-keepalive.yml` daily `PING`. The workers are deliberately quiet (see the Redis command budget below). |
| Hugging Face Space (cpu-basic) | Sleeps after 48 hours without HTTP traffic (the runtime API's `gcTimeout`), and the next request wakes it after a cold start. A *paused* Space (paused by you, or by HF) never wakes on requests. | `uptime-monitor.yml` requests `/health/readiness` every 30 minutes. It reports a paused Space separately, with HF's reason. |
| GitHub scheduled workflows | In a public repository, every `schedule:` trigger is disabled silently after 60 days with no repository activity. That would stop all of the above. | `keep-workflows-enabled.yml` on the 1st and 15th of each month re-enables every scheduled workflow (itself included) with `PUT /repos/{owner}/{repo}/actions/workflows/{id}/enable`. |

Why the API call is enough for GitHub's 60-day rule: re-enabling a workflow resets its
inactivity timer. [liskin/gh-workflow-keepalive](https://github.com/liskin/gh-workflow-keepalive)
is built on exactly that call, so no third-party action and no dummy commits are needed.
`gautamkrishnar/keepalive-workflow`, the older dummy-commit action, has been disabled by GitHub
staff and can't be used. The job runs twice a month, so even after one failed run the next
attempt comes about 30 days before the deadline. Workflows disabled *manually* (state `disabled_manually`) are left alone.
The timer reset can't be tested in less than 60 days, so the job opens an issue if an enable
call fails. If a workflow does get disabled anyway, re-enable it from the Actions tab (or
`gh workflow enable <file>`) and run `keep-workflows-enabled.yml` by hand.

The repository is public, so Actions minutes are free. If it ever goes private, the 30-minute
uptime check alone uses about 1,500 of the 2,000 free minutes a month: slow it down.

## Secrets

Production refuses to start unless `SECRET_KEY` and `JWT_SECRET_KEY` are set, at least 16
characters and not a known default. `API_KEY_ENCRYPTION_KEY` is optional; when set it gets the same
checks. Rotating `JWT_SECRET_KEY` signs everyone out.

Users' Gemini keys are stored encrypted. Without `API_KEY_ENCRYPTION_KEY` the encryption key is
derived from `SECRET_KEY`, so rotating `SECRET_KEY` makes every stored key undecryptable and users
must re-enter them. To make `SECRET_KEY` rotatable:

1. Set `API_KEY_ENCRYPTION_KEY` (a new random value of 16+ characters) and deploy, keeping
   `SECRET_KEY` unchanged. New keys are encrypted with it. Existing keys still decrypt with the
   `SECRET_KEY`-derived key and are re-encrypted with the new one the next time they are used.
2. Move the keys nobody has used yet: from `backend/`, with the production environment,
   `python scripts/reencrypt_api_keys.py`. It prints how many were re-encrypted and how many could
   not be decrypted. Safe to re-run.
3. Rotate `SECRET_KEY`.

`API_KEY_ENCRYPTION_KEY` itself cannot be rotated this way: changing or losing it makes the keys
encrypted with it undecryptable.
