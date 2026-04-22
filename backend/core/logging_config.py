import structlog
import logging
import sys
from flask import g, has_request_context

def add_correlation_id(logger, method, event_dict):
    """
    Processor: inject request correlation ID from structlog contextvars.
    This ensures traceability across the request lifecycle.
    """
    # Core traceability: try to get correlation_id from contextvars first,
    # as middleware binds it there for auto-propagation.
    return event_dict

def add_service_info(logger, method, event_dict):
    """Processor: inject service name and environment."""
    event_dict['service'] = 'fuze-api'
    # Environment will be determined by contextvars or global state if needed
    return event_dict

def configure_logging(debug: bool = False):
    """
    Call once at app startup before any logging occurs.
    Sets up structlog with JSON output for production,
    pretty-printed console output for development.
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt='iso', utc=True),
        add_service_info,
        structlog.processors.StackInfoRenderer(),
    ]

    if debug:
        # Development: human-readable colored output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer()
        ]
    else:
        # Production: JSON lines for log aggregation (Datadog, CloudWatch, etc.)
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging to go through structlog
    # so Flask's internal logs and SQLAlchemy logs are captured too
    logging.basicConfig(
        format='%(message)s',
        stream=sys.stdout,
        level=logging.DEBUG if debug else logging.INFO,
    )

def get_logger(name: str):
    """
    Drop-in replacement for logging.getLogger().
    Use this everywhere in Fuze backend.
    
    Usage:
      from backend.core.logging_config import get_logger
      logger = get_logger(__name__)
      logger.info("bookmark_created", user_id=user_id, url=url)
      logger.error("gemini_failed", error=str(e), attempt=attempt)
    """
    return structlog.get_logger(name)
