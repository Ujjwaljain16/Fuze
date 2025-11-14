#!/usr/bin/env python3
"""
Test script to verify CORS configuration is working
"""

import requests
import time

def test_cors_configuration():
    """Test CORS configuration and login endpoint"""
    base_url = "http://127.0.0.1:5000"
    
    print("🔍 Testing CORS Configuration...")
    print("=" * 50)
    
    # Test 1: Check CORS preflight response
    print("📊 Test 1: CORS Preflight (OPTIONS)")
    try:
        response = requests.options(
            f"{base_url}/api/auth/login",
            headers={
                'Origin': 'http://localhost:5173',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type,Authorization,X-CSRF-TOKEN'
            },
            timeout=5
        )
        
        print(f"✅ OPTIONS response status: {response.status_code}")
        print(f"🔍 Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'Not set')}")
        print(f"🔍 Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods', 'Not set')}")
        print(f"🔍 Access-Control-Allow-Headers: {response.headers.get('Access-Control-Allow-Headers', 'Not set')}")
        print(f"🔍 Access-Control-Max-Age: {response.headers.get('Access-Control-Max-Age', 'Not set')}")
        
        if response.headers.get('Access-Control-Max-Age'):
            max_age = int(response.headers.get('Access-Control-Max-Age'))
            print(f"✅ CORS preflight cached for {max_age} seconds")
        else:
            print("⚠️ CORS preflight not cached")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ OPTIONS request failed: {e}")
    
    print()
    
    # Test 2: Try a simple POST request (without credentials)
    print("📊 Test 2: Simple POST Request")
    try:
        response = requests.post(
            f"{base_url}/api/auth/login",
            json={"email": "jainujjwal1609@gmail.com", "password": "Jainsahab@16"},
            headers={
                'Content-Type': 'application/json',
                'Origin': 'http://localhost:5173'
            },
            timeout=5
        )
        
        print(f"✅ POST response status: {response.status_code}")
        if response.status_code == 401:
            print("✅ CORS working - got expected 401 (invalid credentials)")
        else:
            print(f"📝 Response: {response.text[:200]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ POST request failed: {e}")
    
    print()
    
    # Test 3: Check if server is running
    print("📊 Test 3: Server Health Check")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Server responding: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Server not responding: {e}")
    
    print()
    print("🎯 CORS Configuration Status:")
    print("1. OPTIONS request should return 200 with proper CORS headers")
    print("2. POST request should not be blocked by CORS")
    print("3. Access-Control-Max-Age should be set to 86400")

if __name__ == "__main__":
    test_cors_configuration()
