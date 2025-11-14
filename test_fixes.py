#!/usr/bin/env python3
"""
Test script to verify all the fixes work correctly
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test database connection with the new hostname resolution"""
    print("🔍 Testing database connection...")
    
    try:
        from database_connection_manager import test_database_connection
        if test_database_connection():
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_redis_cache():
    """Test Redis cache functionality"""
    print("\n🔍 Testing Redis cache...")
    
    try:
        from redis_utils import redis_cache
        
        if not redis_cache.connected:
            print("⚠️ Redis not connected, skipping cache tests")
            return True
        
        # Test basic cache operations
        test_key = "test_fix_verification"
        test_data = {"test": "data", "timestamp": time.time()}
        
        # Test setex method
        success = redis_cache.setex(test_key, 60, test_data)
        if success:
            print("✅ Redis setex method working")
        else:
            print("❌ Redis setex method failed")
            return False
        
        # Test get method
        cached_data = redis_cache.get(test_key)
        if cached_data and cached_data.get('test') == 'data':
            print("✅ Redis get method working")
        else:
            print("❌ Redis get method failed")
            return False
        
        # Test get_cache method
        cached_data2 = redis_cache.get_cache(test_key)
        if cached_data2 and cached_data2.get('test') == 'data':
            print("✅ Redis get_cache method working")
        else:
            print("❌ Redis get_cache method failed")
            return False
        
        # Clean up
        redis_cache.redis_client.delete(test_key)
        print("✅ Redis cache tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Redis cache error: {e}")
        return False

def test_smart_engine():
    """Test SmartRecommendationEngine initialization"""
    print("\n🔍 Testing SmartRecommendationEngine...")
    
    try:
        from smart_recommendation_engine import SmartRecommendationEngine
        
        # Test initialization with user_id
        engine = SmartRecommendationEngine(user_id=1)
        print("✅ SmartRecommendationEngine initialized successfully")
        
        # Test that it has required methods
        if hasattr(engine, 'get_smart_recommendations'):
            print("✅ SmartRecommendationEngine has required methods")
            return True
        else:
            print("❌ SmartRecommendationEngine missing required methods")
            return False
            
    except Exception as e:
        print(f"❌ SmartRecommendationEngine error: {e}")
        return False

def test_ensemble_engine():
    """Test ensemble engine with smart engine"""
    print("\n🔍 Testing ensemble engine...")
    
    try:
        from ensemble_recommendation_engine import EnsembleRecommendationEngine
        
        # Initialize ensemble engine
        ensemble = EnsembleRecommendationEngine()
        print("✅ Ensemble engine initialized successfully")
        
        # Check if smart engine is loaded as class
        if 'smart' in ensemble.engines and callable(ensemble.engines['smart']):
            print("✅ Smart engine loaded as class (correct)")
            return True
        else:
            print("❌ Smart engine not loaded correctly")
            return False
            
    except Exception as e:
        print(f"❌ Ensemble engine error: {e}")
        return False

def test_hostname_resolution():
    """Test hostname resolution functionality"""
    print("\n🔍 Testing hostname resolution...")
    
    try:
        from database_connection_manager import DatabaseConnectionManager
        
        manager = DatabaseConnectionManager()
        
        # Test with a known hostname
        test_hostname = "google.com"
        ip_address = manager._resolve_hostname(test_hostname)
        
        if ip_address:
            print(f"✅ Hostname resolution working: {test_hostname} -> {ip_address}")
            return True
        else:
            print(f"❌ Hostname resolution failed for {test_hostname}")
            return False
            
    except Exception as e:
        print(f"❌ Hostname resolution error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing all fixes...")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Redis Cache", test_redis_cache),
        ("Smart Engine", test_smart_engine),
        ("Ensemble Engine", test_ensemble_engine),
        ("Hostname Resolution", test_hostname_resolution)
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
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All fixes are working correctly!")
        return True
    else:
        print("⚠️ Some fixes need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 