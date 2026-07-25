from unittest.mock import MagicMock, patch
import pytest
from ml.unified_recommendation_orchestrator import (
    UnifiedRecommendationOrchestrator,
    UnifiedRecommendationRequest,
    UnifiedRecommendationResult
)


def test_shadow_mode_execution_integration(monkeypatch):
    monkeypatch.setenv("RECOMMENDATION_SHADOW_MODE", "true")
    monkeypatch.setenv("RECOMMENDATION_PIPELINE_ENABLED", "false")

    orchestrator = UnifiedRecommendationOrchestrator()
    assert orchestrator.feature_shadow_enabled is True
    assert orchestrator.feature_pipeline_enabled is False

    mock_req = UnifiedRecommendationRequest(
        user_id=1,
        title="React 19 Hooks",
        description="State patterns",
        technologies="React"
    )

    # Mock legacy candidates return
    monkeypatch.setattr(orchestrator.data_layer, 'get_candidate_content', lambda user_id, req: [
        {
            'id': 101,
            'title': 'React 19 Hooks Guide',
            'url': 'http://example.com/react',
            'content_type': 'bookmark',
            'difficulty': 'intermediate',
            'technologies': ['React'],
            'key_concepts': ['React'],
            'quality_score': 8,
            'engine_used': 'context',
            'confidence': 0.9,
            'metadata': {}
        }
    ])

    results = orchestrator.get_recommendations(mock_req)
    assert len(results) >= 1
    assert results[0].id == 101


def test_pipeline_cutover_feature_flag(monkeypatch):
    monkeypatch.setenv("RECOMMENDATION_PIPELINE_ENABLED", "true")

    orchestrator = UnifiedRecommendationOrchestrator()
    assert orchestrator.feature_pipeline_enabled is True

    mock_req = UnifiedRecommendationRequest(
        user_id=1,
        title="PostgreSQL Indexing",
        description="B-tree and HNSW",
        technologies="PostgreSQL"
    )

    results = orchestrator.get_recommendations(mock_req)
    # Serves via RecommendationPipeline directly
    assert isinstance(results, list)
