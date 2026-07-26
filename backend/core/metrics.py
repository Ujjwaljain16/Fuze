"""
core/metrics.py
===============
Prometheus metrics registry for Fuze.

Defines all application metrics centrally. Instrumentation is added
per-module at call sites — this file only declares the registry and
all metric objects.

Multiprocessing support:
  prometheus_client requires PROMETHEUS_MULTIPROC_DIR env var to be set
  when running under multi-process servers (gunicorn). Set this to a
  writable tmpfs directory (e.g. /tmp/prometheus_multiproc).

  If the env var is not set, falls back to the default (in-process) registry,
  which is safe for single-worker or test environments.

Access:
  GET /metrics
  Authorization: Bearer {METRICS_AUTH_TOKEN}

Usage:
  from core.metrics import (
      http_request_duration,
      recommendation_latency,
      cache_hit_total,
      cache_miss_total,
      ...
  )

  with recommendation_latency.labels(engine="smart", stage="full").time():
      results = pipeline.run(request)
"""

import os
from core.logging_config import get_logger

logger = get_logger(__name__)

METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"

# ---------------------------------------------------------------------------
# Registry setup — multiprocess-aware
# ---------------------------------------------------------------------------
_registry = None
_multiproc_enabled = False

try:
    import prometheus_client
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Histogram,
        Gauge,
        multiprocess,
        CONTENT_TYPE_LATEST,
        generate_latest,
    )

    _multiproc_dir = os.getenv("PROMETHEUS_MULTIPROC_DIR")
    if _multiproc_dir:
        _multiproc_enabled = True
        _registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(_registry)
        logger.info("prometheus_multiproc_registry_initialized", extra={"dir": _multiproc_dir})
    else:
        from prometheus_client import REGISTRY as _registry
        logger.info("prometheus_default_registry_initialized")

    PROMETHEUS_AVAILABLE = True

except ImportError:
    logger.warning("prometheus_client_not_installed — metrics disabled. Add prometheus-client>=0.19.0 to requirements.txt")
    PROMETHEUS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------
# Buckets tuned for web API latency (ms → seconds)
_LATENCY_BUCKETS = (0.005, 0.010, 0.025, 0.050, 0.075, 0.100, 0.150, 0.200,
                    0.300, 0.500, 0.750, 1.0, 2.0, 5.0)

if PROMETHEUS_AVAILABLE and METRICS_ENABLED:
    # HTTP request latency — instrumented in run_production.py after_request
    http_request_duration = Histogram(
        "fuze_http_request_duration_seconds",
        "HTTP request duration in seconds",
        labelnames=["method", "endpoint", "status"],
        buckets=_LATENCY_BUCKETS,
    )

    # Recommendation pipeline latency — instrumented in pipeline.py
    recommendation_latency = Histogram(
        "fuze_recommendation_latency_seconds",
        "Recommendation pipeline duration in seconds",
        labelnames=["engine", "stage"],
        buckets=_LATENCY_BUCKETS,
    )

    # Cache hits and misses — instrumented in redis_utils.py
    cache_hit_total = Counter(
        "fuze_cache_hit_total",
        "Total cache hits",
        labelnames=["cache_type"],
    )
    cache_miss_total = Counter(
        "fuze_cache_miss_total",
        "Total cache misses",
        labelnames=["cache_type"],
    )

    # RQ queue depth — instrumented in task_queue.py on enqueue
    rq_queue_depth = Gauge(
        "fuze_rq_queue_depth",
        "Current RQ queue depth",
        labelnames=["queue"],
    )

    # Gemini API calls — instrumented in gemini_utils.py
    gemini_calls_total = Counter(
        "fuze_gemini_api_calls_total",
        "Total Gemini API calls",
        labelnames=["model", "status"],
    )

    # Embedding generation latency — instrumented in embed_worker.py / bookmark save
    embedding_generation_duration = Histogram(
        "fuze_embedding_generation_duration_seconds",
        "Time to generate a single embedding",
        buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.2, 0.5, 1.0, 2.0),
    )

    # Shadow evaluator quality metrics — emitted by shadow_evaluator.py
    shadow_overlap_at_k = Gauge(
        "fuze_shadow_overlap_at_k",
        "Shadow evaluation Overlap@K between legacy and new pipeline",
        labelnames=["k"],
    )
    shadow_mrr = Gauge(
        "fuze_shadow_mrr",
        "Shadow evaluation Mean Reciprocal Rank delta (new - legacy)",
    )
    shadow_ndcg_at_10 = Gauge(
        "fuze_shadow_ndcg_at_10",
        "Shadow evaluation NDCG@10 delta (new - legacy)",
    )

    # Feature flag evaluation — instrumented in feature_flags.py
    feature_flag_evaluation_total = Counter(
        "fuze_feature_flag_evaluation_total",
        "Total feature flag evaluations",
        labelnames=["flag", "result"],
    )

    # Embedding null rate gauge — set by backfill verification
    embedding_null_rate = Gauge(
        "fuze_embedding_null_rate",
        "Fraction of saved_content rows with NULL embedding (Gate 0 metric)",
    )

    # Total recommendation requests — tracks traffic distribution
    recommendation_requests_total = Counter(
        "fuze_recommendation_requests_total",
        "Total recommendation requests",
        labelnames=["engine", "result"],
    )

    # Event-driven processing pipeline stage metrics
    pipeline_events_total = Counter(
        "fuze_pipeline_events_total",
        "Total pipeline stage events emitted",
        labelnames=["stage", "status"],
    )

    logger.info("prometheus_metrics_registered")

else:
    # Stub objects so import sites don't need try/except
    class _NoOpMetric:
        def labels(self, **_): return self
        def observe(self, _): pass
        def inc(self, _=1): pass
        def set(self, _): pass
        def time(self):
            import contextlib
            return contextlib.nullcontext()

    _noop = _NoOpMetric()

    http_request_duration = _noop
    recommendation_latency = _noop
    cache_hit_total = _noop
    cache_miss_total = _noop
    rq_queue_depth = _noop
    gemini_calls_total = _noop
    embedding_generation_duration = _noop
    shadow_overlap_at_k = _noop
    shadow_mrr = _noop
    shadow_ndcg_at_10 = _noop
    feature_flag_evaluation_total = _noop
    embedding_null_rate = _noop
    recommendation_requests_total = _noop
    pipeline_events_total = _noop


def get_metrics_output() -> tuple:
    """
    Generate Prometheus text format output for /metrics endpoint.
    Returns (content_bytes, content_type_str).
    Returns (None, None) if prometheus_client is not available.
    """
    if not PROMETHEUS_AVAILABLE or not METRICS_ENABLED:
        return None, None
    try:
        output = generate_latest(_registry)
        return output, CONTENT_TYPE_LATEST
    except Exception as exc:
        logger.error("prometheus_generate_latest_error", extra={"error": str(exc)})
        return None, None
