#!/usr/bin/env python3
"""
Fix database performance issues
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_config():
    """Fix config.py with optimized database settings"""
    print("🔧 Fixing config.py...")
    
    config_content = '''import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'your-jwt-secret-key-here'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Optimized database connection settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,           # Increased from 1
        'pool_timeout': 20,       # Reduced from 30
        'pool_recycle': 300,      # Reduced from 1800 (5 minutes)
        'pool_pre_ping': True,    # Enable pre-ping
        'max_overflow': 10,       # Increased from 0
        'connect_args': {
            'connect_timeout': 10,  # Reduced from 30
            'options': '-c statement_timeout=10000 -c idle_in_transaction_session_timeout=10000'
        }
    }
    
    # CORS settings
    CORS_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:5173',
        'http://127.0.0.1:5173'
    ]
    
    # Redis configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Gemini API
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 3,
        'pool_timeout': 15,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'max_overflow': 5,
        'connect_args': {
            'connect_timeout': 8,
            'options': '-c statement_timeout=8000 -c idle_in_transaction_session_timeout=8000'
        }
    }

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_timeout': 30,
        'pool_recycle': 600,
        'pool_pre_ping': True,
        'max_overflow': 20,
        'connect_args': {
            'connect_timeout': 15,
            'options': '-c statement_timeout=15000 -c idle_in_transaction_session_timeout=15000'
        }
    }

# Use development config by default
config = DevelopmentConfig
'''
    
    try:
        with open('config.py', 'w') as f:
            f.write(config_content)
        print("   ✅ config.py updated with optimized settings")
        return True
    except Exception as e:
        print(f"   ❌ Failed to update config.py: {e}")
        return False

def fix_database_utils():
    """Fix database_utils.py with better connection handling"""
    print("🔧 Fixing database_utils.py...")
    
    db_utils_content = '''import os
import logging
from functools import wraps
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, TimeoutError, DisconnectionError

logger = logging.getLogger(__name__)

def retry_on_connection_error(max_retries=2, delay=0.5):
    """Retry decorator for database operations"""
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
                        logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
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

def get_database_connection():
    """Get a direct database connection for testing"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
            
        engine = create_engine(database_url, 
                             pool_pre_ping=True,
                             pool_recycle=300,
                             connect_args={'connect_timeout': 10})
        
        return engine.connect()
        
    except Exception as e:
        logger.error(f"Failed to create database connection: {e}")
        raise

def test_database_connection():
    """Test database connection and performance"""
    try:
        with get_database_connection() as conn:
            # Test simple query
            start_time = time.time()
            result = conn.execute(text('SELECT 1'))
            duration = time.time() - start_time
            
            print(f"✅ Database connection test: {duration:.3f}s")
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_database_tables():
    """Check if required tables exist"""
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
        print(f"❌ Failed to check tables: {e}")
        return []
'''
    
    try:
        with open('database_utils.py', 'w') as f:
            f.write(db_utils_content)
        print("   ✅ database_utils.py updated with better connection handling")
        return True
    except Exception as e:
        print(f"   ❌ Failed to update database_utils.py: {e}")
        return False

def create_test_script():
    """Create a test script to verify the fixes"""
    print("🔧 Creating test script...")
    
    test_content = '''#!/usr/bin/env python3
"""
Test database performance after fixes
"""

import time
import requests

def test_database_performance():
    """Test if database performance improved"""
    print("🧪 Testing Database Performance After Fixes...")
    
    # Test 1: Simple GET (should be fast)
    try:
        start = time.time()
        response = requests.get("http://localhost:5000/", timeout=10)
        duration = time.time() - start
        print(f"   ✅ Simple GET: {duration:.2f}s")
    except Exception as e:
        print(f"   ❌ Simple GET failed: {e}")
    
    # Test 2: Wrong credentials (should fail fast)
    try:
        start = time.time()
        response = requests.post("http://localhost:5000/api/auth/login", 
                               json={"username": "nonexistent", "password": "wrong"}, 
                               timeout=10)
        duration = time.time() - start
        print(f"   ✅ Wrong login: {duration:.2f}s (status: {response.status_code})")
    except Exception as e:
        print(f"   ❌ Wrong login failed: {e}")
    
    # Test 3: Try with admin user
    try:
        start = time.time()
        response = requests.post("http://localhost:5000/api/auth/login", 
                               json={"username": "admin", "password": "admin"}, 
                               timeout=15)
        duration = time.time() - start
        
        if response.status_code == 200:
            print(f"   ✅ Admin login: {duration:.2f}s - SUCCESS!")
            token = response.json().get('access_token')
            
            # Test recommendations
            print("\\n🎯 Testing recommendations...")
            headers = {"Authorization": f"Bearer {token}"}
            test_data = {
                "title": "Test Project",
                "description": "Testing recommendations",
                "max_recommendations": 3
            }
            
            start = time.time()
            rec_response = requests.post(
                "http://localhost:5000/api/recommendations/unified-orchestrator",
                json=test_data,
                headers=headers,
                timeout=20
            )
            rec_duration = time.time() - start
            
            print(f"   Recommendations: {rec_duration:.2f}s (status: {rec_response.status_code})")
            
            if rec_response.status_code == 200:
                data = rec_response.json()
                recommendations = data.get('recommendations', [])
                print(f"   ✅ Got {len(recommendations)} recommendations!")
            else:
                print(f"   ❌ Recommendations failed: {rec_response.text}")
                
        elif response.status_code == 401:
            print(f"   ⚠️ Admin login: {duration:.2f}s - Wrong credentials")
        else:
            print(f"   ❌ Admin login: {duration:.2f}s - Status: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("   ❌ Admin login: TIMEOUT after 15s")
    except Exception as e:
        print(f"   ❌ Admin login failed: {e}")

def main():
    """Main test function"""
    print("🚀 Database Performance Test After Fixes")
    print("=" * 60)
    
    test_database_performance()
    
    print("\\n" + "=" * 60)
    print("🏁 Test completed!")
    print("\\n💡 If performance improved:")
    print("   - Restart your Flask server")
    print("   - Try the frontend again")
    print("\\n💡 If still slow:")
    print("   - Check Supabase dashboard")
    print("   - Consider upgrading your Supabase plan")

if __name__ == "__main__":
    main()
'''
    
    try:
        with open('test_after_fix.py', 'w') as f:
            f.write(test_content)
        print("   ✅ test_after_fix.py created")
        return True
    except Exception as e:
        print(f"   ❌ Failed to create test script: {e}")
        return False

def main():
    """Main fix function"""
    print("🚀 Database Performance Fix")
    print("=" * 50)
    
    # Fix config.py
    config_fixed = fix_config()
    
    # Fix database_utils.py
    db_utils_fixed = fix_database_utils()
    
    # Create test script
    test_created = create_test_script()
    
    print("\n" + "=" * 50)
    print("🏁 Fix completed!")
    
    if all([config_fixed, db_utils_fixed, test_created]):
        print("\n✅ All files updated successfully!")
        print("\\n💡 Next steps:")
        print("   1. RESTART your Flask server (important!)")
        print("   2. Run: python test_after_fix.py")
        print("   3. Check if performance improved")
        print("\\n💡 If still slow:")
        print("   - Check your Supabase dashboard")
        print("   - Database might be overloaded")
    else:
        print("\n❌ Some fixes failed")
        print("💡 Check the error messages above")

if __name__ == "__main__":
    main()
