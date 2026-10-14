# Performance measurements

Raw results are the JSON files here. Live runs come from `scripts/bench_live.py` (30 samples per endpoint),
run against the deployed Hugging Face Space from India; the network floor is the `/health/liveness` p50, which
touches no database. Since run 4 each result also carries the server's own breakdown (`server`: `total`, `embed`,
`db`, SQL statement count) from the `X-Server-Timing: 1` request header, as medians over the samples.
`readonly-bench.json` holds read-only measurements of the production database and the Space's latency to it.

## Live API, p50 / p95 in milliseconds

| Endpoint | 0 baseline | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| Network floor, no DB | 314 / 421 | 311 / 333 | 297 / 617 | 311 / 423 | 277 / 415 | 305 / 384 | 307 / 509 | 282 / 356 |
| Bookmark list (cached) | 317 / 1756 | 319 / 3604 | 359 / 1635 | 316 / 3573 | 263 / 1503 | 327 / 1231 | 1176 / 1474 (*) | 300 / 1521 |
| Dashboard summary (cached) | 318 / 432 | 315 / 391 | 306 / 424 | 305 / 454 | 286 / 446 | 313 / 441 | 1869 / 2240 (*) | 297 / 483 |
| Keyword search | 1239 / 1347 | 1031 / 3540 | 1032 / 3294 | 983 / 1320 | 991 / 1464 | 952 / 1185 | 948 / 3170 | 968 / 1352 |
| **Semantic search** | **3026 / 3915** | 2104 / 2569 | 2154 / 2604 | 2209 / 2605 | 2167 / 4310 | 1833 / 2302 | **1661 / 2071** | **1686 / 2656** |
| SQL statements per semantic search | about 7 + ping, BEGIN, ROLLBACK | 3 | 3 | 3 | 2 | 1 | 1 | 1 |

What each run measured:

- **0** is the baseline before any optimization (`baseline-before-optimizations-live-bench-*.json`).
- **1-3** are after the round-trip reduction (commits cc04bd3, e170404): the search made 7 SQL statements plus a
  connection ping, `BEGIN` and `ROLLBACK`, each costing one round trip; it now makes 3 and pings only idle
  connections.
- **4** is after the vector-search settings were made database defaults (`hnsw.iterative_scan`, `hnsw.ef_search`,
  migrations 0015-0018) so a search no longer sends a settings statement. On Supabase the pooler kept reusing
  database connections that started before the migration, so the defaults did not apply yet: still 2 statements.
- **5** is after the stale pooled connections were recycled: 1 statement per search.
- **6** is the same code, but **(\*)** it ran while the Redis plan's monthly command quota was exhausted, so the
  cache layer was down and the "cached" endpoints went to the database. Ignore those two cells; they are not a
  regression of the cache.

- **7** is after the Redis quota problem was fixed and the passage text was trimmed to 700 characters in SQL
  (41-54 KB returned instead of 60-140 KB). The cached endpoints are back at the network floor (300 and 297 ms
  against 282). Semantic search did not move (1686 against 1661 ms; database time 1138 against 1122 ms for the
  same single statement), so returning less text did **not** remove the time. Its server-side `other` column in
  that file is computed over cache-miss samples only for the cached endpoints (a script bug, fixed afterwards).

Semantic search: p50 **-45%** (3026 to 1661 ms) and p95 **-47%** across the series.

## Where the time goes

Per semantic search (medians, run 7): server total 1388 ms, embedding 15 ms, database 1138 ms in **one** statement,
about 235 ms of other request handling. Postgres runs that statement in about 2 ms (`EXPLAIN (ANALYZE, BUFFERS)`:
HNSW index scan, about 1,000 buffers), and from a laptop the same statement takes about 60 ms end to end. The
Space measures **213-228 ms** to the database (Supabase, Singapore; `GET /health/readiness?timing=1`, a trivial
`SELECT 1`) and **2-3.5 ms** to Redis. So one statement costs about **900 ms more** than a trivial one, and that
is not query execution.

What the runs rule out and what they do not:

- It is **not** the SQL statement count (already 1), the embedding (15 ms), or the amount of passage text:
  returning 41-54 KB instead of 60-140 KB left the database time at 1138 ms against 1122 ms.
- Statement cost grows with the statement: bookmark list about 340 ms per statement, keyword search 458 ms for one
  small statement, the semantic search 1138 ms. Cost per statement is therefore not a constant round trip.
- Not yet tested: whether the cost scales with result size at all on this path (time `SELECT repeat('x', n)` of
  1, 10 and 50 KB from the Space), and whether it is spent in the pooler (Supavisor, session mode) or in the
  network between regions.

The likely fix either way is the one in [../REGION_MOVE.md](../REGION_MOVE.md): move the database next to the
backend, which removes distance for every statement whatever the cause.

## Retrieval quality

See `backend/eval/results/` (BEIR SciFact through the production search code): nDCG@10 0.718, p95 31 ms
retrieval inside Postgres; passage-level retrieval scores 0.504 against 0.016 for whole-document embedding on
long documents.
