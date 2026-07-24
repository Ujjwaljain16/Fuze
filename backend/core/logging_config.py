import os
import sys
import socket
import logging
import uuid
import structlog
from typing import Optional

SERVICE_NAME = os.getenv("SERVICE_NAME", "fuze-api")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
HOSTNAME = socket.gethostname()


def add_correlation_id(logger, method_name, event_dict):
    """
    Processor: inject request correlation ID from event_dict or structlog contextvars.
    Ensures traceability across the request lifecycle and downstream services.
    """
    correlation_id = event_dict.get("correlation_id")
    if not correlation_id:
        try:
            ctx = structlog.contextvars.get_contextvars()
            correlation_id = ctx.get("correlation_id")
        except Exception:
            pass
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def add_service_info(logger, method_name, event_dict):
    """Processor: inject service name and environment."""
    event_dict["service"] = SERVICE_NAME
    event_dict["environment"] = ENVIRONMENT
    return event_dict


def add_runtime_info(logger, method_name, event_dict):
    """Processor: inject process ID and hostname for multi-worker / cluster observability."""
    event_dict["pid"] = os.getpid()
    event_dict["hostname"] = HOSTNAME
    return event_dict


def add_trace_context(logger, method_name, event_dict):
    """Processor: inject OpenTelemetry trace and span context if active."""
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            ctx = span.get_span_context()
            event_dict["trace_id"] = f"{ctx.trace_id:032x}"
            event_dict["span_id"] = f"{ctx.span_id:016x}"
    except Exception:
        pass
    return event_dict


def configure_logging(debug: bool = False, force: bool = False):
    """
    Call once at app startup before any logging occurs.
    Sets up structlog with JSON output for production,
    pretty-printed console output for development.
    Includes re-entrancy protection.
    """
    if getattr(configure_logging, "_configured", False) and not force:
        return
    configure_logging._configured = True

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_correlation_id,
        add_service_info,
        add_runtime_info,
        add_trace_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if not debug:
        shared_processors.append(structlog.processors.dict_tracebacks)

    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)


def get_logger(name: str):
    """
    Drop-in replacement for logging.getLogger().
    Use this everywhere in Fuze backend.

    Usage:
      from core.logging_config import get_logger
      logger = get_logger(__name__)
      logger.info("bookmark_created", user_id=user_id, url=url)
      logger.error("gemini_failed", error=str(e), attempt=attempt)
    """
    return structlog.get_logger(name)


def bind_request_context(correlation_id: Optional[str] = None, **kwargs) -> str:
    """Helper to bind request-scoped context variables to structlog."""
    if not correlation_id:
        correlation_id = uuid.uuid4().hex
    try:
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id, **kwargs)
    except Exception:
        pass
    return correlation_id


def clear_request_context():
    """Helper to clear request-scoped context variables after request execution."""
    try:
        structlog.contextvars.clear_contextvars()
    except Exception:
        pass
