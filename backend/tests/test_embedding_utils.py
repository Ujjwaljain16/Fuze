import pytest
import numpy as np
from utils.embedding_utils import (
    FallbackEmbeddingModel,
    calculate_cosine_similarity,
    get_embedding,
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


def _reset_model(monkeypatch):
    import utils.embedding_utils as eu
    monkeypatch.setattr(eu, '_embedding_model', None)
    monkeypatch.setattr(eu, '_embedding_model_initialized', False)
    return eu


@pytest.mark.unit
def test_model_load_failure_is_loud_not_hash_vectors(monkeypatch):
    """A silent switch to hash 'embeddings' would store vectors that mean nothing."""
    from unittest.mock import patch
    eu = _reset_model(monkeypatch)
    monkeypatch.delenv('DISABLE_EMBEDDINGS', raising=False)
    with patch.object(eu, 'SentenceTransformer', side_effect=OSError('no network')):
        with pytest.raises(eu.EmbeddingUnavailable):
            eu.get_embedding('pgvector tuning')
    assert eu._embedding_model_initialized is False  # the next call tries again


@pytest.mark.unit
def test_encode_failure_raises_instead_of_zero_vector(monkeypatch):
    from unittest.mock import MagicMock
    eu = _reset_model(monkeypatch)
    broken = MagicMock()
    broken.encode.side_effect = RuntimeError('out of memory')
    monkeypatch.setattr(eu, '_embedding_model', broken)
    monkeypatch.setattr(eu, '_embedding_model_initialized', True)
    monkeypatch.setattr(eu.redis_cache, 'get_cached_embedding', lambda *_: None)
    with pytest.raises(eu.EmbeddingUnavailable):
        eu.get_embedding('pgvector tuning')
