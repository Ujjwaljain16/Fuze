#!/usr/bin/env python3
"""
Simple Recommendations Test
Test if server is running and basic endpoints work
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def test_simple_recommendations():
    """Test basic server connectivity and recommendations"""
    print("🎯 Simple Recommendations Test")
    print("=" * 40)
    
    # Test if server is running
    print("🔍 Testing server connectivity...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"✅ Server is running (status: {response.status_code})")
    except Exception as e:
        print(f"❌ Server not running: {e}")
        return
    
    # Test login
    print("\n🔍 Testing login...")
    login_data = {
        "email": "jainujjwal1609@gmail.com",
        "password": "Jainsahab@16"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data, timeout=10)
        print(f"Login response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')  # Changed from 'token' to 'access_token'
            if token:
                print("✅ Login successful, got token")
                headers = {'Authorization': f'Bearer {token}'}
            else:
                print("❌ No token in response")
                print(f"Response: {data}")
                return
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"Response: {response.text}")
            return
    except Exception as e:
        print(f"❌ Login error: {e}")
        return
    
    # Test optimized recommendations (GET method)
    print("\n🔍 Testing Optimized Recommendations (GET):")
    print("-" * 40)
    
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/recommendations/optimized", headers=headers, timeout=30)
        end_time = time.time()
        
        print(f"Response status: {response.status_code}")
        print(f"Response time: {end_time - start_time:.3f}s")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            engine = data.get('engine', 'unknown')
            
            print(f"✅ Success: {len(recommendations)} recommendations")
            print(f"   Engine: {engine}")
            
            if recommendations:
                print("   Sample recommendations:")
                for i, rec in enumerate(recommendations[:2]):
                    title = rec.get('title', 'No title')[:50]
                    reason = rec.get('reason', 'No reason')[:50]
                    print(f"     {i+1}. {title}...")
                    print(f"        Reason: {reason}...")
            else:
                print("   ⚠️ No recommendations returned")
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Request error: {e}")
    
    print("\n" + "=" * 40)
    print("🎯 Simple Test Complete!")
    print("=" * 40)

if __name__ == "__main__":
    test_simple_recommendations() 