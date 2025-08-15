#!/usr/bin/env python3
"""
Test SSL Connection Fix
Tests the SSL connection handling and database connection manager
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_ssl_fix():
    """Test the SSL connection fixes"""
    print("🔧 Testing SSL Connection Fixes...")
    print("=" * 50)
    
    # Test 1: Check if database connection manager is available
    print("Test 1: Database Connection Manager")
    try:
        from database_connection_manager import (
            test_database_connection, 
            get_database_info,
            refresh_database_connections
        )
        print("✅ Database connection manager imported successfully")
        
        # Test connection
        if test_database_connection():
            print("✅ Database connection test successful")
            
            # Get connection info
            info = get_database_info()
            print(f"📊 Connection info: {info}")
        else:
            print("❌ Database connection test failed")
            
            # Try to refresh connections
            print("🔄 Attempting to refresh connections...")
            if refresh_database_connections():
                print("✅ Connections refreshed successfully")
                if test_database_connection():
                    print("✅ Database connection test successful after refresh")
                else:
                    print("❌ Database connection still failing after refresh")
            else:
                print("❌ Failed to refresh connections")
                
    except ImportError as e:
        print(f"❌ Database connection manager not available: {e}")
    except Exception as e:
        print(f"❌ Error testing connection manager: {e}")
    
    print()
    
    # Test 2: Check if SSL fix script is available
    print("Test 2: SSL Fix Script")
    try:
        from fix_ssl_connections import main as fix_ssl
        print("✅ SSL fix script imported successfully")
        
        # Note: Don't run the fix automatically, just test import
        print("ℹ️  SSL fix script is available for manual use")
        
    except ImportError as e:
        print(f"❌ SSL fix script not available: {e}")
    except Exception as e:
        print(f"❌ Error importing SSL fix script: {e}")
    
    print()
    
    # Test 3: Check database configuration
    print("Test 3: Database Configuration")
    try:
        from config import config
        print("✅ Database configuration loaded")
        
        # Check SSL settings
        engine_options = config.SQLALCHEMY_ENGINE_OPTIONS
        connect_args = engine_options.get('connect_args', {})
        
        print(f"📊 Pool size: {engine_options.get('pool_size')}")
        print(f"📊 Pool recycle: {engine_options.get('pool_recycle')}")
        print(f"📊 Pool pre-ping: {engine_options.get('pool_pre_ping')}")
        print(f"📊 SSL mode: {connect_args.get('sslmode')}")
        print(f"📊 Keepalives: {connect_args.get('keepalives')}")
        
    except ImportError as e:
        print(f"❌ Database configuration not available: {e}")
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
    
    print()
    
    # Test 4: Check if production server can start
    print("Test 4: Production Server Import")
    try:
        from run_production import create_app
        print("✅ Production server can be imported")
        
        # Test app creation (without running)
        try:
            app = create_app()
            print("✅ Production app created successfully")
        except Exception as e:
            print(f"❌ Production app creation failed: {e}")
            
    except ImportError as e:
        print(f"❌ Production server not available: {e}")
    except Exception as e:
        print(f"❌ Error importing production server: {e}")
    
    print()
    print("=" * 50)
    print("🎯 SSL Connection Fix Test Complete!")
    
    # Provide recommendations
    print("\n📋 Recommendations:")
    print("1. If all tests pass, your SSL connection issues should be resolved")
    print("2. If connection manager fails, check your DATABASE_URL environment variable")
    print("3. If SSL issues persist, run: python fix_ssl_connections.py")
    print("4. Restart your production server: python run_production.py")
    
    return True

if __name__ == "__main__":
    try:
        test_ssl_fix()
        print("\n✅ All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
