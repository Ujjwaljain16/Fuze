# ML Platform Convergence Audit

**Branch Baseline**: `integration-review` (Tag: `pre-ml-convergence`)  
**Experiment Branch**: `architecture-shift`

---

## Executive Summary

While the **architectural refactoring** (Unit of Work, Repositories, Services, Domain Event Bus, Cache Invalidation, Distributed Locking, and Async Workers) has reached 100% convergence, the **ML Platform** exhibits a structural divergence between the two branches:

- **`integration-review`**: Operates on a production-tested, self-contained multi-strategy recommendation engine (`unified_recommendation_orchestrator.py`). It combines Content-Based Filtering, Interest Keyword Matching, Project Contextual Matching, and Gemini Reasoning with multi-tiered Redis caching and graceful fallback controls.
- **`architecture-shift`**: Attempted a modular multi-file OOP rewrite (`backend/ml/engines/`, `backend/ml/recommendation/`, `orchestrator.py`), breaking out recommendation strategies into separate engine classes and dataclass schemas.

---

## Detailed ML File Audit

| File / Component | Purpose | Used in `integration-review`? | Used in `architecture-shift`? | Production Path | Decision | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`unified_recommendation_orchestrator.py`** | Unified recommendation pipeline & caching | ✅ **YES** (Canonical engine) | ⚠️ Partial / Modified | Production Active | ✅ **KEEP `integration-review`** | Self-contained, multi-strategy engine with fallback degradation and robust Redis caching. Zero un-harvested dependencies. |
| **`orchestrator.py`** | Modular orchestrator wrapper | ❌ No | ✅ Yes | Abandoned | ❌ **REJECT** | Introduces extra wrapper layer over engine classes without performance gains. |
| **`engines/base.py`** | Base recommendation engine class | ❌ No | ✅ Yes | Abandoned | ❌ **REJECT** | Part of multi-file OOP rewrite; adds import overhead. |
| **`engines/context.py`** | Contextual recommendation engine | ❌ No | ✅ Yes | Abandoned | ❌ **REJECT** | Logic already integrated in `unified_recommendation_orchestrator.py`. |
| **`engines/keyword.py`** | Keyword recommendation engine | ❌ No | ✅ Yes | Abandoned | ❌ **REJECT** | Logic already integrated in `unified_recommendation_orchestrator.py`. |
| **`engines/semantic.py`** | Vector similarity engine | ❌ No | ✅ Yes | Abandoned | ❌ **REJECT** | Relies on Supabase RPC search primitives rejected in Phase 13. |
| **`recommendation/data_layer.py`** | Recommendation data fetcher | ❌ No | ✅ Yes | Abandoned | ❌ **REJECT** | Bypasses `RecommendationRepository` and `UnitOfWork` session isolation. |
| **`recommendation/re_ranker.py`** | Cross-encoder re-ranker | ❌ No | ✅ Yes | Abandoned | ❌ **REJECT** | High memory/CPU overhead; causes latency spikes on single-worker deployments. |
| **`recommendation/schemas.py`** | Dataclass schemas for recommendations | ❌ No | ✅ Yes | Abandoned | ❌ **REJECT** | Duplicates DTO schemas in `RecommendationService`. |
| **`intent_analysis_engine.py`** | Project intent extraction | ✅ **YES** | ✅ Yes | Production Active | ✅ **KEEP `integration-review`** | Wired into post-commit domain event handlers (`ProjectCreated`). |
| **`project_embedding_manager.py`** | Project vector embedding manager | ✅ **YES** | ✅ Yes | Production Active | ✅ **KEEP `integration-review`** | Manages project vector creation and updating. |
| **`universal_semantic_matcher.py`** | Universal semantic similarity score | ✅ **YES** | ✅ Yes | Production Active | ✅ **KEEP `integration-review`** | Active similarity calculation utility. |
| **`simple_ml_enhancer.py`** | Text analysis fallback enhancer | ✅ **YES** | ✅ Yes | Production Active | ✅ **KEEP `integration-review`** | Lightweight TF-IDF fallback enhancer. |

---

## ML Convergence Decision

**Final Status**: ✅ **ML Platform Fully Converged on `integration-review`**.

1. **Retain Monolithic Unified Pipeline**: `unified_recommendation_orchestrator.py` on `integration-review` remains the canonical ML engine. It is stable, robust against missing GPU/CPU libraries, and fully integrated with `RecommendationRepository` and Redis caching.
2. **Reject Modular Engine Rewrite**: The `backend/ml/engines/` and `backend/ml/recommendation/` subdirectories from `architecture-shift` are rejected to prevent architecture fragmentation and data-layer bypasses.
3. **Rollback Boundary**: The `pre-ml-convergence` tag serves as a clean snapshot marker.
