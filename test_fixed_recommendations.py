#!/usr/bin/env python3
"""
Test Fixed Recommendations
Verify that recommendations work after removing user_id filter
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def test_fixed_recommendations():
    """Test that recommendations now work"""
    print("🎯 Testing Fixed Recommendations")
    print("=" * 40)
    
    # Login to get token
    login_data = {
        "email": "jainujjwal1609@gmail.com",
        "password": "Jainsahab@16"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json().get('access_token')  # Fixed: use access_token
            headers = {'Authorization': f'Bearer {token}'}
            print("✅ Got auth token")
        else:
            print(f"❌ Login failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Login error: {e}")
        return
    
    # Test ultra-fast recommendations
    print("\n🔍 Testing Ultra-Fast Recommendations:")
    print("-" * 40)
    
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/recommendations/optimized", headers=headers)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            engine = data.get('engine', 'unknown')
            
            print(f"✅ Success: {len(recommendations)} recommendations in {end_time - start_time:.3f}s")
            print(f"   Engine: {engine}")
            
            if recommendations:
                print("   Sample recommendations:")
                for i, rec in enumerate(recommendations[:3]):
                    title = rec.get('title', 'No title')[:50]
                    reason = rec.get('reason', 'No reason')[:50]
                    print(f"     {i+1}. {title}...")
                    print(f"        Reason: {reason}...")
            else:
                print("   ⚠️ No recommendations returned")
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request error: {e}")
    
    # Test Gemini recommendations
    print("\n🔍 Testing Gemini Recommendations:")
    print("-" * 40)
    
    start_time = time.time()
    try:
        # Gemini endpoint uses POST method
        response = requests.post(f"{BASE_URL}/api/recommendations/fast-gemini", headers=headers, json={})
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            engine = data.get('engine', 'unknown')
            fallback = data.get('fallback_reason', None)
            
            print(f"✅ Success: {len(recommendations)} recommendations in {end_time - start_time:.3f}s")
            print(f"   Engine: {engine}")
            
            if fallback:
                print(f"   ⚠️ Fallback: {fallback}")
            
            if recommendations:
                print("   Sample recommendations:")
                for i, rec in enumerate(recommendations[:3]):
                    title = rec.get('title', 'No title')[:50]
                    reason = rec.get('reason', 'No reason')[:50]
                    print(f"     {i+1}. {title}...")
                    print(f"        Reason: {reason}...")
            else:
                print("   ⚠️ No recommendations returned")
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request error: {e}")
    
    print("\n" + "=" * 40)
    print("🎯 Fixed Recommendations Test Complete!")
    print("=" * 40)

if __name__ == "__main__":
    test_fixed_recommendations() 