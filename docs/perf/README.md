# Performance measurements

Raw results are the JSON files here. Live runs come from `scripts/bench_live.py` (30 samples per endpoint,
run by the owner against the deployed Hugging Face Space from India; the network floor is the
`/health/liveness` p50, which touches no database). `readonly-bench.json` holds read-only measurements
of the production database and the Space's own latency to it.

## Live API, p50 / p95 in milliseconds

| Endpoint | Baseline | After round-trip reduction (run 1) | (run 2, next day) |
|---|---|---|---|
| Network floor, no DB | 314 / 421 | 311 / 333 | 297 / 617 |
| Bookmark list (cached) | 317 / 1756 | 319 / 3604 | 359 / 1635 |
| Dashboard summary (cached) | 318 / 432 | 315 / 391 | 306 / 424 |
| Keyword search | 1239 / 1347 | 1031 / 3540 | 1032 / 3294 |
| **Semantic search** | **3026 / 3915** | **2104 / 2569** | **2154 / 2604** |

Semantic search: p50 **-29%**, p95 **-34%**, reproduced in two runs. Cause: the search made 7 SQL statements
plus a connection ping, `BEGIN` and `ROLLBACK`, each costing one round trip; it now makes 3 statements, and the
ping happens only on idle connections. The code change: commits cc04bd3 and e170404.

## Why it is still ~2 s

The Space measures **213-228 ms** to the database (Supabase, Singapore) and **2-3.5 ms** to Redis
(`GET /health/readiness?timing=1`). Five round trips at 215 ms is about 1.1 s of the 2.1 s. Postgres itself
answers a vector search in a median of 25 ms and a keyword search in 5 ms (HNSW and GIN indexes used in
10/10 queries). Moving the database next to the backend is the fix: [../REGION_MOVE.md](../REGION_MOVE.md).

## Retrieval quality

See `backend/eval/results/` (BEIR SciFact through the production search code): nDCG@10 0.718, p95 31 ms
retrieval inside Postgres; passage-level retrieval scores 0.504 against 0.016 for whole-document embedding on
long documents.
