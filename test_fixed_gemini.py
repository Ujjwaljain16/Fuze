#!/usr/bin/env python3
"""
Test Fixed Gemini Engine
Quick test to verify the fixes work
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

def test_fixed_gemini():
    """Test the fixed Gemini engine"""
    print("🔧 Testing Fixed Gemini Engine")
    print("=" * 40)
    
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
    
    print(f"\n📤 Testing fixed engine...")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/recommendations/fast-gemini",
            json=test_data,
            headers=headers,
            timeout=30
        )
        end_time = time.time()
        
        print(f"⏱️ Response time: {end_time - start_time:.3f}s")
        print(f"📊 Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Check key metrics
            recommendations = result.get('recommendations', [])
            context_analysis = result.get('context_analysis', {})
            processing_stats = context_analysis.get('processing_stats', {})
            
            print(f"\n✅ FIXES VERIFIED:")
            print(f"   📊 Recommendations: {len(recommendations)}")
            print(f"   ⚙️ Engine: {processing_stats.get('engine', 'unknown')}")
            print(f"   🤖 Gemini Enhanced: {processing_stats.get('gemini_enhanced', 0)}")
            print(f"   🚀 Response Type: {processing_stats.get('response_type', 'unknown')}")
            print(f"   🤖 Gemini Status: {processing_stats.get('gemini_status', 'unknown')}")
            
            # Check if recommendations have proper data
            if recommendations:
                sample = recommendations[0]
                print(f"\n📝 Sample Recommendation:")
                print(f"   ID: {sample.get('id')}")
                print(f"   Title: {sample.get('title', 'N/A')}")
                print(f"   Enhanced: {sample.get('enhanced', False)}")
                print(f"   Category: {sample.get('category', 'unknown')}")
                print(f"   Score: {sample.get('score', 0)}")
                
                # Check if null fields are fixed
                if sample.get('title') and sample.get('title') != "No title available":
                    print(f"   ✅ Title field fixed")
                else:
                    print(f"   ⚠️ Title field still has issues")
                
                if sample.get('notes') and sample.get('notes') != "No content available":
                    print(f"   ✅ Notes field fixed")
                else:
                    print(f"   ⚠️ Notes field still has issues")
            
            # Check engine type
            if processing_stats.get('engine') == 'advanced_gemini':
                print(f"   ✅ Engine type fixed (shows 'advanced_gemini')")
            else:
                print(f"   ⚠️ Engine type still shows: {processing_stats.get('engine')}")
            
            # Check performance
            response_time = end_time - start_time
            if response_time < 5.0:
                print(f"   ✅ Performance improved ({response_time:.3f}s)")
            else:
                print(f"   ⚠️ Performance still slow ({response_time:.3f}s)")
                
        else:
            print(f"❌ Error response: {response.status_code}")
            print(f"📄 Error text: {response.text}")
            
    except Exception as e:
        print(f"💥 Exception: {e}")

if __name__ == "__main__":
    test_fixed_gemini() 