from unittest.mock import MagicMock
import pytest
from ml.recommendation.domain import (
    RecommendationRequest,
    RecommendationCandidate,
    CandidateSet
)
from ml.recommendation.pipeline import RecommendationPipeline


def test_recommendation_pipeline_lifecycle():
    mock_data_layer = MagicMock()
    req = RecommendationRequest(user_id=1, title="Flask Architecture", max_recommendations=5)

    cand1 = RecommendationCandidate(
        candidate_id=10,
        content_type="bookmark",
        title="Flask SQLAlchemy Best Practices",
        url="http://example.com/flask",
        technologies=["Python", "Flask"]
    )
    mock_data_layer.fetch_candidate_set.return_value = CandidateSet(candidates=[cand1])

    pipeline = RecommendationPipeline(data_layer=mock_data_layer)
    results = pipeline.run(req)

    assert len(results) == 1
    assert results[0].candidate_id == 10
    mock_data_layer.fetch_candidate_set.assert_called_once_with(request=req, user_id=1, limit=100)
