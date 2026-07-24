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
_embedding_lock = threading.RLock()


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
                try:
                    from utils.production_optimizations import get_cached_embedding_model
                    model = get_cached_embedding_model()
                    if model:
                        _embedding_model = model
                        _embedding_model_initialized = True
                        logger.info("using_production_optimized_embedding_model")
                        return _embedding_model
                except Exception as opt_err:
                    logger.debug("production_optimization_unavailable", extra={"error": str(opt_err)})

                _embedding_model = _initialize_embedding_model_robust()
                _embedding_model_initialized = True

    return _embedding_model


def _initialize_embedding_model_robust():
    """Robust embedding model initialization with graceful fallback."""
    if os.environ.get('DISABLE_EMBEDDINGS', '').lower() in ('true', '1', 'yes'):
        logger.info("embeddings_disabled_by_env_using_fallback")
        return FallbackEmbeddingModel()

    model_options = [
        'all-MiniLM-L6-v2',
        'paraphrase-MiniLM-L6-v2',
        'paraphrase-MiniLM-L3-v2',
    ]

    for model_name in model_options:
        try:
            logger.info("attempting_to_load_embedding_model", extra={"model_name": model_name})
            model = SentenceTransformer(model_name)
            test_embedding = model.encode(["test"])
            if test_embedding is not None and len(test_embedding) > 0:
                logger.info("embedding_model_loaded_successfully", extra={"model_name": model_name})
                return model
        except Exception as e:
            logger.warning("failed_to_load_embedding_model", extra={"model_name": model_name, "error": str(e)})

    logger.warning("all_embedding_models_failed_using_fallback")
    return FallbackEmbeddingModel()


def get_embedding(text: str) -> np.ndarray:
    """Get embedding for text with Redis caching and length safeguards."""
    if not text or not isinstance(text, str) or not text.strip():
        return ZERO_EMBEDDING.copy()

    clean_text = text.strip()[:MAX_EMBED_TEXT_LENGTH]

    try:
        cached_embedding = redis_cache.get_cached_embedding(clean_text)
        if cached_embedding is not None:
            return np.array(cached_embedding, dtype=np.float32)
    except Exception as cache_err:
        logger.warning("redis_cached_embedding_lookup_failed", extra={"error": str(cache_err)})

    try:
        model = get_embedding_model()
        embedding = model.encode([clean_text])[0]
        if isinstance(embedding, np.ndarray):
            embedding = embedding.astype(np.float32)
        else:
            embedding = np.array(embedding, dtype=np.float32)

        try:
            redis_cache.cache_embedding(clean_text, embedding)
        except Exception:
            pass

        return embedding
    except Exception as e:
        logger.error("error_generating_embedding", extra={"error": str(e)})
        return ZERO_EMBEDDING.copy()


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


def get_project_embedding(project) -> np.ndarray:
    """Get embedding for project combining title, description, and technologies."""
    try:
        if not project:
            return ZERO_EMBEDDING.copy()

        title = getattr(project, 'title', '') or ''
        desc = getattr(project, 'description', '') or ''
        tech = getattr(project, 'technologies', '') or ''

        combined_text = f"{title} {desc} {tech}".strip()
        return get_embedding(combined_text)
    except Exception as e:
        logger.error("error_getting_project_embedding", extra={"error": str(e)})
        return ZERO_EMBEDDING.copy()


def get_task_embedding(task) -> np.ndarray:
    """Get embedding for task combining title and description."""
    try:
        if not task:
            return ZERO_EMBEDDING.copy()

        title = getattr(task, 'title', '') or ''
        desc = getattr(task, 'description', '') or ''

        combined_text = f"{title} {desc}".strip()
        return get_embedding(combined_text)
    except Exception as e:
        logger.error("error_getting_task_embedding", extra={"error": str(e)})
        return ZERO_EMBEDDING.copy()


def get_subtask_embedding(subtask) -> np.ndarray:
    """Get embedding for subtask combining title and description."""
    try:
        if not subtask:
            return ZERO_EMBEDDING.copy()

        title = getattr(subtask, 'title', '') or ''
        desc = getattr(subtask, 'description', '') or ''

        combined_text = f"{title} {desc}".strip()
        return get_embedding(combined_text)
    except Exception as e:
        logger.error("error_getting_subtask_embedding", extra={"error": str(e)})
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