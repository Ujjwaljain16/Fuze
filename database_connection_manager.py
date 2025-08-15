#!/usr/bin/env python3
"""
Database Connection Manager
Provides robust SSL connection handling and automatic recovery
"""

import os
import time
import logging
import threading
from contextlib import contextmanager
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError, DisconnectionError, TimeoutError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    """Manages database connections with SSL error handling and automatic recovery"""
    
    def __init__(self):
        self._engine: Optional[Engine] = None
        self._lock = threading.Lock()
        self._connection_attempts = 0
        self._max_retries = 3
        self._last_connection_test = 0
        self._connection_test_interval = 60  # Test connection every minute
        
    def _get_database_url(self) -> str:
        """Get database URL from environment"""
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        return database_url
    
    def _create_engine(self, ssl_mode: str = 'prefer') -> Engine:
        """Create database engine with specified SSL mode"""
        database_url = self._get_database_url()
        
        # Update SSL mode in connection string
        if 'sslmode=' in database_url:
            # Replace existing SSL mode
            base_url = database_url.split('sslmode=')[0]
            remaining = database_url.split('sslmode=')[1]
            if '&' in remaining:
                remaining = '&' + remaining.split('&', 1)[1]
            else:
                remaining = ''
            database_url = f"{base_url}sslmode={ssl_mode}{remaining}"
        else:
            # Add SSL mode
            separator = '&' if '?' in database_url else '?'
            database_url = f"{database_url}{separator}sslmode={ssl_mode}"
        
        # Enhanced connection configuration with longer timeouts for Supabase
        connect_args = {
            'connect_timeout': 30,  # Increased from 10 to 30 seconds for Supabase
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
            'application_name': 'fuze_connection_manager',
            'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000'
        }
        
        # Add SSL-specific arguments
        if ssl_mode in ['require', 'verify-ca', 'verify-full']:
            connect_args.update({
                'sslcert': None,
                'sslkey': None,
                'sslrootcert': None
            })
        
        engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=20,
            pool_recycle=300,
            pool_pre_ping=True,
            echo=False,
            connect_args=connect_args
        )
        
        # Add event listeners for connection management
        self._setup_engine_events(engine)
        
        return engine
    
    def _setup_engine_events(self, engine: Engine):
        """Setup event listeners for the engine"""
        
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas if using SQLite"""
            if hasattr(dbapi_connection, 'execute'):
                dbapi_connection.execute("PRAGMA journal_mode=WAL")
        
        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Handle connection checkout"""
            logger.debug("Database connection checked out")
        
        @event.listens_for(engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Handle connection checkin"""
            logger.debug("Database connection checked in")
    
    def _test_connection(self, engine: Engine) -> bool:
        """Test if the engine connection works with retry logic"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                with engine.connect() as conn:
                    # Use a simple, fast query with timeout
                    result = conn.execute(text('SELECT 1'))
                    result.fetchone()  # Actually fetch the result
                    return True
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection test attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.warning(f"Connection test failed after {max_retries} attempts: {e}")
                    return False
        
        return False
    
    def _find_working_ssl_mode(self) -> Optional[str]:
        """Find a working SSL mode by testing different configurations"""
        ssl_modes = ['prefer', 'require', 'verify-ca', 'verify-full']
        
        for ssl_mode in ssl_modes:
            try:
                logger.info(f"Testing SSL mode: {ssl_mode}")
                test_engine = self._create_engine(ssl_mode)
                
                if self._test_connection(test_engine):
                    logger.info(f"✅ SSL mode '{ssl_mode}' works")
                    test_engine.dispose()
                    return ssl_mode
                
                test_engine.dispose()
                
            except Exception as e:
                logger.warning(f"SSL mode '{ssl_mode}' failed: {e}")
                continue
        
        # If no SSL mode works, try 'allow' mode (less secure but more compatible)
        try:
            logger.info("Testing SSL mode: allow")
            # Create a custom engine with 'allow' mode
            database_url = self._get_database_url()
            if 'sslmode=' in database_url:
                base_url = database_url.split('sslmode=')[0]
                remaining = database_url.split('sslmode=')[1]
                if '&' in remaining:
                    remaining = '&' + remaining.split('&', 1)[1]
                else:
                    remaining = ''
                database_url = f"{base_url}sslmode=allow{remaining}"
            else:
                separator = '&' if '?' in database_url else '?'
                database_url = f"{database_url}{separator}sslmode=allow"
            
            test_engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=3,
                max_overflow=5,
                pool_timeout=30,
                pool_recycle=300,
                pool_pre_ping=True,
                echo=False,
                connect_args={
                    'connect_timeout': 30,
                    'application_name': 'fuze_connection_manager_allow_ssl'
                }
            )
            
            if self._test_connection(test_engine):
                logger.info("✅ SSL mode 'allow' works")
                test_engine.dispose()
                return 'allow'
            
            test_engine.dispose()
            
        except Exception as e:
            logger.warning(f"SSL mode 'allow' failed: {e}")
        
        return None
    
    def get_engine(self, force_refresh: bool = False) -> Engine:
        """Get database engine, creating or refreshing as needed"""
        with self._lock:
            current_time = time.time()
            
            # Check if we need to test the connection
            if (self._engine and not force_refresh and 
                current_time - self._last_connection_test < self._connection_test_interval):
                return self._engine
            
            # Dispose existing engine if any
            if self._engine:
                try:
                    self._engine.dispose()
                except Exception as e:
                    logger.warning(f"Failed to dispose engine: {e}")
                self._engine = None
            
            # Try to create new engine
            working_ssl_mode = None
            
            # First try with current SSL mode from environment
            try:
                database_url = self._get_database_url()
                if 'sslmode=' in database_url:
                    current_ssl = database_url.split('sslmode=')[1].split('&')[0]
                    logger.info(f"Trying current SSL mode: {current_ssl}")
                    
                    test_engine = self._create_engine(current_ssl)
                    if self._test_connection(test_engine):
                        working_ssl_mode = current_ssl
                        test_engine.dispose()
                    else:
                        test_engine.dispose()
                        
            except Exception as e:
                logger.warning(f"Current SSL mode failed: {e}")
            
            # If current mode doesn't work, find a working one
            if not working_ssl_mode:
                working_ssl_mode = self._find_working_ssl_mode()
            
            # If no SSL mode works, try without SSL
            if not working_ssl_mode:
                logger.warning("No SSL mode works, trying without SSL")
                try:
                    database_url = self._get_database_url()
                    # Remove SSL mode completely
                    if 'sslmode=' in database_url:
                        base_url = database_url.split('sslmode=')[0]
                        remaining = database_url.split('sslmode=')[1]
                        if '&' in remaining:
                            remaining = '&' + remaining.split('&', 1)[1]
                        else:
                            remaining = ''
                        database_url = base_url + remaining
                        database_url = database_url.rstrip('&?')
                    
                    # Create engine without SSL
                    engine = create_engine(
                        database_url,
                        poolclass=QueuePool,
                        pool_size=5,
                        max_overflow=10,
                        pool_timeout=20,
                        pool_recycle=300,
                        pool_pre_ping=True,
                        echo=False,
                        connect_args={
                            'connect_timeout': 30,  # Increased from 10 to 30 seconds
                            'application_name': 'fuze_connection_manager_no_ssl',
                            'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000'
                        }
                    )
                    
                    if self._test_connection(engine):
                        working_ssl_mode = 'none'
                        engine.dispose()
                    else:
                        engine.dispose()
                        raise Exception("No SSL mode works and non-SSL also fails")
                        
                except Exception as e:
                    logger.error(f"Failed to create working connection: {e}")
                    raise
            
            # Create the final working engine
            if working_ssl_mode == 'none':
                # Create engine without SSL
                database_url = self._get_database_url()
                if 'sslmode=' in database_url:
                    base_url = database_url.split('sslmode=')[0]
                    remaining = database_url.split('sslmode=')[1]
                    if '&' in remaining:
                        remaining = '&' + remaining.split('&', 1)[1]
                    else:
                        remaining = ''
                    database_url = base_url + remaining
                    database_url = database_url.rstrip('&?')
                
                self._engine = create_engine(
                    database_url,
                    poolclass=QueuePool,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=20,
                    pool_recycle=300,
                    pool_pre_ping=True,
                    echo=False,
                    connect_args={
                        'connect_timeout': 30,  # Increased from 10 to 30 seconds
                        'application_name': 'fuze_connection_manager_no_ssl',
                        'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000'
                    }
                )
            else:
                # Create engine with working SSL mode
                self._engine = self._create_engine(working_ssl_mode)
            
            # Test the final engine
            if not self._test_connection(self._engine):
                raise Exception("Created engine but connection test failed")
            
            self._last_connection_test = current_time
            logger.info(f"✅ Database engine created successfully with SSL mode: {working_ssl_mode}")
            
            return self._engine
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic error handling"""
        engine = self.get_engine()
        connection = None
        
        try:
            connection = engine.connect()
            yield connection
        except (OperationalError, DisconnectionError, TimeoutError) as e:
            logger.warning(f"Database connection error: {e}")
            
            # Try to refresh the engine
            try:
                engine = self.get_engine(force_refresh=True)
                connection = engine.connect()
                yield connection
            except Exception as refresh_error:
                logger.error(f"Failed to refresh connection: {refresh_error}")
                raise
        finally:
            if connection:
                try:
                    connection.close()
                except Exception as e:
                    logger.warning(f"Failed to close connection: {e}")
    
    def test_connection(self) -> bool:
        """Test if the database connection is working"""
        try:
            with self.get_connection() as conn:
                conn.execute(text('SELECT 1'))
                return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def refresh_connections(self) -> bool:
        """Force refresh of all database connections"""
        try:
            with self._lock:
                if self._engine:
                    self._engine.dispose()
                    self._engine = None
                
                # Test new connection
                engine = self.get_engine(force_refresh=True)
                return self._test_connection(engine)
                
        except Exception as e:
            logger.error(f"Failed to refresh connections: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about the current database connection"""
        try:
            database_url = self._get_database_url()
            
            info = {
                'has_ssl': 'sslmode=' in database_url,
                'connection_string': database_url.replace(
                    database_url.split('@')[0].split('://')[1], '***'
                ) if '@' in database_url else database_url
            }
            
            if 'sslmode=' in database_url:
                info['ssl_mode'] = database_url.split('sslmode=')[1].split('&')[0]
            else:
                info['ssl_mode'] = 'Not specified'
            
            if self._engine:
                info['pool_size'] = self._engine.pool.size()
                info['checked_out'] = self._engine.pool.checkedout()
                info['overflow'] = self._engine.pool.overflow()
            
            return info
            
        except Exception as e:
            return {'error': str(e)}

# Global instance
connection_manager = DatabaseConnectionManager()

def get_database_engine():
    """Get database engine from the connection manager"""
    return connection_manager.get_engine()

def get_database_connection():
    """Get database connection from the connection manager"""
    return connection_manager.get_connection()

def test_database_connection():
    """Test database connection"""
    return connection_manager.test_connection()

def refresh_database_connections():
    """Refresh database connections"""
    return connection_manager.refresh_connections()

def get_database_info():
    """Get database connection information"""
    return connection_manager.get_connection_info()

if __name__ == "__main__":
    # Test the connection manager
    print("Testing Database Connection Manager...")
    
    try:
        # Test connection
        if test_database_connection():
            print("✅ Database connection successful")
            
            # Get connection info
            info = get_database_info()
            print(f"Connection info: {info}")
        else:
            print("❌ Database connection failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
