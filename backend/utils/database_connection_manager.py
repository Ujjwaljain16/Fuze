#!/usr/bin/env python3
"""
Database Connection Manager
Provides robust SSL connection handling and automatic recovery
"""

import os
import time
import logging
import threading
import socket
from urllib.parse import urlparse, urlunparse
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

# IPv4 resolution helper - ensures we always get IPv4 addresses
def resolve_hostname_to_ipv4(hostname: str, max_retries: int = 3) -> Optional[str]:
    """
    Resolve hostname to IPv4 address with multiple retry strategies.
    Returns None if IPv4 resolution fails (will force using hostname, which may fail).
    """
    for attempt in range(max_retries):
        try:
            # Method 1: Use getaddrinfo with AF_INET to force IPv4 only
            addresses = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
            if addresses:
                ipv4_address = addresses[0][4][0]
                logger.info(f" Resolved {hostname} to IPv4 (method 1): {ipv4_address}")
                return ipv4_address
        except socket.gaierror as e:
            logger.debug(f"IPv4 resolution attempt {attempt + 1} (method 1) failed: {e}")
        
        try:
            # Method 2: Use gethostbyname (legacy, but sometimes works when getaddrinfo fails)
            ipv4_address = socket.gethostbyname(hostname)
            if ipv4_address:
                logger.info(f" Resolved {hostname} to IPv4 (method 2): {ipv4_address}")
                return ipv4_address
        except socket.gaierror as e:
            logger.debug(f"IPv4 resolution attempt {attempt + 1} (method 2) failed: {e}")
        
        # Wait before retry
        if attempt < max_retries - 1:
            time.sleep(1)
    
    logger.warning(f" Failed to resolve {hostname} to IPv4 after {max_retries} attempts")
    return None

