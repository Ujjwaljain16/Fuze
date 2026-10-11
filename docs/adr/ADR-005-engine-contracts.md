# ADR-005: Engine Contract Specifications & Input/Output Constraints

## Status
Accepted, later superseded. The legacy recommendation stack this ADR governs was removed in commit 4446a9a and replaced by the intent x content engine ([design and benchmark](../INTENT_ENGINE_PLAN.md)). Kept as a record of the decision; the modules it names no longer exist.

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
