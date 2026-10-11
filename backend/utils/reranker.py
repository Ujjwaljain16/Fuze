import os
import threading
from typing import List, Optional

from core.logging_config import get_logger

logger = get_logger(__name__)

RERANK_MODEL = os.environ.get("SEARCH_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

_model = None
_model_failed = False
_lock = threading.Lock()


def _get_model():
    global _model, _model_failed
    if _model is not None or _model_failed:
        return _model
    with _lock:
        if _model is None and not _model_failed:
            try:
                from sentence_transformers import CrossEncoder
                _model = CrossEncoder(RERANK_MODEL, max_length=320)
                logger.info("reranker_loaded", extra={"model": RERANK_MODEL})
            except Exception as e:
                # Don't retry on every search: a missing model would add its load timeout to each request.
                _model_failed = True
                logger.warning("reranker_unavailable", extra={"model": RERANK_MODEL, "error": str(e)})
    return _model


def rerank_passages(query: str, passages: List[str]) -> Optional[List[float]]:
    """Relevance scores for (query, passage) pairs, or None if the reranker is unavailable."""
    model = _get_model()
    if model is None or not passages:
        return None
    return list(model.predict([(query, p) for p in passages], batch_size=32))
