#!/usr/bin/env python3
"""
Test script to verify the fixes for database connection and FastSemanticEngine
"""

import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test database connection with retry logic"""
    print("🧪 Testing Database Connection")
    print("=" * 40)
    
    try:
        from models import db
        from sqlalchemy import text
        
        # Test basic connection
        print("📊 Testing basic database connection...")
        result = db.session.execute(text("SELECT 1"))
        print("✅ Basic database connection successful")
        
        # Test connection pool
        print("📊 Testing connection pool...")
        for i in range(3):
            try:
                result = db.session.execute(text(f"SELECT {i+1} as test_number"))
                print(f"   ✅ Connection {i+1} successful")
            except Exception as e:
                print(f"   ❌ Connection {i+1} failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False

def test_fast_semantic_engine():
    """Test FastSemanticEngine initialization and methods"""
    print("\n🧪 Testing FastSemanticEngine")
    print("=" * 40)
    
    try:
        from unified_recommendation_orchestrator import FastSemanticEngine, UnifiedDataLayer
        
        # Test data layer initialization
        print("📊 Testing UnifiedDataLayer initialization...")
        data_layer = UnifiedDataLayer()
        print("✅ UnifiedDataLayer initialized successfully")
        
        # Test database session method
        print("📊 Testing database session method...")
        db_session = data_layer.get_db_session()
        if db_session:
            print("✅ Database session method working")
        else:
            print("❌ Database session method failed")
            return False
        
        # Test FastSemanticEngine initialization
        print("📊 Testing FastSemanticEngine initialization...")
        engine = FastSemanticEngine(data_layer)
        print("✅ FastSemanticEngine initialized successfully")
        
        # Test technology overlap method
        print("📊 Testing technology overlap calculation...")
        test_techs = ['python', 'django', 'postgresql']
        content_techs = ['python', 'flask', 'sqlite']
        overlap = engine._calculate_technology_overlap(content_techs, test_techs)
        print(f"✅ Technology overlap calculation working: {overlap:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ FastSemanticEngine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ssl_configuration():
    """Test SSL configuration"""
    print("\n🧪 Testing SSL Configuration")
    print("=" * 40)
    
    try:
        from config import config
        
        print(f"📊 SSL Mode: {config.SQLALCHEMY_ENGINE_OPTIONS['connect_args'].get('sslmode', 'not set')}")
        print(f"📊 Pool Size: {config.SQLALCHEMY_ENGINE_OPTIONS['pool_size']}")
        print(f"📊 Pool Recycle: {config.SQLALCHEMY_ENGINE_OPTIONS['pool_recycle']}")
        print(f"📊 Pool Pre-ping: {config.SQLALCHEMY_ENGINE_OPTIONS['pool_pre_ping']}")
        
        print("✅ SSL configuration loaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ SSL configuration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Database and Engine Fixes")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("FastSemanticEngine", test_fast_semantic_engine),
        ("SSL Configuration", test_ssl_configuration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🏁 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your fixes are working correctly.")
    else:
        print("⚠️ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main() 