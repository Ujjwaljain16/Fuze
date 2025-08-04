#!/usr/bin/env python3
"""
Quick test to verify JSON parsing fix
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

def test_json_fix():
    """Test JSON parsing fix"""
    print("🔧 Testing JSON Parsing Fix")
    print("=" * 30)
    
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
    
    # Test data
    test_data = {
        "title": "React Development",
        "technologies": "React, JavaScript, TypeScript",
        "description": "Looking for React development resources"
    }
    
    print("\n📤 Testing JSON parsing fix...")
    
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
        
        print("\n✅ JSON PARSING FIX VERIFIED:")
        print(f"   📊 Recommendations: {len(data.get('recommendations', []))}")
        print(f"   🤖 Gemini Enhanced: {data.get('context_analysis', {}).get('processing_stats', {}).get('gemini_enhanced', 0)}")
        print(f"   ⚙️ Engine: {data.get('context_analysis', {}).get('processing_stats', {}).get('engine', 'unknown')}")
        
        # Check if recommendations have proper data
        recommendations = data.get('recommendations', [])
        if recommendations:
            sample = recommendations[0]
            print(f"\n📝 Sample Recommendation:")
            print(f"   ID: {sample.get('id')}")
            print(f"   Title: {sample.get('title', 'No title')}")
            print(f"   Enhanced: {sample.get('enhanced', False)}")
            print(f"   Category: {sample.get('category', 'unknown')}")
            print(f"   Score: {sample.get('score', 0)}")
            
            # Check for JSON parsing errors
            if "No content available" not in str(sample.get('title', '')):
                print("   ✅ JSON parsing working correctly")
            else:
                print("   ⚠️ JSON parsing still has issues")
                
        else:
            print("   ❌ No recommendations returned")
            
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    test_json_fix() 