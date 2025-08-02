#!/usr/bin/env python3
"""
Authentication test script for Fuze application
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = "http://localhost:5000/api"
HEADERS = {
    'Content-Type': 'application/json',
}

def test_health():
    """Test if the API is running"""
    print("🔍 Testing API health...")
    try:
        response = requests.get(f"{BASE_URL.replace('/api', '')}/api/health")
        if response.status_code == 200:
            print("✅ API is running")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False

def test_registration():
    """Test user registration"""
    print("\n📝 Testing user registration...")
    
    # Test data
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", 
                               headers=HEADERS, 
                               json=user_data)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            print("✅ Registration successful")
            return True
        elif response.status_code == 400:
            data = response.json()
            if "already exists" in data.get('message', ''):
                print("ℹ️  User already exists (this is fine)")
                return True
            else:
                print(f"❌ Registration failed: {data}")
                return False
        else:
            print(f"❌ Registration failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return False

def test_login():
    """Test user login"""
    print("\n🔐 Testing user login...")
    
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", 
                               headers=HEADERS, 
                               json=login_data)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            if access_token:
                print("✅ Login successful")
                print(f"Token: {access_token[:20]}...")
                return access_token
            else:
                print("❌ No access token in response")
                return None
        else:
            print(f"❌ Login failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_protected_endpoints(token):
    """Test protected endpoints with token"""
    print("\n🛡️ Testing protected endpoints...")
    
    auth_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    endpoints = [
        '/profile',
        '/projects',
        '/recommendations/gemini-status',
        '/bookmarks'
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", 
                                  headers=auth_headers)
            
            print(f"{endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  ✅ {endpoint} working")
            elif response.status_code == 401:
                print(f"  ❌ {endpoint} unauthorized")
            else:
                print(f"  ⚠️  {endpoint} status: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ {endpoint} error: {e}")

def test_gemini_status(token):
    """Test Gemini status endpoint specifically"""
    print("\n🤖 Testing Gemini status...")
    
    auth_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    try:
        response = requests.get(f"{BASE_URL}/recommendations/gemini-status", 
                              headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Gemini status: {data}")
        else:
            print(f"❌ Gemini status failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Gemini status error: {e}")

def main():
    """Main test function"""
    print("="*60)
    print(" FUZE AUTHENTICATION TEST")
    print("="*60)
    
    # Test API health
    if not test_health():
        print("\n❌ API is not running. Please start the application first:")
        print("   python app.py")
        return
    
    # Test registration
    if not test_registration():
        print("\n❌ Registration test failed")
        return
    
    # Test login
    token = test_login()
    if not token:
        print("\n❌ Login test failed")
        return
    
    # Test protected endpoints
    test_protected_endpoints(token)
    
    # Test Gemini status
    test_gemini_status(token)
    
    print("\n" + "="*60)
    print(" TEST COMPLETED")
    print("="*60)
    
    print("\n📋 Summary:")
    print("- If all tests passed: Your authentication is working correctly")
    print("- If you see 401 errors: Users need to log in again")
    print("- If Gemini status shows 'available': Your API integration is working!")

if __name__ == "__main__":
    main() 