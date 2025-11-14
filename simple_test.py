#!/usr/bin/env python3
"""
Simple test to check basic connectivity and identify issues
"""

import requests
import time

def test_basic_connectivity():
    """Test basic server connectivity"""
    print("🌐 Testing basic server connectivity...")
    
    try:
        # Test if server is responding
        response = requests.get("http://localhost:5000/", timeout=5)
        print(f"✅ Server is responding: {response.status_code}")
    except requests.exceptions.Timeout:
        print("❌ Server timeout - server might be overloaded")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection refused - server not running on port 5000")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    
    return True

def test_auth_endpoint():
    """Test auth endpoint without registration"""
    print("\n🔐 Testing auth endpoint...")
    
    try:
        # Test login with invalid credentials (should fail but endpoint should work)
        response = requests.post("http://localhost:5000/api/auth/login", 
                               json={"username": "nonexistent", "password": "wrong"},
                               timeout=10)
        print(f"✅ Auth endpoint responding: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Correctly rejected invalid credentials")
        return True
    except requests.exceptions.Timeout:
        print("❌ Auth endpoint timeout - server might be overloaded")
        return False
    except Exception as e:
        print(f"❌ Auth endpoint error: {e}")
        return False

def test_recommendations_endpoint():
    """Test recommendations endpoint without auth"""
    print("\n🎯 Testing recommendations endpoint without auth...")
    
    try:
        # Test without authentication (should return 401)
        response = requests.post("http://localhost:5000/api/recommendations/unified-orchestrator",
                               json={"title": "test"},
                               timeout=10)
        print(f"✅ Recommendations endpoint responding: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Correctly rejected without authentication")
        return True
    except requests.exceptions.Timeout:
        print("❌ Recommendations endpoint timeout")
        return False
    except Exception as e:
        print(f"❌ Recommendations endpoint error: {e}")
        return False

def test_database_health():
    """Test if database is accessible"""
    print("\n🗄️ Testing database health...")
    
    try:
        # Try to access a simple endpoint that might hit the database
        response = requests.get("http://localhost:5000/api/profile", timeout=10)
        print(f"✅ Profile endpoint responding: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Endpoint working, just needs auth")
        return True
    except requests.exceptions.Timeout:
        print("❌ Database endpoint timeout - database might be slow")
        return False
    except Exception as e:
        print(f"❌ Database endpoint error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Simple Connectivity Test")
    print("=" * 50)
    
    # Test basic connectivity
    if not test_basic_connectivity():
        print("\n❌ Basic connectivity failed. Server might not be running.")
        return
    
    # Test auth endpoint
    if not test_auth_endpoint():
        print("\n❌ Auth endpoint failed. There might be a server issue.")
        return
    
    # Test recommendations endpoint
    if not test_recommendations_endpoint():
        print("\n❌ Recommendations endpoint failed. There might be a routing issue.")
        return
    
    # Test database health
    if not test_database_health():
        print("\n❌ Database health check failed. Database might be slow or down.")
        return
    
    print("\n" + "=" * 50)
    print("✅ All basic tests passed! The issue might be in the registration process.")
    print("💡 Try checking the server logs for any database connection errors.")

if __name__ == "__main__":
    main()
