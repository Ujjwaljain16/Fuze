"""
core/startup_validation.py
==========================
Startup integrity checker. Verifies that critical wiring, metrics,
feature flags, and configurations are correctly registered.
Fails fast if integration drift is detected.
"""

import sys
from core.logging_config import get_logger

logger = get_logger(__name__)


def validate_startup_integrity():
    """Run all critical startup assertions. Fails fast on failure."""
    logger.info("startup_validation_starting")

    try:
        _verify_queue_functions()
        _verify_metrics_registered()
        _verify_feature_flags_registered()
        _verify_gemini_config()
        logger.info("startup_validation_passed")
    except Exception as e:
        logger.critical("startup_validation_failed", extra={"error": str(e)})
        # Fail fast in production
        sys.exit(f"Startup validation failed: {e}")


def _verify_queue_functions():
    try:
        import services.task_queue as tq
    except ImportError as e:
        raise RuntimeError(f"Could not import task_queue: {e}")
    
    required_functions = [
        "enqueue_project_ml_job",
        "enqueue_embedding_job",
        "enqueue_bookmark_processing",
        "enqueue_cache_warm_job",
    ]
    for func in required_functions:
        if not hasattr(tq, func):
            raise RuntimeError(f"Missing required queue function: {func} in services/task_queue.py")


def _verify_metrics_registered():
    try:
        import core.metrics as metrics
    except ImportError as e:
        raise RuntimeError(f"Could not import metrics: {e}")

    required_metrics = [
        "http_request_duration",
        "recommendation_latency",
        "gemini_calls_total",
        "rq_queue_depth",
        "embedding_generation_duration",
        "feature_flag_evaluation_total",
        "embedding_null_rate",
        "recommendation_requests_total",
    ]
    for metric in required_metrics:
        if not hasattr(metrics, metric):
            raise RuntimeError(f"Missing required metric definition: {metric} in core/metrics.py")


def _verify_feature_flags_registered():
    try:
        import core.feature_flags as ff
    except ImportError as e:
        raise RuntimeError(f"Could not import feature_flags: {e}")

    required_flags = [
        "two_stage_retrieval",
        "search_rpc",
        "async_embeddings",
        "cache_warm_on_login",
    ]
    for flag in required_flags:
        if flag not in ff._ENV_DEFAULTS:
            raise RuntimeError(f"Missing required feature flag in _ENV_DEFAULTS: {flag} in core/feature_flags.py")


def _verify_gemini_config():
    try:
        from utils.unified_config import get_config
        config = get_config()
    except ImportError as e:
        raise RuntimeError(f"Could not import unified_config: {e}")

    if not config.ai.gemini_model:
        raise RuntimeError("Missing required config: GEMINI_MODEL")
    if not config.ai.gemini_fallback_model:
        raise RuntimeError("Missing required config: GEMINI_FALLBACK_MODEL")
