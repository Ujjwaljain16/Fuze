# ADR-001: Recommendation Domain Model & Bounded Contexts

## Status
Accepted

## Context
The legacy [`unified_recommendation_orchestrator.py`](file:///d:/Projects/fuze/backend/ml/unified_recommendation_orchestrator.py) combined database models, scoring math, AI prompt templates, and HTTP serialization into a single 3,092-line god object. To avoid creating smaller god objects during decomposition, explicit Domain-Driven Design (DDD) boundaries must be frozen.

## Decision
1. **Explicit Entities & Value Objects**:
   - Entities: `RecommendationRequest`, `RecommendationCandidate`, `RecommendationScore`, `RecommendationResult`.
   - Value Objects: `UserIntent`, `Embedding` ($D=384, \|v\|=1.0$), `ScoreBreakdown`, `ReasonTag`, `RecommendationExplanation`.
2. **Decoupled Explanation Context**:
   - `RecommendationExplanation` is separated from core scoring into a distinct bounded context (`ExplanationEngine`), allowing multi-provider LLM explanations (Gemini, OpenAI, Local LLM) without altering scoring math.
3. **Invariants**:
   - $\forall \text{score} \in \text{RecommendationScore}, \quad 0.0 \le \text{total\_score} \le 1.0$.
   - `candidate_id` and `content_type` MUST be non-empty.
   - Result list MUST be strictly sorted in descending order by `total_score`.

## Consequences
- Engine strategies operate strictly on Domain Entities and Value Objects.
- Scoring math is pure, deterministic, and testable without database or Redis mocks.
