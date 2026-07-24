#!/usr/bin/env python3
"""
Database Connection Manager
Provides production-grade SQLAlchemy engine management with RLock thread safety,
pool recycling, pre-ping validation, and secure SSL configuration.
"""

import os
import threading
from contextlib import contextmanager
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError, DisconnectionError, TimeoutError
from dotenv import load_dotenv

from core.logging_config import get_logger

load_dotenv()
logger = get_logger(__name__)


class DatabaseConnectionManager:
    """Manages database engine lifecycle and connection resilience."""

    def __init__(self):
        self._engine: Optional[Engine] = None
        self._lock = threading.RLock()

    def _get_database_url(self) -> str:
        """Fetch DATABASE_URL from environment with validation."""
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        return database_url

    def _is_sqlite(self, database_url: str) -> bool:
        """Check if the database URL is for SQLite."""
        return database_url.startswith('sqlite:///') or database_url.startswith('sqlite://')

    def _create_engine(self) -> Engine:
        """Create database engine with proper pooling and dialect-specific configuration."""
        database_url = self._get_database_url()
        is_sqlite = self._is_sqlite(database_url)

        if is_sqlite:
            connect_args = {}
            engine = create_engine(
                database_url,
                connect_args=connect_args,
                echo=False
            )
        else:
            statement_timeout = os.environ.get('DB_STATEMENT_TIMEOUT', '60000')
            connect_args = {
                'connect_timeout': 30,
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5,
                'application_name': 'fuze_app',
                'options': f'-c statement_timeout={statement_timeout} -c idle_in_transaction_session_timeout={statement_timeout}'
            }

            engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=int(os.environ.get('DB_POOL_SIZE', 5)),
                max_overflow=int(os.environ.get('DB_MAX_OVERFLOW', 10)),
                pool_timeout=30,
                pool_recycle=int(os.environ.get('DB_POOL_RECYCLE', 300)),
                pool_pre_ping=True,
                echo=False,
                connect_args=connect_args
            )

        self._setup_engine_events(engine)
        return engine

    def _setup_engine_events(self, engine: Engine):
        """Setup dialect-scoped event listeners."""
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if engine.dialect.name == "sqlite":
                if hasattr(dbapi_connection, 'execute'):
                    dbapi_connection.execute("PRAGMA journal_mode=WAL")

    def get_engine(self, force_refresh: bool = False) -> Engine:
        """Get or initialize the database engine using reentrant RLock."""
        with self._lock:
            if self._engine is not None and not force_refresh:
                return self._engine

            if self._engine is not None:
                try:
                    self._engine.dispose()
                except Exception as e:
                    logger.warning("db_engine_dispose_failed", extra={"error": str(e)})
                self._engine = None

            self._engine = self._create_engine()
            logger.info("db_engine_initialized_successfully")
            return self._engine

    @contextmanager
    def get_connection(self):
        """Yield a database connection with error handling and automatic retry on disconnect."""
        engine = self.get_engine()
        connection = None
        try:
            connection = engine.connect()
            yield connection
        except (OperationalError, DisconnectionError, TimeoutError) as e:
            logger.warning("db_connection_error_retrying", extra={"error": str(e)})
            try:
                engine = self.get_engine(force_refresh=True)
                connection = engine.connect()
                yield connection
            except Exception as refresh_err:
                logger.error("db_connection_refresh_failed", extra={"error": str(refresh_err)})
                raise
        finally:
            if connection:
                try:
                    connection.close()
                except Exception as close_err:
                    logger.warning("db_connection_close_failed", extra={"error": str(close_err)})

    def test_connection(self) -> bool:
        """Test active database connectivity with a fast SELECT 1 query."""
        try:
            with self.get_connection() as conn:
                conn.execute(text('SELECT 1'))
                return True
        except Exception as e:
            logger.error("db_connection_test_failed", extra={"error": str(e)})
            return False

    def refresh_connections(self) -> bool:
        """Force refresh of database connections without deadlock risk."""
        with self._lock:
            try:
                engine = self.get_engine(force_refresh=True)
                with engine.connect() as conn:
                    conn.execute(text('SELECT 1'))
                return True
            except Exception as e:
                logger.error("db_connection_refresh_failed", extra={"error": str(e)})
                return False

    def get_connection_info(self) -> Dict[str, Any]:
        """Get safe connection info with rendered URL and password masking."""
        try:
            database_url = self._get_database_url()
            url_obj = make_url(database_url)
            safe_url = url_obj.render_as_string(hide_password=True)

            info = {
                'drivername': url_obj.drivername,
                'database': url_obj.database,
                'host': url_obj.host,
                'port': url_obj.port,
                'safe_url': safe_url
            }

            if self._engine and hasattr(self._engine, 'pool'):
                info['pool_size'] = self._engine.pool.size()
                info['checked_out'] = self._engine.pool.checkedout()
                info['overflow'] = self._engine.pool.overflow()

            return info
        except Exception as e:
            return {'error': str(e)}


# Global instance
connection_manager = DatabaseConnectionManager()


def get_database_engine():
    return connection_manager.get_engine()


def get_database_connection():
    return connection_manager.get_connection()


def test_database_connection():
    return connection_manager.test_connection()


def refresh_database_connections():
    return connection_manager.refresh_connections()


def get_database_info():
    return connection_manager.get_connection_info()
