#!/usr/bin/env python3
"""
Test database performance to see what's slow
"""

import requests
import time

def test_simple_operations():
    """Test simple operations that don't require database writes"""
    print("🧪 Testing Simple Operations...")
    
    # Test 1: Simple GET request
    try:
        start = time.time()
        response = requests.get("http://localhost:5000/", timeout=10)
        duration = time.time() - start
        print(f"   ✅ Simple GET: {duration:.2f}s")
    except Exception as e:
        print(f"   ❌ Simple GET failed: {e}")
    
    # Test 2: Profile endpoint (should be fast, just returns 401)
    try:
        start = time.time()
        response = requests.get("http://localhost:5000/api/profile", timeout=10)
        duration = time.time() - start
        print(f"   ✅ Profile GET: {duration:.2f}s (status: {response.status_code})")
    except Exception as e:
        print(f"   ❌ Profile GET failed: {e}")

def test_database_operations():
    """Test operations that require database access"""
    print("\n🗄️ Testing Database Operations...")
    
    # Test 1: Try to get recommendations without auth (should fail fast)
    try:
        start = time.time()
        response = requests.get("http://localhost:5000/api/recommendations/gemini-status", timeout=10)
        duration = time.time() - start
        print(f"   ✅ Recommendations GET: {duration:.2f}s (status: {response.status_code})")
    except Exception as e:
        print(f"   ❌ Recommendations GET failed: {e}")
    
    # Test 2: Try login with wrong credentials (should fail fast)
    try:
        start = time.time()
        response = requests.post("http://localhost:5000/api/auth/login", 
                               json={"username": "nonexistent", "password": "wrong"}, 
                               timeout=10)
        duration = time.time() - start
        print(f"   ✅ Wrong login: {duration:.2f}s (status: {response.status_code})")
    except Exception as e:
        print(f"   ❌ Wrong login failed: {e}")

def test_with_existing_user():
    """Test with a user that might exist"""
    print("\n👤 Testing with Existing User...")
    
    # Try to login with a user that might exist
    try:
        start = time.time()
        response = requests.post("http://localhost:5000/api/auth/login", 
                               json={"username": "admin", "password": "admin"}, 
                               timeout=15)
        duration = time.time() - start
        
        if response.status_code == 200:
            print(f"   ✅ Admin login: {duration:.2f}s - SUCCESS!")
            return response.json().get('access_token')
        elif response.status_code == 401:
            print(f"   ⚠️ Admin login: {duration:.2f}s - Wrong credentials")
        else:
            print(f"   ❌ Admin login: {duration:.2f}s - Status: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("   ❌ Admin login: TIMEOUT after 15s")
    except Exception as e:
        print(f"   ❌ Admin login failed: {e}")
    
    return None

def main():
    """Main test function"""
    print("🚀 Database Performance Test")
    print("=" * 50)
    
    # Test simple operations
    test_simple_operations()
    
    # Test database operations
    test_database_operations()
    
    # Test with existing user
    token = test_with_existing_user()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")
    
    if token:
        print("\n🎉 Found working user!")
        print("💡 Now we can test recommendations with this token")
    else:
        print("\n❌ No working user found")
        print("💡 The issue is database performance during login/registration")
        print("💡 Check your Supabase dashboard for database performance")

if __name__ == "__main__":
    main()
