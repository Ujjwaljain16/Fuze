import os
import hashlib
import threading
from typing import Optional, Any, List
import numpy as np
from sentence_transformers import SentenceTransformer
from core.logging_config import get_logger
from .redis_utils import redis_cache

logger = get_logger(__name__)

EMBEDDING_DIMENSION = 384
MAX_EMBED_TEXT_LENGTH = 10000
ZERO_EMBEDDING = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)

_embedding_model: Optional[Any] = None
_embedding_model_initialized: bool = False
_embedding_model_name: str = "fallback-hash"
_embedding_lock = threading.RLock()

# Chosen by the SciFact bake-off (scripts/eval_retrieval.py): +10% nDCG@10 over MiniLM, same 384 dims.
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


def configured_model_name() -> str:
    return os.environ.get("EMBEDDING_MODEL_NAME", "").strip() or DEFAULT_EMBEDDING_MODEL


def _prefixes(model_name: str):
    """(query_prefix, passage_prefix) the model was trained with for asymmetric retrieval."""
    name = model_name.lower()
    if "bge-" in name and "-en" in name:
        return "Represent this sentence for searching relevant passages: ", ""
    if "e5-" in name:
        return "query: ", "passage: "
    return "", ""


class FallbackEmbeddingModel:
    """Deterministic, process-stable fallback embedding model using SHA256 hashing."""

    def __init__(self):
        self.dimension = EMBEDDING_DIMENSION
        self.is_fallback_model = True
        logger.info("fallback_embedding_model_initialized")

    def encode(self, texts, **kwargs) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]

        embeddings = []
        for text in texts:
            embeddings.append(self._generate_fallback_embedding(text))

        return np.array(embeddings, dtype=np.float32)

    def _generate_fallback_embedding(self, text: str) -> np.ndarray:
        try:
            import re
            from collections import Counter

            clean_text = text.lower()[:MAX_EMBED_TEXT_LENGTH]
            words = re.findall(r'\b\w+\b', clean_text)
            if not words:
                return ZERO_EMBEDDING.copy()

            word_counts = Counter(words)
            vector = np.zeros(self.dimension, dtype=np.float32)

            for word, count in word_counts.items():
                h1 = int(hashlib.sha256(word.encode('utf-8')).hexdigest(), 16) % self.dimension
                h2 = int(hashlib.sha256((word + "_salt").encode('utf-8')).hexdigest(), 16) % self.dimension

                vector[h1] += count * 0.1
                vector[h2] += count * 0.05

            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm

            return vector
        except Exception as e:
            logger.error("fallback_embedding_generation_failed", extra={"error": str(e)})
            return ZERO_EMBEDDING.copy()


def get_embedding_model():
    """Get or lazy-load the embedding model singleton with thread safety."""
    global _embedding_model, _embedding_model_initialized

    if not _embedding_model_initialized:
        with _embedding_lock:
            if not _embedding_model_initialized:
                _embedding_model = _initialize_embedding_model_robust()
                _embedding_model_initialized = True

    return _embedding_model


class EmbeddingUnavailable(RuntimeError):
    """The embedding model could not be loaded or failed to encode."""


def _initialize_embedding_model_robust():
    """Load the configured model, or fail loudly.

    There is deliberately no silent fallback: hash "embeddings" or a different model produce
    vectors in another space, which would be stored next to real ones and corrupt every
    similarity comparison. The hash model is only used when DISABLE_EMBEDDINGS opts into it
    (local development without the model download).
    """
    if os.environ.get('DISABLE_EMBEDDINGS', '').lower() in ('true', '1', 'yes'):
        logger.info("embeddings_disabled_by_env_using_fallback")
        return FallbackEmbeddingModel()

    global _embedding_model_name
    model_name = configured_model_name()
    try:
        logger.info("attempting_to_load_embedding_model", extra={"model_name": model_name})
        model = SentenceTransformer(model_name)
        dimension = model.encode(["test"]).shape[-1]
    except Exception as e:
        raise EmbeddingUnavailable(f"could not load embedding model {model_name}: {e}") from e
    if dimension != EMBEDDING_DIMENSION:
        raise EmbeddingUnavailable(f"model {model_name} has {dimension} dimensions, expected {EMBEDDING_DIMENSION}")
    _embedding_model_name = model_name
    logger.info("embedding_model_loaded_successfully", extra={"model_name": model_name})
    return model


