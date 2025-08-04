#!/usr/bin/env python3
"""
Test Original Recommendations
Verify that your original recommendation system is working
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def test_original_recommendations():
    """Test your original recommendation system"""
    print("🎯 Testing Original Recommendation System")
    print("=" * 50)
    
    # Login to get token
    login_data = {
        "email": "jainujjwal1609@gmail.com",
        "password": "Jainsahab@16"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json().get('access_token')
            headers = {'Authorization': f'Bearer {token}'}
            print("✅ Got auth token")
        else:
            print(f"❌ Login failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Login error: {e}")
        return
    
    # Test general recommendations (your original endpoint)
    print("\n🔍 Testing General Recommendations (Original):")
    print("-" * 50)
    
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/recommendations/general", headers=headers)
        end_time = time.time()
        
        print(f"Response status: {response.status_code}")
        print(f"Response time: {end_time - start_time:.3f}s")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            
            print(f"✅ Success: {len(recommendations)} recommendations")
            
            if recommendations:
                print("   Sample recommendations:")
                for i, rec in enumerate(recommendations[:3]):
                    title = rec.get('title', 'No title')[:50]
                    reason = rec.get('reason', 'No reason')[:50]
                    print(f"     {i+1}. {title}...")
                    print(f"        Reason: {reason}...")
            else:
                print("   ⚠️ No recommendations returned")
                print(f"   Message: {data.get('message', 'No message')}")
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Request error: {e}")
    
    # Test project recommendations (your original endpoint)
    print("\n🔍 Testing Project Recommendations (Original):")
    print("-" * 50)
    
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/recommendations/project/1", headers=headers)
        end_time = time.time()
        
        print(f"Response status: {response.status_code}")
        print(f"Response time: {end_time - start_time:.3f}s")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            
            print(f"✅ Success: {len(recommendations)} recommendations")
            
            if recommendations:
                print("   Sample recommendations:")
                for i, rec in enumerate(recommendations[:3]):
                    title = rec.get('title', 'No title')[:50]
                    reason = rec.get('reason', 'No reason')[:50]
                    print(f"     {i+1}. {title}...")
                    print(f"        Reason: {reason}...")
            else:
                print("   ⚠️ No recommendations returned")
                print(f"   Message: {data.get('message', 'No message')}")
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Request error: {e}")
    
    # Test Gemini-enhanced recommendations
    print("\n🔍 Testing Gemini-Enhanced Recommendations:")
    print("-" * 50)
    
    start_time = time.time()
    try:
        data = {
            'title': 'Test Recommendations',
            'description': 'Testing Gemini-enhanced recommendations',
            'technologies': 'javascript, react, python',
            'user_interests': 'web development, machine learning'
        }
        
        response = requests.post(f"{BASE_URL}/api/recommendations/gemini-enhanced", headers=headers, json=data)
        end_time = time.time()
        
        print(f"Response status: {response.status_code}")
        print(f"Response time: {end_time - start_time:.3f}s")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            
            print(f"✅ Success: {len(recommendations)} recommendations")
            
            if recommendations:
                print("   Sample recommendations:")
                for i, rec in enumerate(recommendations[:3]):
                    title = rec.get('title', 'No title')[:50]
                    reason = rec.get('reason', 'No reason')[:50]
                    print(f"     {i+1}. {title}...")
                    print(f"        Reason: {reason}...")
            else:
                print("   ⚠️ No recommendations returned")
                print(f"   Message: {data.get('message', 'No message')}")
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Request error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Original Recommendation System Test Complete!")
    print("=" * 50)

if __name__ == "__main__":
    test_original_recommendations() 