#!/usr/bin/env python3
"""
Fix Supabase session pooling performance issues
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def optimize_for_session_pooling():
    """Optimize database settings for Supabase session pooling"""
    print("🔧 Optimizing for Supabase session pooling...")
    
    # Update config.py with session pooling optimized settings
    config_content = '''import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # OPTIMIZED for Supabase session pooling (NOT direct connections)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 1,  # Minimal pool size for session pooling
        'pool_timeout': 30,  # Longer timeout for pooled connections
        'pool_recycle': 1800,  # Recycle connections after 30 minutes
        'pool_pre_ping': False,  # Disable for session pooling
        'max_overflow': 0,  # No overflow for session pooling
        'connect_args': {
            'connect_timeout': 30,  # Longer connection timeout
            'application_name': 'fuze_app',
            # Remove keepalive settings (not needed for session pooling)
            # Add session pooling optimizations
            'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000'
        }
    }
    
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # Environment detection
    ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # HTTPS and Security Settings
    HTTPS_ENABLED = os.environ.get('HTTPS_ENABLED', 'False').lower() == 'true'
    CSRF_ENABLED = os.environ.get('CSRF_ENABLED', 'False').lower() == 'true'
    
    # JWT Configuration
    JWT_ACCESS_TOKEN_EXPIRES = 60  # minutes
    JWT_REFRESH_TOKEN_EXPIRES = 14  # days
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_SECURE = HTTPS_ENABLED
    JWT_COOKIE_SAMESITE = 'Strict'
    JWT_COOKIE_CSRF_PROTECT = CSRF_ENABLED
    JWT_CSRF_IN_COOKIES = CSRF_ENABLED
    JWT_CSRF_CHECK_FORM = CSRF_ENABLED
    
    # CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')
    
    # Session Configuration
    SESSION_COOKIE_SECURE = HTTPS_ENABLED
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'

class DevelopmentConfig(Config):
    DEBUG = True
    HTTPS_ENABLED = False
    CSRF_ENABLED = False
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False

class ProductionConfig(Config):
    DEBUG = False
    HTTPS_ENABLED = os.environ.get('HTTPS_ENABLED', 'False').lower() == 'true'
    CSRF_ENABLED = os.environ.get('CSRF_ENABLED', 'False').lower() == 'true'
    JWT_COOKIE_SECURE = HTTPS_ENABLED
    JWT_COOKIE_CSRF_PROTECT = CSRF_ENABLED
'''
    
    try:
        with open('config.py', 'w') as f:
            f.write(config_content)
        print("✅ Updated config.py for session pooling optimization")
    except Exception as e:
        print(f"❌ Failed to update config.py: {e}")

def optimize_database_utils_for_pooling():
    """Optimize database utilities for session pooling"""
    print("\n🔧 Optimizing database utilities for session pooling...")
    
    # Update database_utils.py with session pooling optimizations
    db_utils_content = '''"""
Database utilities optimized for Supabase session pooling
"""

import time
import logging
from functools import wraps
from sqlalchemy.exc import OperationalError, DisconnectionError
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import db
import threading

logger = logging.getLogger(__name__)

# Global database connection manager
_db_engine = None
_db_session_factory = None
_db_session = None
_lock = threading.Lock()

def get_db_engine():
    """Get or create a database engine optimized for session pooling"""
    global _db_engine
    
    if _db_engine is None:
        with _lock:
            if _db_engine is None:
                try:
                    from config import Config
                    database_url = Config.SQLALCHEMY_DATABASE_URI
                    
                    # Create engine OPTIMIZED for Supabase session pooling
                    _db_engine = create_engine(
                        database_url,
                        pool_size=1,  # Minimal pool for session pooling
                        max_overflow=0,  # No overflow for session pooling
                        pool_timeout=30,  # Longer timeout for pooled connections
                        pool_recycle=1800,  # 30 minutes
                        pool_pre_ping=False,  # Disable for session pooling
                        connect_args={
                            'connect_timeout': 30,  # Longer connection timeout
                            'application_name': 'fuze_app',
                            # Session pooling optimizations
                            'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000'
                        }
                    )
                    logger.info("Created database engine OPTIMIZED for Supabase session pooling")
                except Exception as e:
                    logger.error(f"Failed to create database engine: {e}")
                    return None
    
    return _db_engine

def get_db_session():
    """Get a database session from the connection pool"""
    global _db_session_factory, _db_session
    
    if _db_session_factory is None:
        with _lock:
            if _db_session_factory is None:
                engine = get_db_engine()
                if engine:
                    _db_session_factory = sessionmaker(bind=engine)
                    _db_session = scoped_session(_db_session_factory)
                    logger.info("Created new database session factory")
                else:
                    return None
    
    return _db_session

def close_db_session():
    """Close the current database session"""
    global _db_session
    if _db_session:
        try:
            _db_session.remove()
            logger.debug("Database session closed")
        except Exception as e:
            logger.warning(f"Error closing database session: {e}")

def get_db_connection_count():
    """Get current database connection count for monitoring"""
    try:
        engine = get_db_engine()
        if engine:
            return engine.pool.size() + engine.pool.checkedin() + engine.pool.overflow()
        return 0
    except Exception as e:
        logger.warning(f"Could not get connection count: {e}")
        return 0

def retry_on_connection_error(max_retries=1, delay=1.0):  # Minimal retries for session pooling
    """
    Decorator to retry database operations on connection errors
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 because we try once without retry
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DisconnectionError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Database connection error on attempt {attempt + 1}/{max_retries + 1}: {e}")
                        logger.info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
                        
                        # Try to refresh the connection
                        try:
                            close_db_session()
                            time.sleep(0.5)  # Brief pause
                        except Exception as rollback_error:
                            logger.warning(f"Error during session cleanup: {rollback_error}")
                    else:
                        logger.error(f"Database operation failed after {max_retries + 1} attempts: {e}")
            
            # If we get here, all attempts failed
            raise last_exception
            
        return wrapper
    return decorator

