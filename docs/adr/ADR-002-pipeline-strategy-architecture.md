# ADR-002: Pipeline + Strategy Hybrid Architecture

## Status
Accepted

## Context
The recommendation system needs to support multiple scoring strategies (Context-Aware, Vector-Hybrid, Quality Ensemble) while enforcing consistent caching, metrics, and fallback behavior across requests.

## Decision
1. **Hybrid Architecture**:
   - Use the **Pipeline Pattern** for standard request execution stages:
     `Cache Lookup → Candidate Retrieval → Engine Strategy Scoring → Ensemble Ranking → Context Enrichment → Cache Persistence`.
   - Use the **Strategy Pattern** for recommendation algorithm selection (`ContextEngine`, `SmartEngine`, `QualityEnsembleEngine`).
2. **Anti-God Pipeline Rules**:
   - `RecommendationPipeline` MAY: Coordinate lifecycle stages, route strategies, manage Redis cache, record metrics, trigger circuit breaker fallbacks.
   - `RecommendationPipeline` FORBIDDEN from: Vector cosine similarity math, raw DB queries, BM25 scoring, Gemini LLM prompt formatting.

## Consequences
- Engine strategies can be added, benchmarked, or swapped independently.
- The pipeline coordinator remains lightweight and focused strictly on lifecycle orchestration.
