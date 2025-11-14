#!/usr/bin/env python3
"""
Quick test to create a user and test recommendations
"""

import requests
import json

def create_test_user():
    """Create a test user quickly"""
    print("👤 Creating test user...")
    
    user_data = {
        "username": "quicktest",
        "email": "quick@test.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post("http://localhost:5000/api/auth/register", 
                               json=user_data, timeout=15)
        print(f"Registration status: {response.status_code}")
        
        if response.status_code == 201:
            print("✅ User created successfully")
            return user_data
        elif response.status_code == 409:
            print("✅ User already exists")
            return user_data
        else:
            print(f"❌ Registration failed: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ Registration timeout - database might be slow")
        return None
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return None

def login_user(user_data):
    """Login with the test user"""
    print("\n🔐 Logging in...")
    
    try:
        response = requests.post("http://localhost:5000/api/auth/login", 
                               json=user_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            user_id = data.get('user', {}).get('id')
            print(f"✅ Login successful! User ID: {user_id}")
            return token, user_id
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None, None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None, None

def test_recommendations_with_auth(token):
    """Test recommendations with real authentication"""
    print("\n🎯 Testing recommendations with authentication...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    test_data = {
        "title": "Quick Test Project",
        "description": "Testing recommendations system",
        "technologies": "Python, Flask, React",
        "max_recommendations": 3
    }
    
    try:
        response = requests.post(
            "http://localhost:5000/api/recommendations/unified-orchestrator",
            json=test_data,
            headers=headers,
            timeout=15
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print(f"✅ SUCCESS! Got {len(recommendations)} recommendations")
            print(f"Engine used: {data.get('engine_used', 'Unknown')}")
            
            if recommendations:
                print("\nFirst recommendation:")
                rec = recommendations[0]
                print(f"  Title: {rec.get('title', 'N/A')}")
                print(f"  Score: {rec.get('score', 'N/A')}")
                print(f"  Reason: {rec.get('reason', 'N/A')[:100]}...")
            else:
                print("⚠️ No recommendations returned - this might be the issue!")
                
        elif response.status_code == 500:
            print(f"❌ Server error: {response.text}")
        else:
            print(f"❌ Unexpected status: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ Recommendations request timeout")
    except Exception as e:
        print(f"❌ Recommendations error: {e}")

def main():
    """Main test function"""
    print("🚀 Quick User Test for Recommendations")
    print("=" * 50)
    
    # Create user
    user_data = create_test_user()
    if not user_data:
        print("❌ Cannot proceed without user")
        return
    
    # Login
    token, user_id = login_user(user_data)
    if not token:
        print("❌ Cannot proceed without authentication")
        return
    
    # Test recommendations
    test_recommendations_with_auth(token)
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")

if __name__ == "__main__":
    main()
