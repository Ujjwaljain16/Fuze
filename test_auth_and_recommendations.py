#!/usr/bin/env python3
"""
Test script to verify authentication and recommendations are working
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:5000"
TEST_USER = {
    "username": "testuser",
    "email": "test@example.com", 
    "password": "testpass123"
}

def test_auth_flow():
    """Test the complete authentication flow"""
    print("🔐 Testing Authentication Flow...")
    
    # 1. Test registration
    print("\n1. Testing user registration...")
    try:
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json=TEST_USER)
        if reg_response.status_code in [201, 409]:  # 409 means user already exists
            print(f"✅ Registration: {reg_response.status_code} - User created or already exists")
        else:
            print(f"❌ Registration failed: {reg_response.status_code} - {reg_response.text}")
            return None
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return None
    
    # 2. Test login
    print("\n2. Testing user login...")
    try:
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        })
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            access_token = login_data.get('access_token')
            user_data = login_data.get('user')
            print(f"✅ Login successful for user: {user_data.get('username')}")
            print(f"   User ID: {user_data.get('id')}")
            print(f"   Token: {access_token[:20]}...")
            return access_token, user_data.get('id')
        else:
            print(f"❌ Login failed: {login_response.status_code} - {login_response.text}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_recommendations_with_auth(token, user_id):
    """Test recommendations endpoints with authentication"""
    print(f"\n🎯 Testing Recommendations with Authentication...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test data for recommendations
    test_data = {
        "title": "React Learning Project",
        "description": "Building a modern web application with React",
        "technologies": "JavaScript, React, Node.js",
        "user_interests": "Frontend development, state management",
        "max_recommendations": 5,
        "engine_preference": "auto",
        "diversity_weight": 0.3,
        "quality_threshold": 6,
        "include_global_content": True
    }
    
    # Test unified orchestrator endpoint
    print("\n1. Testing Unified Orchestrator endpoint...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/recommendations/unified-orchestrator",
            json=test_data,
            headers=headers
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print(f"   ✅ Success! Got {len(recommendations)} recommendations")
            print(f"   Engine used: {data.get('engine_used', 'Unknown')}")
            
            # Show first recommendation details
            if recommendations:
                first_rec = recommendations[0]
                print(f"   First recommendation:")
                print(f"     Title: {first_rec.get('title', 'N/A')}")
                print(f"     Score: {first_rec.get('score', 'N/A')}")
                print(f"     Engine: {first_rec.get('engine_used', 'N/A')}")
        else:
            print(f"   ❌ Failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test ensemble endpoint
    print("\n2. Testing Ensemble endpoint...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/recommendations/ensemble",
            json=test_data,
            headers=headers
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print(f"   ✅ Success! Got {len(recommendations)} recommendations")
            print(f"   Engine used: {data.get('engine_used', 'Unknown')}")
        else:
            print(f"   ❌ Failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test gemini status endpoint
    print("\n3. Testing Gemini Status endpoint...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/recommendations/gemini-status",
            headers=headers
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success! Gemini available: {data.get('gemini_available', False)}")
            print(f"   Status: {data.get('status', 'Unknown')}")
        else:
            print(f"   ❌ Failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_without_auth():
    """Test recommendations without authentication (should fail)"""
    print(f"\n🚫 Testing Recommendations WITHOUT Authentication...")
    
    test_data = {
        "title": "Test Project",
        "description": "Test description",
        "technologies": "Test tech",
        "max_recommendations": 3
    }
    
    # Test unified orchestrator without auth
    print("\n1. Testing Unified Orchestrator without auth...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/recommendations/unified-orchestrator",
            json=test_data
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print(f"   ✅ Correctly rejected (401 Unauthorized)")
        else:
            print(f"   ⚠️ Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    """Main test function"""
    print("🚀 Starting Authentication and Recommendations Test")
    print("=" * 60)
    
    # Test authentication flow
    auth_result = test_auth_flow()
    if not auth_result:
        print("\n❌ Authentication test failed. Cannot proceed with recommendations test.")
        return
    
    token, user_id = auth_result
    
    # Test recommendations with authentication
    test_recommendations_with_auth(token, user_id)
    
    # Test without authentication
    test_without_auth()
    
    print("\n" + "=" * 60)
    print("🏁 Test completed!")

if __name__ == "__main__":
    main()