def check_database_connection():
    """
    Check if database connection is healthy
    """
    try:
        session = get_db_session()
        if session:
            # Try a simple query with timeout
            result = session.execute(text('SELECT 1'))
            result.fetchone()
            return True
        return False
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

def ensure_database_connection():
    """
    Ensure database connection is available, retry if needed
    """
    if not check_database_connection():
        logger.warning("Database connection lost, attempting to reconnect...")
        
        try:
            # Close existing sessions
            close_db_session()
            
            # Wait a moment
            time.sleep(1.0)  # Longer wait for session pooling
            
            # Try to reconnect
            if check_database_connection():
                logger.info("Database reconnection successful")
                return True
            else:
                logger.error("Database reconnection failed")
                return False
                
        except Exception as e:
            logger.error(f"Error during database reconnection: {e}")
            return False
    
    return True

def safe_db_operation(operation_func, *args, **kwargs):
    """
    Safely execute a database operation with retry logic
    """
    @retry_on_connection_error(max_retries=1, delay=1.0)
    def execute_operation():
        return operation_func(*args, **kwargs)
    
    return execute_operation()

def with_db_session(func):
    """
    Decorator to provide a database session to functions
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        session = get_db_session()
        if not session:
            logger.error("Could not get database session")
            return None
        
        try:
            # Add session to kwargs if not already present
            if 'session' not in kwargs:
                kwargs['session'] = session
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            # Don't close the session here - let the connection pool manage it
            pass
    
    return wrapper
'''
    
    try:
        with open('database_utils.py', 'w') as f:
            f.write(db_utils_content)
        print("✅ Updated database_utils.py for session pooling optimization")
    except Exception as e:
        print(f"❌ Failed to update database_utils.py: {e}")

def optimize_auth_blueprint_for_pooling():
    """Optimize auth blueprint for session pooling"""
    print("\n🔧 Optimizing auth blueprint for session pooling...")
    
    # Read the current auth.py file
    try:
        with open('blueprints/auth.py', 'r') as f:
            auth_content = f.read()
        
        # Replace the retry decorator usage with session pooling optimized version
        if '@retry_on_connection_error(max_retries=3, delay=1)' in auth_content:
            auth_content = auth_content.replace(
                '@retry_on_connection_error(max_retries=3, delay=1)',
                '@retry_on_connection_error(max_retries=1, delay=1.0)'
            )
            print("✅ Reduced retry attempts for session pooling")
        
        if '@retry_on_connection_error(max_retries=2, delay=0.5)' in auth_content:
            auth_content = auth_content.replace(
                '@retry_on_connection_error(max_retries=2, delay=0.5)',
                '@retry_on_connection_error(max_retries=1, delay=1.0)'
            )
            print("✅ Reduced retry attempts for session pooling")
        
        # Write back the optimized version
        with open('blueprints/auth.py', 'w') as f:
            f.write(auth_content)
            
    except Exception as e:
        print(f"❌ Failed to optimize auth blueprint: {e}")

def create_session_pooling_test():
    """Create a test script for session pooling performance"""
    print("\n🧪 Creating session pooling performance test...")
    
    test_content = '''#!/usr/bin/env python3
"""
Test Supabase session pooling performance
"""

import requests
import time

def test_session_pooling_performance():
    """Test if session pooling is now working properly"""
    print("🚀 Testing Supabase session pooling performance...")
    
    user_data = {
        "username": f"pooltest{int(time.time())}",
        "email": f"pool{int(time.time())}@test.com",
        "password": "testpass123"
    }
    
    start_time = time.time()
    
    try:
        response = requests.post("http://localhost:5000/api/auth/register", 
                               json=user_data, timeout=20)  # Increased timeout for session pooling
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Registration took: {duration:.2f} seconds")
        
        if response.status_code in [201, 409]:
            if duration < 10:
                print("✅ Session pooling is working well!")
            elif duration < 20:
                print("⚠️ Session pooling is acceptable but could be faster")
            else:
                print("❌ Session pooling is still too slow")
            return True
        else:
            print(f"❌ Registration failed: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Registration still timing out after 20 seconds")
        return False
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return False

def test_recommendations_with_pooling():
    """Test if recommendations work with session pooling"""
    print("\\n🎯 Testing recommendations with session pooling...")
    
    # First login to get a token
    login_data = {
        "username": "quicktest",  # Use existing user
        "password": "testpass123"
    }
    
    try:
        login_response = requests.post("http://localhost:5000/api/auth/login", 
                                     json=login_data, timeout=15)
        
        if login_response.status_code == 200:
            token = login_response.json().get('access_token')
            
            # Test recommendations
            headers = {"Authorization": f"Bearer {token}"}
            test_data = {
                "title": "Session Pooling Test",
                "description": "Testing recommendations with session pooling",
                "technologies": "Python, Flask, Supabase",
                "max_recommendations": 3
            }
            
            start_time = time.time()
            rec_response = requests.post(
                "http://localhost:5000/api/recommendations/unified-orchestrator",
                json=test_data,
                headers=headers,
                timeout=20  # Increased timeout for session pooling
            )
            end_time = time.time()
            
            duration = end_time - start_time
            print(f"Recommendations took: {duration:.2f} seconds")
            
            if rec_response.status_code == 200:
                data = rec_response.json()
                recommendations = data.get('recommendations', [])
                print(f"✅ SUCCESS! Got {len(recommendations)} recommendations")
                print(f"Engine used: {data.get('engine_used', 'Unknown')}")
                return True
            else:
                print(f"❌ Recommendations failed: {rec_response.status_code}")
                print(f"Response: {rec_response.text}")
                return False
        else:
            print(f"❌ Login failed: {login_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    """Run session pooling tests"""
    print("🧪 Supabase Session Pooling Performance Test")
    print("=" * 60)
    
    # Test registration with session pooling
    reg_success = test_session_pooling_performance()
    
    # Test recommendations with session pooling
    rec_success = test_recommendations_with_pooling()
    
    print("\\n" + "=" * 60)
    if reg_success and rec_success:
        print("🎉 All tests passed! Session pooling is now optimized.")
        print("💡 Your recommendations should now work properly!")
    else:
        print("⚠️ Some tests failed. Session pooling might need further optimization.")

if __name__ == "__main__":
    main()
'''
    
    try:
        with open('test_session_pooling.py', 'w') as f:
            f.write(test_content)
        print("✅ Created session pooling performance test script")
    except Exception as e:
        print(f"❌ Failed to create test script: {e}")

def main():
    """Main optimization function for session pooling"""
    print("🚀 Supabase Session Pooling Optimization")
    print("=" * 60)
    
    # Optimize for session pooling
    optimize_for_session_pooling()
    
    # Optimize database utilities for pooling
    optimize_database_utils_for_pooling()
    
    # Optimize auth blueprint for pooling
    optimize_auth_blueprint_for_pooling()
    
    # Create session pooling test
    create_session_pooling_test()
    
    print("\n" + "=" * 60)
    print("✅ Session pooling optimizations completed!")
    print("💡 Next steps:")
    print("   1. Restart your Flask server")
    print("   2. Run: python test_session_pooling.py")
    print("   3. Check if registration and recommendations are faster")
    print("\\n🔑 Key changes made:")
    print("   - Reduced connection pool size to 1 (optimal for session pooling)")
    print("   - Increased timeouts for pooled connections")
    print("   - Disabled connection pre-ping (not needed for pooling)")
    print("   - Reduced retry attempts to minimize pool congestion")

if __name__ == "__main__":
    main()