def active_embedding_model_name() -> str:
    """Name of the model actually producing vectors (loads it if needed)."""
    get_embedding_model()
    return _embedding_model_name


def _embed_one(text: str, prefix: str) -> np.ndarray:
    if not text or not isinstance(text, str) or not text.strip():
        return ZERO_EMBEDDING.copy()

    clean_text = prefix + text.strip()[:MAX_EMBED_TEXT_LENGTH]
    model = get_embedding_model()
    # Cache key includes the model so switching models never serves another model's vectors.
    cache_text = f"{_embedding_model_name}::{clean_text}"

    try:
        cached_embedding = redis_cache.get_cached_embedding(cache_text)
        if cached_embedding is not None:
            return np.array(cached_embedding, dtype=np.float32)
    except Exception as cache_err:
        logger.warning("redis_cached_embedding_lookup_failed", extra={"error": str(cache_err)})

    try:
        embedding = np.asarray(model.encode([clean_text])[0], dtype=np.float32)
    except Exception as e:
        # A zero vector here would be stored or ranked as if it meant something.
        raise EmbeddingUnavailable(f"encoding failed: {e}") from e
    try:
        redis_cache.cache_embedding(cache_text, embedding)
    except Exception:
        pass
    return embedding


def get_embedding(text: str) -> np.ndarray:
    """Embed stored content (bookmarks, projects, passages)."""
    get_embedding_model()
    return _embed_one(text, _prefixes(_embedding_model_name)[1])


def embed_query(text: str) -> np.ndarray:
    """Embed a search query / intent, with the model's query instruction where it has one."""
    get_embedding_model()
    return _embed_one(text, _prefixes(_embedding_model_name)[0])


def get_embeddings_batch(texts: list, batch_size: int = 32) -> np.ndarray:
    """Encode many passages in one model call (no per-text Redis caching)."""
    if not texts:
        return np.zeros((0, EMBEDDING_DIMENSION), dtype=np.float32)
    model = get_embedding_model()
    prefix = _prefixes(_embedding_model_name)[1]
    clean = [prefix + ((t or "").strip()[:MAX_EMBED_TEXT_LENGTH] or " ") for t in texts]
    return np.asarray(model.encode(clean, batch_size=batch_size), dtype=np.float32)


def calculate_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate fast NumPy cosine similarity between two 1D/2D vectors."""
    try:
        if vec1 is None or vec2 is None:
            return 0.0

        a = np.asarray(vec1, dtype=np.float32).flatten()
        b = np.asarray(vec2, dtype=np.float32).flatten()

        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(a, b) / (norm_a * norm_b))
    except Exception as e:
        logger.error("error_calculating_cosine_similarity", extra={"error": str(e)})
        return 0.0


def get_content_embedding(content) -> np.ndarray:
    """Get embedding for content combining title, extracted text, and notes."""
    try:
        if not content:
            return ZERO_EMBEDDING.copy()

        title = getattr(content, 'title', '') or ''
        text_val = getattr(content, 'extracted_text', '') or ''
        notes = getattr(content, 'notes', '') or ''

        combined_text = f"{title} {text_val} {notes}".strip()
        return get_embedding(combined_text)
    except Exception as e:
        logger.error("error_getting_content_embedding", extra={"error": str(e)})
        return ZERO_EMBEDDING.copy()





def is_embedding_available() -> bool:
    """Check if proper embedding model is available (not fallback)."""
    try:
        model = get_embedding_model()
        return model is not None and not getattr(model, 'is_fallback_model', False)
    except Exception:
        return False


def get_embedding_model_info() -> str:
    """Get description of active embedding model."""
    try:
        model = get_embedding_model()
        if model is None:
            return "No embedding model available"

        if getattr(model, 'is_fallback_model', False):
            return "Fallback embedding model (limited functionality)"

        model_name = getattr(model, 'model_name', 'SentenceTransformer')
        return f"Proper embedding model: {model_name}"
    except Exception:
        return "No embedding model available"