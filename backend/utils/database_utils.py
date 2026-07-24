import os
import time
from functools import wraps
from typing import Optional, List, Tuple
from sqlalchemy import text, inspect
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


# Alias for backward compatibility
retry_on_ssl_error = retry_on_connection_error


def get_db_session():
    """Get a database session for the current app context."""
    try:
        from models import db
        return db.session
    except Exception as e:
        logger.error("get_db_session_failed", extra={"error": str(e)})
        return None


def with_db_session(func):
    """Decorator to provide database session to functions without overwriting explicit kwargs."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        session = get_db_session()
        if session:
            kwargs.setdefault('session', session)
        return func(*args, **kwargs)
    return wrapper


def set_rls_context(session, user_id: str):
    """
    Sets the PostgreSQL session variable for RLS policies within the current transaction scope.
    """
    try:
        session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)}
        )
    except Exception as e:
        logger.error("set_rls_context_failed", extra={"error": str(e)})


def ensure_database_connection() -> bool:
    """Ensure database connection is available."""
    try:
        from models import db
        with db.engine.connect() as conn:
            conn.execute(text('SELECT 1'))
            return True
    except Exception as e:
        logger.error("database_connection_check_failed", extra={"error": str(e)})
        return False


def get_database_connection():
    """Get a database connection from Flask-SQLAlchemy or connection manager without creating new engines."""
    try:
        from models import db
        return db.engine.connect()
    except Exception:
        from utils.database_connection_manager import get_database_connection as get_mgr_conn
        return get_mgr_conn()


def test_database_connection() -> bool:
    """Test database connection and performance."""
    try:
        with get_database_connection() as conn:
            start_time = time.time()
            conn.execute(text('SELECT 1'))
            duration = time.time() - start_time
            logger.info("database_connection_test_passed", extra={"duration_seconds": round(duration, 3)})
            return True
    except Exception as e:
        logger.error("database_connection_test_failed", extra={"error": str(e)})
        return False


def check_database_tables() -> List[Tuple[str, int]]:
    """Check table existence and count rows safely."""
    try:
        with get_database_connection() as conn:
            inspector = inspect(conn)
            allowed_tables = ['users', 'saved_content', 'projects']
            existing_tables = []

            for table in allowed_tables:
                if inspector.has_table(table):
                    try:
                        res = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = res.fetchone()[0]
                        existing_tables.append((table, count))
                    except Exception:
                        existing_tables.append((table, 0))
                else:
                    existing_tables.append((table, 0))

            return existing_tables
    except Exception as e:
        logger.error("check_database_tables_failed", extra={"error": str(e)})
        return []


def refresh_database_connections() -> bool:
    """Force refresh of database sessions and connection pools."""
    try:
        from models import db
        logger.info("refreshing_database_connections")
        db.session.remove()
        db.engine.dispose()
        with db.engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        logger.info("database_connections_refreshed_successfully")
        return True
    except Exception as e:
        logger.error("refresh_database_connections_failed", extra={"error": str(e)})
        return False


def get_ssl_connection_info() -> dict:
    """Get SSL connection information for debugging."""
    try:
        database_url = os.environ.get('DATABASE_URL', '')
        if not database_url:
            return {'ssl_mode': 'Not specified', 'has_ssl': False, 'connection_string': 'DATABASE_URL not set'}

        has_ssl = 'sslmode=' in database_url
        ssl_mode = database_url.split('sslmode=')[1].split('&')[0] if has_ssl else 'Not specified'

        return {
            'ssl_mode': ssl_mode,
            'has_ssl': has_ssl,
        }
    except Exception as e:
        return {'error': str(e)}
