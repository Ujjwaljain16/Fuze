# Performance measurements

Raw results are the JSON files here. Live runs come from `scripts/bench_live.py` (30 samples per endpoint),
run against the deployed Hugging Face Space from India; the network floor is the `/health/liveness` p50, which
touches no database. Since run 4 each result also carries the server's own breakdown (`server`: `total`, `embed`,
`db`, SQL statement count) from the `X-Server-Timing: 1` request header, as medians over the samples.
`readonly-bench.json` holds read-only measurements of the production database and the Space's latency to it.

## Live API, p50 / p95 in milliseconds

| Endpoint | 0 baseline | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| Network floor, no DB | 314 / 421 | 311 / 333 | 297 / 617 | 311 / 423 | 277 / 415 | 305 / 384 | 307 / 509 |
| Bookmark list (cached) | 317 / 1756 | 319 / 3604 | 359 / 1635 | 316 / 3573 | 263 / 1503 | 327 / 1231 | 1176 / 1474 (*) |
| Dashboard summary (cached) | 318 / 432 | 315 / 391 | 306 / 424 | 305 / 454 | 286 / 446 | 313 / 441 | 1869 / 2240 (*) |
| Keyword search | 1239 / 1347 | 1031 / 3540 | 1032 / 3294 | 983 / 1320 | 991 / 1464 | 952 / 1185 | 948 / 3170 |
| **Semantic search** | **3026 / 3915** | 2104 / 2569 | 2154 / 2604 | 2209 / 2605 | 2167 / 4310 | 1833 / 2302 | **1661 / 2071** |
| SQL statements per semantic search | about 7 + ping, BEGIN, ROLLBACK | 3 | 3 | 3 | 2 | 1 | 1 |

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

Semantic search: p50 **-45%** (3026 to 1661 ms) and p95 **-47%** across the series.

## Where the time goes

For run 6 the server reports, per semantic search (medians): total 1358 ms, embedding 2 ms, database 1122 ms in
one statement. Postgres runs that statement in about 2 ms (`EXPLAIN (ANALYZE, BUFFERS)`: HNSW index scan, about 1,000
buffers), so the remaining ~1.1 s is distance and data transfer between the Space and the database, not query
cost. The Space measures **213-228 ms** to the database (Supabase, Singapore) and **2-3.5 ms** to Redis
(`GET /health/readiness?timing=1`). Each search returned 60-140 KB, about 90% of it passage text of which the
result list shows 300 characters; the combined statement now returns the first 700 characters of each passage
(41-54 KB), which has not been measured on the Space yet. Moving the database next to the backend is the larger
fix: [../REGION_MOVE.md](../REGION_MOVE.md).

## Retrieval quality

See `backend/eval/results/` (BEIR SciFact through the production search code): nDCG@10 0.718, p95 31 ms
retrieval inside Postgres; passage-level retrieval scores 0.504 against 0.016 for whole-document embedding on
long documents.
