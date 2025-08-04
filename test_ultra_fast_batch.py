#!/usr/bin/env python3
"""
Test Ultra-Fast Batch Optimization
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def get_auth_token():
    """Get authentication token"""
    try:
        login_data = {
            "username": "ujjwaljain16",
            "password": "Jainsahab@16"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        
        if response.status_code == 200:
            return response.json().get('access_token')
        
        return None
        
    except Exception as e:
        print(f"❌ Auth error: {e}")
        return None

def test_ultra_fast_batch():
    """Test ultra-fast batch optimization"""
    print("🚀 Testing Ultra-Fast Batch Optimization")
    print("=" * 45)
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("❌ Failed to get auth token")
        return
    
    print("✅ Got auth token")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Clear cache first
    print("\n🧹 Clearing cache...")
    clear_response = requests.post(
        f"{BASE_URL}/api/recommendations/fast-gemini-clear-cache",
        headers=headers
    )
    print(f"   Cache cleared: {clear_response.status_code}")
    
    # Test data
    test_data = {
        "title": "Python web development",
        "technologies": "Flask, Python, SQLAlchemy",
        "description": "Looking for Python web development resources"
    }
    
    print("\n📤 Testing ULTRA-FAST batch optimization...")
    
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/api/recommendations/fast-gemini",
        json=test_data,
        headers=headers
    )
    response_time = time.time() - start_time
    
    print(f"⏱️ Response time: {response_time:.3f}s")
    print(f"📊 Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print("\n🚀 ULTRA-FAST BATCH RESULTS:")
        print(f"   📊 Recommendations: {len(data.get('recommendations', []))}")
        print(f"   ⚙️ Engine: {data.get('context_analysis', {}).get('processing_stats', {}).get('engine', 'unknown')}")
        print(f"   🤖 Gemini Enhanced: {data.get('context_analysis', {}).get('processing_stats', {}).get('gemini_enhanced', 0)}")
        print(f"   📡 API Calls: {data.get('context_analysis', {}).get('processing_stats', {}).get('api_calls', 0)}")
        print(f"   🚀 Response Type: {data.get('context_analysis', {}).get('processing_stats', {}).get('response_type', 'unknown')}")
        
        # Performance analysis
        if response_time < 3.0:
            print(f"   🎉 ULTRA-FAST: {response_time:.3f}s (Under 3 seconds!)")
        elif response_time < 5.0:
            print(f"   ✅ FAST: {response_time:.3f}s (Under 5 seconds)")
        else:
            print(f"   ⚠️ SLOW: {response_time:.3f}s (Over 5 seconds)")
        
        # Check sample recommendation
        recommendations = data.get('recommendations', [])
        if recommendations:
            sample = recommendations[0]
            print(f"\n📝 Sample Recommendation:")
            print(f"   ID: {sample.get('id')}")
            print(f"   Title: {sample.get('title', 'No title')}")
            print(f"   Enhanced: {sample.get('enhanced', False)}")
            print(f"   Status: {sample.get('enhancement_status', 'unknown')}")
            print(f"   Category: {sample.get('category', 'unknown')}")
            print(f"   Score: {sample.get('score', 0)}")
            
            # Check for batch enhancement
            if sample.get('enhancement_status') == 'batch_enhanced':
                print("   ✅ BATCH ENHANCEMENT: Working!")
            elif sample.get('enhancement_status') == 'cached':
                print("   ⚡ CACHED: Ultra-fast from cache!")
            else:
                print(f"   📊 Status: {sample.get('enhancement_status')}")
                
        else:
            print("   ❌ No recommendations returned")
            
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    test_ultra_fast_batch() 