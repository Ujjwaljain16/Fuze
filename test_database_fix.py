#!/usr/bin/env python3
"""
Test script to verify database connection fixes work correctly
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_hostname_resolution():
    """Test hostname resolution with IPv4 fallback"""
    print("🔍 Testing hostname resolution...")
    
    try:
        from database_connection_manager import DatabaseConnectionManager
        
        manager = DatabaseConnectionManager()
        
        # Test with Supabase hostname
        test_hostname = "db.xqfgfalwwfwtzvuuvroq.supabase.co"
        ip_address = manager._resolve_hostname_with_fallback(test_hostname)
        
        if ip_address:
            print(f"✅ Hostname resolution working: {test_hostname} -> {ip_address}")
            
            # Check if it's IPv4 (preferred)
            if ':' in ip_address and ip_address.count(':') > 1:
                print(f"⚠️ Got IPv6 address: {ip_address}")
            else:
                print(f"✅ Got IPv4 address: {ip_address}")
            
            return True
        else:
            print(f"❌ Hostname resolution failed for {test_hostname}")
            return False
            
    except Exception as e:
        print(f"❌ Hostname resolution error: {e}")
        return False

def test_database_url_processing():
    """Test database URL processing and IP replacement"""
    print("\n🔍 Testing database URL processing...")
    
    try:
        from database_connection_manager import DatabaseConnectionManager
        
        manager = DatabaseConnectionManager()
        
        # Test with the actual DATABASE_URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found in environment")
            return False
        
        print(f"Original DATABASE_URL: {database_url[:50]}...")
        
        # Process the URL
        processed_url = manager._get_database_url()
        
        if processed_url != database_url:
            print(f"✅ URL processed successfully")
            print(f"Processed URL: {processed_url[:50]}...")
            
            # Validate the processed URL
            if manager._validate_database_url(processed_url):
                print("✅ Processed URL is valid")
                return True
            else:
                print("❌ Processed URL is invalid")
                return False
        else:
            print("ℹ️ URL unchanged (no hostname resolution needed)")
            return True
            
    except Exception as e:
        print(f"❌ Database URL processing error: {e}")
        return False

def test_database_connection():
    """Test actual database connection"""
    print("\n🔍 Testing database connection...")
    
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

def test_connection_manager_initialization():
    """Test connection manager initialization"""
    print("\n🔍 Testing connection manager initialization...")
    
    try:
        from database_connection_manager import DatabaseConnectionManager
        
        manager = DatabaseConnectionManager()
        print("✅ Connection manager initialized successfully")
        
        # Test getting engine (this will trigger hostname resolution)
        try:
            engine = manager.get_engine()
            print("✅ Database engine created successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to create database engine: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Connection manager initialization error: {e}")
        return False

def test_ipv6_handling():
    """Test IPv6 address handling"""
    print("\n🔍 Testing IPv6 address handling...")
    
    try:
        from database_connection_manager import DatabaseConnectionManager
        
        manager = DatabaseConnectionManager()
        
        # Test with a known IPv6 hostname
        test_hostname = "ipv6.google.com"
        ip_address = manager._resolve_hostname_with_fallback(test_hostname)
        
        if ip_address:
            print(f"✅ IPv6 resolution working: {test_hostname} -> {ip_address}")
            
            # Test URL validation with IPv6
            test_url = f"postgresql://user:pass@[{ip_address}]:5432/db"
            if manager._validate_database_url(test_url):
                print("✅ IPv6 URL validation working")
                return True
            else:
                print("❌ IPv6 URL validation failed")
                return False
        else:
            print(f"⚠️ IPv6 resolution not available for {test_hostname}")
            return True  # Not a failure if IPv6 is not available
            
    except Exception as e:
        print(f"❌ IPv6 handling error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Database Connection Fixes...")
    print("=" * 60)
    
    tests = [
        ("Hostname Resolution", test_hostname_resolution),
        ("Database URL Processing", test_database_url_processing),
        ("Database Connection", test_database_connection),
        ("Connection Manager", test_connection_manager_initialization),
        ("IPv6 Handling", test_ipv6_handling)
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
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All database fixes are working correctly!")
        return True
    else:
        print("⚠️ Some database fixes need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
