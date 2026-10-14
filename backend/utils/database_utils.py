import time
from functools import wraps
from sqlalchemy.exc import OperationalError, TimeoutError, DisconnectionError
from core.logging_config import get_logger

logger = get_logger(__name__)


def retry_on_connection_error(max_retries: int = 3, delay: float = 1.0):
    """
    Retry decorator for read-only / idempotent database operations on transient connection failures.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, TimeoutError, DisconnectionError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        backoff = delay * (2 ** attempt)
                        logger.warning("db_operation_transient_error_retry", extra={"attempt": attempt + 1, "max_retries": max_retries + 1, "error": str(e)})
                        time.sleep(backoff)
                    else:
                        logger.error("db_operation_retry_exhausted", extra={"max_retries": max_retries + 1, "error": str(e)})
                        raise
                except Exception as e:
                    logger.error("db_operation_non_retryable_error", extra={"error": str(e)})
                    raise

            if last_exception:
                raise last_exception
            return None
        return wrapper
    return decorator
