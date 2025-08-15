#!/usr/bin/env python3
"""
Test script to measure login performance improvements
"""

import requests
import time
import json

def test_login_performance():
    """Test login endpoint performance"""
    base_url = "http://127.0.0.1:5000"
    
    # Test data
    login_data = {
        "email": "test@example.com",  # Replace with actual test user
        "password": "testpassword"    # Replace with actual test password
    }
    
    print("🚀 Testing Login Performance...")
    print("=" * 50)
    
    # Test 1: Measure CORS preflight + login time
    print("📊 Test 1: Full login request (CORS + login)")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        end_time = time.time()
        
        if response.status_code == 200:
            print(f"✅ Login successful in {end_time - start_time:.3f} seconds")
            print(f"📈 Response time: {(end_time - start_time) * 1000:.1f}ms")
        else:
            print(f"❌ Login failed with status {response.status_code}")
            print(f"📝 Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    print()
    
    # Test 2: Measure just the login endpoint (if we can bypass CORS)
    print("📊 Test 2: Login endpoint only (if CORS bypassed)")
    start_time = time.time()
    
    try:
        # Try to make a direct request to see if CORS is optimized
        response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            headers={
                'Content-Type': 'application/json',
                'Origin': 'http://localhost:5173'
            },
            timeout=10
        )
        end_time = time.time()
        
        if response.status_code == 200:
            print(f"✅ Direct login successful in {end_time - start_time:.3f} seconds")
            print(f"📈 Response time: {(end_time - start_time) * 1000:.1f}ms")
        else:
            print(f"❌ Direct login failed with status {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Direct request failed: {e}")
    
    print()
    
    # Test 3: Check CORS headers
    print("📊 Test 3: CORS Headers Analysis")
    try:
        # Make an OPTIONS request to check CORS preflight
        response = requests.options(
            f"{base_url}/api/auth/login",
            headers={'Origin': 'http://localhost:5173'},
            timeout=5
        )
        
        print(f"🔍 OPTIONS response status: {response.status_code}")
        print(f"🔍 Access-Control-Max-Age: {response.headers.get('Access-Control-Max-Age', 'Not set')}")
        print(f"🔍 Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'Not set')}")
        print(f"🔍 Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods', 'Not set')}")
        
        if response.headers.get('Access-Control-Max-Age'):
            max_age = int(response.headers.get('Access-Control-Max-Age'))
            print(f"✅ CORS preflight cached for {max_age} seconds")
        else:
            print("⚠️ CORS preflight not cached (will cause delays)")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ OPTIONS request failed: {e}")
    
    print()
    print("🎯 Performance Recommendations:")
    print("1. CORS preflight should be cached (max-age header)")
    print("2. Login should complete in < 500ms for good UX")
    print("3. Database connections should be optimized")
    print("4. CSRF token initialization should be non-blocking")

if __name__ == "__main__":
    test_login_performance()
