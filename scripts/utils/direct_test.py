#!/usr/bin/env python3
"""
Direct test to see what's actually happening with recommendations
"""

import requests
import json
import time

def test_step_by_step():
    """Test each step to find the exact issue"""
    print("🔍 Direct Test - Step by Step")
    print("=" * 50)
    
    # Step 1: Test if server is running
    print("\n1️⃣ Testing server connectivity...")
    try:
        response = requests.get("http://localhost:5000/", timeout=5)
        print(f"   ✅ Server responding: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Server not responding: {e}")
        return
    
    # Step 2: Test if we can create a user
    print("\n2️⃣ Testing user creation...")
    user_data = {
        "username": f"testuser{int(time.time())}",
        "email": f"test{int(time.time())}@example.com",
        "password": "testpass123"
    }
    
    try:
        start_time = time.time()
        response = requests.post("http://localhost:5000/api/auth/register", 
                               json=user_data, timeout=30)
        duration = time.time() - start_time
        
        print(f"   Registration took: {duration:.2f} seconds")
        print(f"   Status: {response.status_code}")
        
        if response.status_code in [201, 409]:
            print("   ✅ User creation successful")
            username = user_data["username"]
        else:
            print(f"   ❌ User creation failed: {response.text}")
            return
            
    except Exception as e:
        print(f"   ❌ User creation error: {e}")
        return
    
    # Step 3: Test login
    print("\n3️⃣ Testing login...")
    try:
        login_response = requests.post("http://localhost:5000/api/auth/login", 
                                     json=user_data, timeout=15)
        
        if login_response.status_code == 200:
            token = login_response.json().get('access_token')
            print("   ✅ Login successful")
            print(f"   Token: {token[:20]}...")
        else:
            print(f"   ❌ Login failed: {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return
            
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        return
    
    # Step 4: Test recommendations endpoint directly
    print("\n4️⃣ Testing recommendations endpoint...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test with minimal data
    test_data = {
        "title": "Test Project",
        "description": "Testing recommendations",
        "technologies": "Python",
        "max_recommendations": 1
    }
    
    try:
        print("   Sending request to /api/recommendations/unified-orchestrator...")
        start_time = time.time()
        
        response = requests.post(
            "http://localhost:5000/api/recommendations/unified-orchestrator",
            json=test_data,
            headers=headers,
            timeout=30
        )
        
        duration = time.time() - start_time
        print(f"   Request took: {duration:.2f} seconds")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print(f"   ✅ SUCCESS! Got {len(recommendations)} recommendations")
            
            if recommendations:
                rec = recommendations[0]
                print(f"   First recommendation:")
                print(f"     Title: {rec.get('title', 'N/A')}")
                print(f"     Score: {rec.get('score', 'N/A')}")
                print(f"     Engine: {rec.get('engine_used', 'N/A')}")
            else:
                print("   ⚠️ No recommendations returned")
                
        elif response.status_code == 500:
            print(f"   ❌ Server error: {response.text}")
            print("   This means the backend is crashing when processing recommendations")
            
        elif response.status_code == 401:
            print("   ❌ Unauthorized - token issue")
            
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("   ❌ Request timed out after 30 seconds")
        print("   The recommendations system is hanging")
        
    except Exception as e:
        print(f"   ❌ Request error: {e}")
    
    # Step 5: Check server logs
    print("\n5️⃣ Checking for server errors...")
    print("   💡 Check your terminal where the Flask server is running")
    print("   💡 Look for any error messages or stack traces")
    print("   💡 The issue is likely in the server logs")

def test_simple_endpoint():
    """Test a simple endpoint to see if it's a general issue"""
    print("\n🔍 Testing simple endpoint...")
    
    try:
        response = requests.get("http://localhost:5000/api/profile", timeout=10)
        print(f"   Profile endpoint: {response.status_code}")
        
        if response.status_code == 401:
            print("   ✅ Endpoint working, just needs auth")
        else:
            print(f"   ⚠️ Unexpected response: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    """Main test function"""
    print("🚀 Direct Recommendations Test")
    print("=" * 50)
    
    # Test step by step
    test_step_by_step()
    
    # Test simple endpoint
    test_simple_endpoint()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")
    print("\n💡 Based on the results:")
    print("   - If registration is slow: Database connection issue")
    print("   - If recommendations return 500: Backend code error")
    print("   - If recommendations timeout: System hanging")
    print("   - If recommendations return 401: Authentication issue")

if __name__ == "__main__":
    main()
