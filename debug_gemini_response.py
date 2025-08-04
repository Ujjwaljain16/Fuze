#!/usr/bin/env python3
"""
Debug Gemini Response
Examine the actual response from the Gemini engine to identify issues
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def get_auth_token():
    """Get authentication token"""
    try:
        login_data = {
            "email": "jainujjwal1609@gmail.com",
            "password": "Jainsahab@16"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('access_token')
        else:
            print(f"Login failed: {response.status_code}")
            return None
                
    except Exception as e:
        print(f"Authentication error: {e}")
        return None

def debug_gemini_response():
    """Debug the Gemini engine response"""
    print("🔍 Debugging Gemini Engine Response")
    print("=" * 50)
    
    # Get auth token
    auth_token = get_auth_token()
    if not auth_token:
        print("❌ Failed to get auth token")
        return
    
    print("✅ Got auth token")
    
    # Test data
    test_data = {
        "user_id": 1,
        "title": "React Development",
        "technologies": "react,javascript,typescript",
        "content_type": "tutorial",
        "difficulty": "intermediate"
    }
    
    headers = {'Authorization': f'Bearer {auth_token}'}
    
    print(f"\n📤 Sending request to: {BASE_URL}/api/recommendations/fast-gemini")
    print(f"📋 Test data: {json.dumps(test_data, indent=2)}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/recommendations/fast-gemini",
            json=test_data,
            headers=headers,
            timeout=30
        )
        end_time = time.time()
        
        print(f"\n⏱️ Response time: {end_time - start_time:.3f}s")
        print(f"📊 Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n📄 Full Response Structure:")
            print(json.dumps(result, indent=2))
            
            # Analyze the response
            print(f"\n🔍 Response Analysis:")
            
            recommendations = result.get('recommendations', [])
            context_analysis = result.get('context_analysis', {})
            processing_stats = context_analysis.get('processing_stats', {})
            
            print(f"   📊 Recommendations count: {len(recommendations)}")
            print(f"   🤖 Gemini Enhanced: {processing_stats.get('gemini_enhanced', 0)}")
            print(f"   ⚙️ Engine: {processing_stats.get('engine', 'unknown')}")
            print(f"   🎯 Cache Hits: {processing_stats.get('cache_hits', 0)}")
            print(f"   ❌ Cache Misses: {processing_stats.get('cache_misses', 0)}")
            print(f"   📡 API Calls: {processing_stats.get('api_calls', 0)}")
            print(f"   🚀 Response Type: {processing_stats.get('response_type', 'unknown')}")
            print(f"   🤖 Gemini Status: {processing_stats.get('gemini_status', 'unknown')}")
            
            # Check if recommendations have enhancement data
            if recommendations:
                print(f"\n📝 Sample Recommendation Analysis:")
                sample = recommendations[0]
                print(f"   ID: {sample.get('id')}")
                print(f"   Title: {sample.get('title', 'N/A')}")
                print(f"   Enhanced: {sample.get('enhanced', False)}")
                print(f"   Enhancement Status: {sample.get('enhancement_status', 'none')}")
                print(f"   Category: {sample.get('category', 'unknown')}")
                print(f"   Score: {sample.get('score', 0)}")
                print(f"   Confidence: {sample.get('confidence', 0)}")
                
                # Check for Gemini-specific fields
                if 'relevance_score' in sample:
                    print(f"   Relevance Score: {sample.get('relevance_score')}")
                if 'difficulty' in sample:
                    print(f"   Difficulty: {sample.get('difficulty')}")
                if 'key_benefit' in sample:
                    print(f"   Key Benefit: {sample.get('key_benefit')}")
            
            # Check if this looks like ultra-fast engine response
            if processing_stats.get('engine') == 'fast_gemini':
                print(f"\n⚠️ WARNING: Engine shows 'fast_gemini' instead of 'advanced_gemini'")
                print(f"   This suggests the engine may have fallen back to ultra-fast mode")
                
            if processing_stats.get('gemini_enhanced') == 0:
                print(f"\n⚠️ WARNING: No Gemini enhancement detected")
                print(f"   This could mean:")
                print(f"   - Gemini API is not working")
                print(f"   - Rate limiting is active")
                print(f"   - Engine fell back to ultra-fast mode")
                print(f"   - No candidates were selected for enhancement")
                
        else:
            print(f"❌ Error response: {response.status_code}")
            print(f"📄 Error text: {response.text}")
            
    except Exception as e:
        print(f"💥 Exception: {e}")

def debug_cache_stats():
    """Debug cache statistics"""
    print(f"\n🔍 Debugging Cache Statistics")
    print("=" * 30)
    
    auth_token = get_auth_token()
    if not auth_token:
        return
    
    headers = {'Authorization': f'Bearer {auth_token}'}
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/recommendations/fast-gemini-cache-stats",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"📊 Cache Stats Response:")
            print(json.dumps(result, indent=2))
        else:
            print(f"❌ Cache stats error: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except Exception as e:
        print(f"💥 Cache stats exception: {e}")

if __name__ == "__main__":
    debug_gemini_response()
    debug_cache_stats() 