import os
import logging
from functools import wraps
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, TimeoutError, DisconnectionError
from sqlalchemy.pool import QueuePool
import psycopg2

logger = logging.getLogger(__name__)

def retry_on_connection_error(max_retries=3, delay=1.0):
    """Enhanced retry decorator for database operations with SSL handling"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except (OperationalError, TimeoutError, DisconnectionError) as e:
                    last_exception = e
                    error_str = str(e).lower()
                    
                    # Check if it's an SSL connection error
                    if any(ssl_error in error_str for ssl_error in ['ssl', 'connection closed', 'unexpected']):
                        logger.warning(f"SSL connection error (attempt {attempt + 1}/{max_retries + 1}): {e}")
                        if attempt < max_retries:
                            # Force connection refresh for SSL issues
                            try:
                                from models import db
                                db.session.remove()
                                db.engine.dispose()  # Dispose all connections
                                time.sleep(delay * (2 ** attempt))  # Exponential backoff
                            except Exception as refresh_error:
                                logger.warning(f"Failed to refresh connections: {refresh_error}")
                        else:
                            logger.error(f"SSL connection failed after {max_retries + 1} attempts: {e}")
                            raise
                    else:
                        # Regular connection error
                        logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                        if attempt < max_retries:
                            time.sleep(delay * (2 ** attempt))  # Exponential backoff
                        else:
                            logger.error(f"Database operation failed after {max_retries + 1} attempts: {e}")
                            raise
                        
                except Exception as e:
                    # Don't retry on non-connection errors
                    logger.error(f"Non-retryable error: {e}")
                    raise
                    
            raise last_exception
            
        return wrapper
    return decorator

def retry_on_ssl_error(max_retries=3, delay=1.0):
    """Specialized retry decorator for SSL connection issues"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    error_str = str(e).lower()
                    # Check if it's an SSL connection error
                    if any(ssl_error in error_str for ssl_error in ['ssl', 'connection closed', 'unexpected']):
                        last_exception = e
                        if attempt < max_retries:
                            logger.warning(f"SSL connection error (attempt {attempt + 1}/{max_retries + 1}): {e}")
                            # Force complete connection refresh
                            try:
                                from models import db
                                db.session.remove()
                                db.engine.dispose()  # Dispose all connections
                                time.sleep(delay * (2 ** attempt))  # Exponential backoff
                            except Exception as refresh_error:
                                logger.warning(f"Failed to refresh connections: {refresh_error}")
                        else:
                            logger.error(f"SSL connection failed after {max_retries + 1} attempts: {e}")
                            raise
                    else:
                        # Non-SSL error, don't retry
                        logger.error(f"Non-SSL error: {e}")
                        raise
                    
            raise last_exception
            
        return wrapper
    return decorator

def get_db_session():
    """Get a database session for the current app context with SSL error handling"""
    try:
        from models import db
        return db.session
    except Exception as e:
        logger.error(f"Failed to get database session: {e}")
        return None

def with_db_session(func):
    """Decorator to provide database session to functions"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        session = get_db_session()
        if session:
            kwargs['session'] = session
        return func(*args, **kwargs)
    return wrapper

def ensure_database_connection():
    """Ensure database connection is available with SSL error handling"""
    try:
        from models import db
        with db.engine.connect() as conn:
            conn.execute(text('SELECT 1'))
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

def get_database_connection():
    """Get a direct database connection with enhanced SSL configuration"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        # Check if using SQLite
        is_sqlite = database_url.startswith('sqlite:///') or database_url.startswith('sqlite://')
        
        # Enhanced SSL configuration (only for PostgreSQL)
        if is_sqlite:
            # SQLite doesn't support PostgreSQL connection arguments
            connect_args = {}
        else:
            # PostgreSQL connection configuration
            connect_args = {
                'connect_timeout': 10,
                'sslmode': 'require',  # Require SSL for security
                'sslcert': None,       # No client certificate required
                'sslkey': None,        # No client key required
                'sslrootcert': None,   # No root certificate required
                'keepalives': 1,       # Enable keepalives
                'keepalives_idle': 30, # Send keepalive after 30s idle
                'keepalives_interval': 10,  # Send keepalive every 10s
                'keepalives_count': 5, # Retry keepalive 5 times
                'application_name': 'fuze_utils'
            }
        
        engine = create_engine(
            database_url, 
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=20,
            pool_recycle=300,
            pool_pre_ping=True,
            connect_args=connect_args
        )
        
        return engine.connect()
        
    except Exception as e:
        logger.error(f"Failed to create database connection: {e}")
        raise

def test_database_connection():
    """Test database connection and performance with SSL error handling"""
    try:
        with get_database_connection() as conn:
            # Test simple query
            start_time = time.time()
            result = conn.execute(text('SELECT 1'))
            duration = time.time() - start_time
            
            print(f"Database connection test: {duration:.3f}s")
            return True
            
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

def check_database_tables():
    """Check if required tables exist with SSL error handling"""
    try:
        with get_database_connection() as conn:
            tables = ['users', 'saved_content', 'projects']
            existing_tables = []
            
            for table in tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    existing_tables.append((table, count))
                except Exception:
                    existing_tables.append((table, 0))
            
            return existing_tables
            
    except Exception as e:
        print(f"Failed to check tables: {e}")
        return []

def refresh_database_connections():
    """Force refresh of all database connections to resolve SSL issues"""
    try:
        from models import db
        logger.info("Refreshing database connections...")
        
        # Remove all sessions
        db.session.remove()
        
        # Dispose all connections in the pool
        db.engine.dispose()
        
        # Test connection
        with db.engine.connect() as conn:
            conn.execute(text('SELECT 1'))
            logger.info("Database connections refreshed successfully")
            return True
            
    except Exception as e:
        logger.error(f"Failed to refresh database connections: {e}")
        return False

def get_ssl_connection_info():
    """Get SSL connection information for debugging"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            return "DATABASE_URL not set"
        
        # Parse connection string to get SSL info
        if 'sslmode=' in database_url:
            ssl_mode = database_url.split('sslmode=')[1].split('&')[0]
        else:
            ssl_mode = "Not specified"
        
        return {
            'ssl_mode': ssl_mode,
            'has_ssl': 'sslmode=' in database_url,
            'connection_string': database_url.replace(database_url.split('@')[0].split('://')[1], '***') if '@' in database_url else database_url
        }
        
    except Exception as e:
        return f"Error parsing connection info: {e}"
