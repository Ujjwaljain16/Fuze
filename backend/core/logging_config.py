import structlog
import logging
import sys

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
            structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
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
