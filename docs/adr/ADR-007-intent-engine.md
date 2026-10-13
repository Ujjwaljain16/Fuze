# ADR-007: Intent x content recommendation engine

## Status

Accepted. Implemented in `backend/ml/intent_engine/`; how it works today is in
[RECOMMENDATIONS.md](../RECOMMENDATIONS.md).

## Context

The previous recommendation stack had these properties:

- **One embedding per bookmark.** The model reads about 256 tokens, so only the title and the first
  ~200 words of a page were searchable. On a long-document benchmark the first-pass search scored an
  nDCG@10 of 0.016 (bge-small) and 0.001 (MiniLM) (`backend/eval/results/scifact_long8_*`).
- **Ranking by rules.** A weighted sum of a semantic score and rule-based scores (technology lists, word-based
  content-type rules, intent classified into enums with a keyword fallback), a ~3,000-line orchestrator, and a
  second "shadow" pipeline that ran beside it. Behaviour was hard to test and to explain.

## Decision

Replace the stack with one engine that works on meaning only:

1. **Store passages, not one vector.** Split saved text into overlapping chunks, embed each, and also embed a
   validated Gemini content profile (what the item teaches and when it is useful). Both live in
   `content_chunks`, indexed with HNSW, and every vector records its embedding model.
2. **Intent from the user's own words.** Compose the query and the project, task and subtask text into the
   intent. A Gemini intent statement and information needs are computed in a background job, cached, and used
   to add query vectors; a request never waits for them and there is no rule-based fallback.
3. **Rank by retrieval, then diversify.** Nearest chunks per query vector with a per-user filter (pgvector
   iterative scan), an optional cross-encoder rerank behind `SEARCH_RERANK_ENABLED`, then MMR. Explain a result
   by the passage that matched.
4. **Shared retrieval.** Search uses the same passage retrieval (`services/hybrid_search.py`) with the query as the
   intent.
5. **Choose the embedding model by benchmark.** `BAAI/bge-small-en-v1.5` over `all-MiniLM-L6-v2` and
   `e5-small-v2` (all 384 dimensions, so no schema change).
6. **Remove the legacy code** instead of keeping it behind flags (commit 4446a9a removed about 7,200 lines).

Measured on BEIR SciFact (test split, 300 queries, nDCG@10; `backend/eval/results/`):

| | One vector per bookmark | Passages |
|---|---|---|
| bge-small, original documents | 0.713 | 0.718 |
| bge-small, long documents | 0.016 | 0.504 |
| MiniLM, original documents | 0.648 | 0.652 |
| MiniLM, long documents | 0.001 | 0.441 |

The ms-marco cross-encoder changed nDCG@10 by -0.008 (original) and +0.004 (long documents) while adding about
700 ms per query on CPU, so reranking stays off by default.

## Consequences

- Retrieval no longer sees only the start of a page; short documents score no worse.
- Results are explainable: each shows the passage that matched. Nothing in the ranking is a hand-set weight.
- Changing the embedding model means re-embedding (`scripts/reindex_content.py`). Until a bookmark is
  re-embedded it is missing from results for the new model; there is no fallback model, and an unloadable model
  makes embedding jobs fail and retry and search return 503.
- Each bookmark costs one Gemini call for its profile, and each new project, task or subtask context costs one
  for its intent statement. Both run in RQ jobs and wait when the user's key is out of quota.
- Feedback is stored per project (`user_feedback.project_id`) and exported as an evaluation set
  (`scripts/export_feedback_eval.py`); it does not yet tune ranking.
- The old endpoint and engine-status names (`/unified-orchestrator`, `unified_orchestrator_available`) remain
  because the frontend uses them.
