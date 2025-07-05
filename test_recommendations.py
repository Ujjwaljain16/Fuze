#!/usr/bin/env python3
"""
Test script for recommendations functionality
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_recommendations():
    print("🧪 Testing Recommendations System")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return
    
    # Test 2: Login to get token
    print("\n2. Testing authentication...")
    login_data = {
        "username": "testuser",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("✅ Login successful")
        else:
            print(f"❌ Login failed: {response.status_code}")
            print("Response:", response.text)
            return
    except Exception as e:
        print(f"❌ Login error: {e}")
        return
    
    # Test 3: Get general recommendations
    print("\n3. Testing general recommendations...")
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/api/recommendations/general", headers=headers)
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get("recommendations", [])
            print(f"✅ General recommendations: {len(recommendations)} items found")
            
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"   {i}. {rec.get('title', 'No title')}")
                print(f"      Score: {rec.get('score', 'N/A')}%")
                print(f"      Reason: {rec.get('reason', 'No reason provided')}")
                print()
        else:
            print(f"❌ General recommendations failed: {response.status_code}")
            print("Response:", response.text)
    except Exception as e:
        print(f"❌ General recommendations error: {e}")
    
    # Test 4: Submit feedback
    print("\n4. Testing feedback submission...")
    feedback_data = {
        "content_id": 1,
        "feedback_type": "relevant"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/recommendations/feedback", 
                               json=feedback_data, headers=headers)
        if response.status_code == 200:
            print("✅ Feedback submitted successfully")
        else:
            print(f"❌ Feedback submission failed: {response.status_code}")
            print("Response:", response.text)
    except Exception as e:
        print(f"❌ Feedback submission error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Recommendations testing completed!")
    print("\nTo test the frontend:")
    print("1. Backend is running on: http://localhost:5000")
    print("2. Frontend is running on: http://localhost:5173")
    print("3. Open http://localhost:5173 in your browser")
    print("4. Login and navigate to the Recommendations page")

if __name__ == "__main__":
    test_recommendations() 