class DatabaseConnectionManager:
    """Manages database connections with SSL error handling and automatic recovery"""
    
    def __init__(self):
        self._engine: Optional[Engine] = None
        self._lock = threading.Lock()
        self._connection_attempts = 0
        self._max_retries = 3
        self._last_connection_test = 0
        self._connection_test_interval = 60  # Test connection every minute
        
    def _resolve_hostname(self, hostname: str) -> Optional[str]:
        """Resolve hostname to IP address with IPv6 support and IPv4 fallback"""
        try:
            # Try to get all addresses (both IPv4 and IPv6)
            addresses = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            
            # Prefer IPv4 if available, otherwise use IPv6
            ipv4_addresses = [addr[4][0] for addr in addresses if addr[0] == socket.AF_INET]
            ipv6_addresses = [addr[4][0] for addr in addresses if addr[0] == socket.AF_INET6]
            
            if ipv4_addresses:
                logger.info(f" Resolved {hostname} to IPv4: {ipv4_addresses[0]}")
                return ipv4_addresses[0]
            elif ipv6_addresses:
                logger.info(f" Resolved {hostname} to IPv6: {ipv6_addresses[0]}")
                return ipv6_addresses[0]
            else:
                logger.warning(f" Could not resolve {hostname} to any IP address")
                return None
                
        except socket.gaierror as e:
            logger.error(f" DNS resolution failed for {hostname}: {e}")
            return None
        except Exception as e:
            logger.error(f" Unexpected error resolving {hostname}: {e}")
            return None
    
    def _resolve_hostname_with_fallback(self, hostname: str) -> Optional[str]:
        """Resolve hostname to IPv4 only (never use IPv6 as it causes connection issues)"""
        try:
            # Force IPv4 resolution only - never use IPv6
            addresses = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
            if addresses:
                ipv4_address = addresses[0][4][0]
                logger.info(f" Resolved {hostname} to IPv4: {ipv4_address}")
                return ipv4_address
        except Exception as e:
            logger.warning(f" IPv4 resolution failed for {hostname}: {e}")
        
        # Don't try IPv6 - it causes "Network is unreachable" errors on Render
        logger.warning(f" IPv4 resolution failed, will use hostname directly instead of IPv6")
        return None
    
    def _validate_database_url(self, url: str) -> bool:
        """Validate that the database URL is properly formatted"""
        try:
            # Basic validation - check if it looks like a valid PostgreSQL URL
            if not url.startswith('postgresql://'):
                return False
            
            # Check if it has the basic structure
            if '@' not in url:
                return False
            
            # Check if the host part looks reasonable
            at_index = url.find('@')
            slash_index = url.find('/', at_index)
            
            if slash_index == -1:
                # No slash found, URL ends with host:port
                host_port_part = url[at_index + 1:]
            else:
                host_port_part = url[at_index + 1:slash_index]
            
            # Host part should not be empty
            if not host_port_part.strip():
                return False
            
            # If there's a port, it should be a number
            if ':' in host_port_part:
                parts = host_port_part.split(':')
                if len(parts) == 2:
                    try:
                        int(parts[1])
                    except ValueError:
                        return False
            
            return True
            
        except Exception as e:
            logger.warning(f" URL validation error: {e}")
            return False
    
    def _get_database_url(self) -> str:
        """Get database URL from environment and resolve hostname if needed"""
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        # Check if this is a Supabase URL that needs hostname resolution
        # Handle both direct db.*.supabase.co and pooler.*.pooler.supabase.co URLs
        if 'supabase.co' in database_url and ('db.' in database_url or 'pooler.' in database_url):
            try:
                # Use urllib.parse for robust URL parsing
                parsed = urlparse(database_url)
                
                # Extract hostname and port from netloc
                # netloc format: user:password@host:port
                netloc = parsed.netloc
                if not netloc:
                    logger.warning(" Could not extract netloc from DATABASE_URL, skipping IPv4 resolution")
                    return database_url
                
                # Split credentials and host:port
                # Note: password may contain @, so we need to find the LAST @ which separates credentials from host
                # Format: username:password@host:port (password can contain @)
                if '@' in netloc:
                    # Find the last @ which should separate credentials from host
                    # But we need to be careful - if there are multiple @, the last one is the separator
                    # Count @ symbols to determine if password contains @
                    at_count = netloc.count('@')
                    if at_count == 1:
                        # Simple case: user:pass@host:port
                        creds_part, host_port_part = netloc.split('@', 1)
                    else:
                        # Password contains @ - find the last @ which is the separator
                        # Format: user:pass@with@symbols@host:port
                        # We need to find where hostname starts (after last @)
                        # Hostname should start with a letter or number, not a digit followed by @
                        # Actually, the safest is to find the last @ and check if what follows looks like a hostname
                        last_at_index = netloc.rfind('@')
                        potential_host = netloc[last_at_index + 1:]
                        
                        # Check if potential_host looks like a hostname (starts with letter, contains dots)
                        if '.' in potential_host and potential_host.split(':')[0].replace('.', '').replace('-', '').isalnum():
                            # This looks like a hostname, so last @ is the separator
                            creds_part = netloc[:last_at_index]
                            host_port_part = potential_host
                        else:
                            # Doesn't look like hostname, try second-to-last @
                            if at_count >= 2:
                                # Try finding @ before the last one
                                second_last_at = netloc.rfind('@', 0, last_at_index)
                                potential_host2 = netloc[second_last_at + 1:]
                                if '.' in potential_host2.split(':')[0]:
                                    creds_part = netloc[:second_last_at]
                                    host_port_part = potential_host2
                                else:
                                    # Fallback: use last @ anyway
                                    creds_part = netloc[:last_at_index]
                                    host_port_part = potential_host
                            else:
                                # Fallback: use last @
                                creds_part = netloc[:last_at_index]
                                host_port_part = potential_host
                else:
                    # No credentials: host:port
                    creds_part = ""
                    host_port_part = netloc
                
                # Extract hostname and port from host_port_part
                if ':' in host_port_part:
                    # Handle IPv6 addresses (they have colons)
                    if host_port_part.startswith('['):
                        # IPv6 address in brackets: [::1]:5432
                        bracket_end = host_port_part.find(']')
                        if bracket_end != -1:
                            hostname = host_port_part[1:bracket_end]
                            port_part = host_port_part[bracket_end + 1:]  # Includes the ':'
                        else:
                            logger.warning(" Malformed IPv6 address in URL, skipping IPv4 resolution")
                            return database_url
                    else:
                        # Regular hostname:port format - split from right
                        parts = host_port_part.rsplit(':', 1)
                        if len(parts) == 2:
                            hostname = parts[0]
                            port_part = ':' + parts[1]
                        else:
                            hostname = host_port_part
                            port_part = ""
                else:
                    hostname = host_port_part
                    port_part = ""
                
                # Validate hostname - should not contain @, :, or be empty
                if '@' in hostname or ':' in hostname or hostname.strip() == '':
                    logger.warning(f" Invalid hostname extracted: {hostname}, skipping IPv4 resolution")
                    logger.debug(f"   Original netloc: {netloc}, host_port_part: {host_port_part}")
                    return database_url
                
                # Try to resolve hostname to IPv4 only (avoid IPv6 which causes connection issues)
                # This is critical for Render.com which has IPv6 connectivity issues
                ip_address = resolve_hostname_to_ipv4(hostname)
                
                if ip_address:
                    # Only use IPv4 addresses (never IPv6) - this prevents "Network is unreachable" errors
                    # Reconstruct netloc with credentials if they existed
                    if creds_part:
                        new_netloc = f"{creds_part}@{ip_address}{port_part}"
                    else:
                        new_netloc = f"{ip_address}{port_part}"
                    
                    # Reconstruct the URL using urlunparse
                    new_parsed = parsed._replace(netloc=new_netloc)
                    new_url = urlunparse(new_parsed)
                    
                    # Validate the new URL
                    if self._validate_database_url(new_url):
                        logger.info(f" Updated DATABASE_URL to use IPv4 address: {ip_address}")
                        return new_url
                    else:
                        logger.warning(f" Generated IPv4 URL is malformed, using original")
                else:
                    # IPv4 resolution failed - log warning but continue with hostname
                    logger.warning(f" IPv4 resolution failed for {hostname} - connection may fail on Render.com")
                    logger.warning(f"   This is likely due to network configuration issues")
                
                # If IPv4 resolution fails, we'll use hostname but it may resolve to IPv6 and fail
                logger.info(f"ℹ️ Using hostname directly: {hostname} (IPv4 resolution failed)")
                        
            except Exception as e:
                logger.warning(f" Error processing DATABASE_URL: {e}")
                logger.debug(f"   Exception details: {type(e).__name__}: {str(e)}")
                import traceback
                logger.debug(f"   Traceback: {traceback.format_exc()}")
        
        return database_url
    
    def _is_sqlite(self, database_url: str) -> bool:
        """Check if the database URL is for SQLite"""
        return database_url.startswith('sqlite:///') or database_url.startswith('sqlite://')
    
    def _create_engine(self, ssl_mode: str = 'prefer') -> Engine:
        """Create database engine with specified SSL mode"""
        database_url = self._get_database_url()
        
        # Check if using SQLite
        is_sqlite = self._is_sqlite(database_url)
        
        # Check if the URL contains IPv6 addresses (shouldn't happen with our new logic, but safety check)
        if '[' in database_url and ']' in database_url:
            logger.error(" IPv6 address detected in database URL - this will cause connection failures")
            logger.error("   IPv6 connections are not supported. Please use hostname or IPv4 address.")
            # Extract hostname from original URL and use that instead
            try:
                # Try to extract the original hostname from the URL
                if '@' in database_url:
                    at_index = database_url.find('@')
                    # Find the hostname part (before any brackets or slashes)
                    host_part = database_url[at_index + 1:]
                    if '/' in host_part:
                        host_part = host_part.split('/')[0]
                    # Extract hostname (before brackets)
                    if '[' in host_part:
                        # This is IPv6, we need to get the original hostname
                        # Unfortunately we can't recover it, so we'll let it fail and log the error
                        logger.error("   Cannot recover hostname from IPv6 URL. Connection will likely fail.")
            except Exception as e:
                logger.warning(f" Error processing IPv6 address: {e}")
        
        # Update SSL mode in connection string (only for PostgreSQL)
        if not is_sqlite:
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
        
        # Enhanced connection configuration - database-specific
        if is_sqlite:
            # SQLite doesn't support PostgreSQL connection arguments
            connect_args = {}
        else:
            # PostgreSQL connection configuration with longer timeouts for Supabase
            # Note: IPv4 enforcement is done at URL resolution level (hostname -> IPv4 IP)
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
        database_url = self._get_database_url()
        is_sqlite = self._is_sqlite(database_url)
        
        # SQLite doesn't use SSL modes
        if is_sqlite:
            logger.info("SQLite detected - skipping SSL mode testing")
            return 'none'
        
        ssl_modes = ['prefer', 'require', 'verify-ca', 'verify-full']
        
        for ssl_mode in ssl_modes:
            try:
                logger.info(f"Testing SSL mode: {ssl_mode}")
                test_engine = self._create_engine(ssl_mode)
                
                if self._test_connection(test_engine):
                    logger.info(f" SSL mode '{ssl_mode}' works")
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
            is_sqlite = self._is_sqlite(database_url)
            
            if not is_sqlite:
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
            
            # Use appropriate connect_args based on database type
            if is_sqlite:
                connect_args = {}
            else:
                connect_args = {
                    'connect_timeout': 30,
                    'application_name': 'fuze_connection_manager_allow_ssl'
                }
            
            test_engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=3,
                max_overflow=5,
                pool_timeout=30,
                pool_recycle=300,
                pool_pre_ping=True,
                echo=False,
                connect_args=connect_args
            )
            
            if self._test_connection(test_engine):
                logger.info(" SSL mode 'allow' works")
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
                    is_sqlite = self._is_sqlite(database_url)
                    
                    # Remove SSL mode completely (only for PostgreSQL)
                    if not is_sqlite:
                        if 'sslmode=' in database_url:
                            base_url = database_url.split('sslmode=')[0]
                            remaining = database_url.split('sslmode=')[1]
                            if '&' in remaining:
                                remaining = '&' + remaining.split('&', 1)[1]
                            else:
                                remaining = ''
                            database_url = base_url + remaining
                            database_url = database_url.rstrip('&?')
                    
                    # Use appropriate connect_args based on database type
                    if is_sqlite:
                        connect_args = {}
                    else:
                        connect_args = {
                            'connect_timeout': 30,  # Increased from 10 to 30 seconds
                            'application_name': 'fuze_connection_manager_no_ssl',
                            'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000'
                        }
                    
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
                        connect_args=connect_args
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
                is_sqlite = self._is_sqlite(database_url)
                
                if not is_sqlite:
                    # Only remove sslmode for PostgreSQL
                    if 'sslmode=' in database_url:
                        base_url = database_url.split('sslmode=')[0]
                        remaining = database_url.split('sslmode=')[1]
                        if '&' in remaining:
                            remaining = '&' + remaining.split('&', 1)[1]
                        else:
                            remaining = ''
                        database_url = base_url + remaining
                        database_url = database_url.rstrip('&?')
                
                # Use appropriate connect_args based on database type
                if is_sqlite:
                    connect_args = {}
                else:
                    connect_args = {
                        'connect_timeout': 30,  # Increased from 10 to 30 seconds
                        'application_name': 'fuze_connection_manager_no_ssl',
                        'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000'
                    }
                
                self._engine = create_engine(
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
            else:
                # Create engine with working SSL mode
                self._engine = self._create_engine(working_ssl_mode)
            
            # Test the final engine
            if not self._test_connection(self._engine):
                raise Exception("Created engine but connection test failed")
            
            self._last_connection_test = current_time
            logger.info(f" Database engine created successfully with SSL mode: {working_ssl_mode}")
            
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
            print(" Database connection successful")
            
            # Get connection info
            info = get_database_info()
            print(f"Connection info: {info}")
        else:
            print(" Database connection failed")
            
    except Exception as e:
        print(f" Error: {e}")
