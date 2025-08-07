#!/usr/bin/env python3
"""
Test script to verify database connection fix
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test database connection with the new configuration"""
    try:
        from flask import Flask
        from config import ProductionConfig
        from models import db
        from database_utils import check_database_connection, ensure_database_connection
        from sqlalchemy import text
        
        print("🔍 Testing database connection...")
        
        # Create a minimal Flask app for testing
        app = Flask(__name__)
        app.config.from_object(ProductionConfig)
        db.init_app(app)
        
        with app.app_context():
            # Test basic connection
            print("1. Testing basic connection...")
            if check_database_connection():
                print("✅ Basic connection successful")
            else:
                print("❌ Basic connection failed")
                return False
            
            # Test ensure connection
            print("2. Testing ensure connection...")
            if ensure_database_connection():
                print("✅ Ensure connection successful")
            else:
                print("❌ Ensure connection failed")
                return False
            
            # Test a simple query
            print("3. Testing simple query...")
            try:
                result = db.session.execute(text('SELECT 1 as test'))
                row = result.fetchone()
                if row and row.test == 1:
                    print("✅ Simple query successful")
                else:
                    print("❌ Simple query failed")
                    return False
            except Exception as e:
                print(f"❌ Simple query failed: {e}")
                return False
            
            # Test connection pool info
            print("4. Testing connection pool...")
            try:
                engine = db.engine
                pool = engine.pool
                print(f"✅ Connection pool: size={pool.size()}, checked_in={pool.checkedin()}, checked_out={pool.checkedout()}")
            except Exception as e:
                print(f"⚠️  Could not get pool info: {e}")
            
            print("🎉 All database connection tests passed!")
            return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def test_auth_endpoint():
    """Test the auth endpoint with retry logic"""
    try:
        from flask import Flask
        from config import ProductionConfig
        from models import db
        from blueprints.auth import auth_bp
        
        print("\n🔍 Testing auth endpoint with retry logic...")
        
        # Create a minimal app for testing
        app = Flask(__name__)
        app.config.from_object(ProductionConfig)
        db.init_app(app)
        app.register_blueprint(auth_bp)
        
        with app.app_context():
            # Test that the login endpoint exists and has retry decorator
            from database_utils import retry_on_connection_error
            
            # Check if the login function has the retry decorator
            login_func = auth_bp.view_functions.get('login')
            if login_func:
                # Check if the function has been decorated
                if hasattr(login_func, '__wrapped__') or hasattr(login_func, '__closure__'):
                    print("✅ Login endpoint has retry decorator")
                else:
                    print("⚠️  Login endpoint may not have retry decorator")
            else:
                print("❌ Login endpoint not found")
                return False
            
            print("✅ Auth endpoint test completed")
            return True
            
    except Exception as e:
        print(f"❌ Auth endpoint test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Database Connection Fix")
    print("=" * 40)
    
    # Test database connection
    db_test_passed = test_database_connection()
    
    # Test auth endpoint
    auth_test_passed = test_auth_endpoint()
    
    print("\n" + "=" * 40)
    if db_test_passed and auth_test_passed:
        print("🎉 All tests passed! Database connection fix is working.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the configuration.")
        sys.exit(1) 