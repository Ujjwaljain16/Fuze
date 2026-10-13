# Optimizations

What exists in the code and what was measured. Raw measurements and the method are in
[perf/README.md](perf/README.md); the JSON files there are the source of every number below.

The backend runs on a Hugging Face Space and the database on Supabase in another region, so one SQL
statement costs one network round trip of roughly 215 ms (`perf/README.md`). Most of the work below
removes round trips.

## Semantic search: fewer database round trips

`POST /api/search/semantic` (`services/search_service.py`, `services/hybrid_search.py`).

| Change | Where |
|---|---|
| The HNSW settings (`hnsw.iterative_scan`, `hnsw.ef_search`) are database or role defaults (migrations `0015` to `0018`, for example `0015_ann_database_defaults` and `0017_ann_role_defaults`). Each new connection reads what it received (`ann_defaults`, in `run_production.py`, in the same round trip that sets `statement_timeout`), and a search sends the settings only if the connection lacks them. | `hybrid_search.configure_filtered_ann` |
| One statement returns the nearest passages, their bookmark's title, url, notes and date, and the not-yet-chunked bookmarks (`UNION ALL`, each branch `LIMIT`ed so HNSW still drives it). Reranking keeps the two-step path. | `hybrid_search.retrieve_with_unchunked` |
| Passage text is trimmed in SQL (`left(x.text, 700)`); the result list shows 300 characters, and 60 whole passages were 60-140 KB per search. | `hybrid_search._COMBINED_SQL` |
| Within one transaction, the settings statement is sent once, however many ANN queries follow. | `hybrid_search.configure_filtered_ann` |

A real search therefore sends **1** statement when the connection has the defaults and **2** (settings, then
the query) when it does not; it sent 7, then 3, before these changes. Both counts are asserted against a
real Postgres in `tests/test_ann_round_trips.py`. The effect of passage trimming on the Space has not been
measured (`perf/README.md`).

Measured on the deployed Space, 30 samples per endpoint, `POST /api/search/semantic` p50 / p95 in ms:

| Run (file in `docs/perf/`) | Statements | p50 / p95 |
|---|---|---|
| `baseline-before-optimizations-live-bench-20261012T225613Z.json` | 7 plus ping, BEGIN, ROLLBACK | 3026 / 3915 |
| `live-bench-20261012T233044Z.json` | 3 | 2104 / 2569 |
| `live-bench-20261013T184202Z.json` | 2 | 2167 / 4310 |
| `live-bench-20261013T185807Z.json` | 1 | 1833 / 2302 |
| `live-bench-20261013T191429Z.json` | 1 | 1661 / 2071 |

Across the series p50 fell 45% (3026 to 1661 ms) and p95 47% (`perf/README.md`).
The remaining time is mostly the database link; moving the database next to the backend is described in
[REGION_MOVE.md](REGION_MOVE.md).

## Connection pool

- **Ping only idle connections** (`utils/db_pool.py`). SQLAlchemy's `pool_pre_ping` sends `SELECT 1` on every
  checkout, a round trip per request. `install_idle_ping` pings a connection only after `DB_PING_IDLE_SECONDS`
  (default 15) of disuse and replaces it if the ping fails. With the idle ping on, `pool_pre_ping` is turned
  off in the engine options (`utils/unified_config.py`). `DB_PING_IDLE_SECONDS=0` restores a ping on every
  checkout. Tested in `tests/test_db_pool.py`.
- **Pool sizes** are per process and set by role: web workers default to `DB_POOL_SIZE=5`,
  `DB_MAX_OVERFLOW=5` (`utils/unified_config.py`, `.env.example`). The connection budget is in
  [OPERATIONS.md](OPERATIONS.md).
- **Cooperative DB waits.** The gunicorn workers use gevent, and `psycogreen` makes Postgres waits yield
  (`gunicorn.conf.py`), so a slow query does not block other requests in the same worker.

## Where a request's time goes

`core/server_timing.py` adds a `Server-Timing` header (`total`, `embed`, `db`, and `dbn`, the statement
count) when a request sends `X-Server-Timing: 1`. Ordinary requests get no header. `scripts/bench_live.py` (repository root)
records these values under `server` in the `docs/perf/live-bench-*.json` files from
`live-bench-20261013T184202Z.json` on; for example the semantic search in `live-bench-20261013T191429Z.json`
shows `embed` 2.0 ms and `db` 1122.5 ms of a 1358 ms request.

## Caching

- Redis caches are keyed in one place, `core/cache_keys.py`.
- Query embeddings are cached in Redis, keyed by model and text (`utils/embedding_utils.py`), which is why
  `embed` is about 2 ms in the timing above.
- The bookmark list is cached for 300 s, or 60 s for a search (`blueprints/bookmarks.py`); the dashboard
  summary for 30 s, in a versioned key (`blueprints/dashboard.py`).
- Redis calls on request paths use short socket timeouts, so a slow Redis cannot hang a request
  (`services/task_queue.py`, `middleware/rate_limiting.py`).
- The embedding model loads once per process; RQ workers load it before forking.

## Redis command budget

Upstash's free plan allows 500,000 commands a month. [OPERATIONS.md](OPERATIONS.md#redis-command-budget) has
the full account; the changes are:

- No RQ scheduler. The reconciler moves due retries back onto their queues (`move_due_retries` in
  `services/pipeline_reconciler.py`); retries can be late by up to one reconciler interval.
- The reconciler reads all attempt counters with one `MGET`. A pass over 150 stuck bookmarks costs under
  10 commands (`test_an_idle_pass_over_a_big_backlog_costs_a_handful_of_redis_commands` in
  `tests/test_pipeline_recovery.py`).
- Idle workers renew their registration every 30 minutes instead of every 7 (`worker.py`, `WORKER_TTL_SECONDS`).
- `scripts/redis_usage.py` samples the command rate without writing.

## Reranking is off by default

`SEARCH_RERANK_ENABLED=false`. On BEIR SciFact the cross-encoder changed nDCG@10 by -0.008 (short documents)
and +0.004 (long documents) at about 700 ms per query on CPU (`services/hybrid_search.py`,
`backend/eval/results/`).

## Frontend build

`frontend/vite.config.js` splits the production bundle into vendor chunks (`react-vendor`, `router-vendor`,
`axios-vendor`, `icons-vendor`) and page chunks (`dashboard`, `project-detail`, `recommendations`); most
pages are loaded with `React.lazy` in `src/App.jsx`. Source maps are off in production builds, CSS is
code-split, and the service worker version is injected at build time. Responses are compressed by
Flask-Compress. No bundle sizes or load times are published here because none were measured.
