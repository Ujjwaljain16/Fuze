# ADR-005: Engine Contract Specifications & Input/Output Constraints

## Status
Accepted

## Context
Engines must be prevented from leaking infrastructure logic (raw SQL, Redis calls, Gemini SDK calls) into recommendation algorithms.

## Decision
1. **Engine Interface**:
   All recommendation engines inherit from `BaseRecommendationEngine` and implement `generate(request, candidates, scorer) -> EngineResult`.
2. **Allowed Input Boundaries**:
   - `RecommendationRequest` (Domain Entity)
   - `CandidateSet` (Aggregate)
   - `RecommendationScorer` (Pure Scoring Helper)
3. **Forbidden Input/Dependency Leakage**:
   - Repositories, SQLAlchemy sessions, `RedisCache`, `GeminiAnalyzer` SDK, Flask `request` object.

## Consequences
- Engines remain isolated, modular strategy implementations.
- Data fetching and caching stay strictly in `RecommendationDataLayer` and `RecommendationPipeline`.
