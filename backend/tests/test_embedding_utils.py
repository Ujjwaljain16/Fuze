import pytest
import numpy as np
from utils.embedding_utils import (
    FallbackEmbeddingModel,
    calculate_cosine_similarity,
    get_embedding,
    get_project_embedding,
    EMBEDDING_DIMENSION
)


@pytest.mark.unit
def test_fallback_embedding_model_callable():
    model = FallbackEmbeddingModel()
    assert model.is_fallback_model is True

    # Test encode method calls internal _generate_fallback_embedding without TypeError
    embeddings = model.encode(["python development", "machine learning"])
    assert isinstance(embeddings, np.ndarray)
    assert embeddings.shape == (2, EMBEDDING_DIMENSION)


@pytest.mark.unit
def test_cosine_similarity_numpy_speed():
    vec1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    vec2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    vec3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    assert calculate_cosine_similarity(vec1, vec2) == pytest.approx(1.0)
    assert calculate_cosine_similarity(vec1, vec3) == pytest.approx(0.0)


@pytest.mark.unit
def test_get_embedding_empty_text():
    emb = get_embedding("")
    assert isinstance(emb, np.ndarray)
    assert emb.shape == (EMBEDDING_DIMENSION,)
    assert np.all(emb == 0)
