# ADR-004: Scoring Layer Isolation & Pure Function Boundaries

## Status
Accepted

## Context
Recommendation scoring algorithms (vector cosine similarity, BM25, tech stack matching, recency decay) were previously interspersed with database queries and Redis cache checks, making unit testing slow and fragile.

## Decision
1. **Pure Scorer Isolation**:
   - `RecommendationScorer` in [`backend/ml/recommendation/scorer.py`](file:///d:/Projects/fuze/backend/ml/recommendation/scorer.py) contains 100% pure functions.
2. **Zero Side Effects**:
   - Scorer functions may NOT perform database calls, Redis lookups, network requests, or global state mutations.
3. **Deterministic Evaluation**:
   - Inputs are raw candidate feature vectors and query parameters; outputs are numerical scores $[0.0, 1.0]$ and `ScoreBreakdown` objects.

## Consequences
- 100% unit test coverage for scoring math executing in <5ms without mocks.
