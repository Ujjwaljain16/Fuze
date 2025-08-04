#!/usr/bin/env python3
"""
Test script to verify Gemini fixes
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

def get_auth_token():
    """Get authentication token"""
    try:
        # Try to login first
        login_data = {
            "username": "ujjwaljain16",
            "password": "Jainsahab@16"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        
        if response.status_code == 200:
            return response.json().get('access_token')
        
        # If login fails, try to register
        register_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "name": "Test User"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
        
        if response.status_code == 201:
            # After registration, try to login
            login_response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
            if login_response.status_code == 200:
                return login_response.json().get('access_token')
        
        return None
        
    except Exception as e:
        print(f"❌ Auth error: {e}")
        return None

def test_gemini_fixes():
    """Test all Gemini fixes"""
    print("🔧 Testing Gemini Fixes")
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
        "title": "Python web development",
        "technologies": "Flask, Python, SQLAlchemy",
        "description": "Looking for Python web development resources"
    }
    
    print("\n📤 Testing fixed Gemini engine...")
    
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
        
        print("\n✅ FIXES VERIFIED:")
        print(f"   📊 Recommendations: {len(data.get('recommendations', []))}")
        print(f"   ⚙️ Engine: {data.get('context_analysis', {}).get('processing_stats', {}).get('engine', 'unknown')}")
        print(f"   🤖 Gemini Enhanced: {data.get('context_analysis', {}).get('processing_stats', {}).get('gemini_enhanced', 0)}")
        print(f"   🚀 Response Type: {data.get('context_analysis', {}).get('processing_stats', {}).get('response_type', 'unknown')}")
        print(f"   🤖 Gemini Status: {data.get('context_analysis', {}).get('processing_stats', {}).get('gemini_status', 'unknown')}")
        
        # Check sample recommendation
        recommendations = data.get('recommendations', [])
        if recommendations:
            sample = recommendations[0]
            print(f"\n📝 Sample Recommendation:")
            print(f"   ID: {sample.get('id')}")
            print(f"   Title: {sample.get('title', 'No title')}")
            print(f"   Enhanced: {sample.get('enhanced', False)}")
            print(f"   Category: {sample.get('category', 'unknown')}")
            print(f"   Score: {sample.get('score', 0)}")
            
            # Check specific fixes
            title_ok = sample.get('title') and sample.get('title') != "No content available"
            notes_ok = sample.get('notes') and sample.get('notes') != "No content available"
            engine_ok = data.get('context_analysis', {}).get('processing_stats', {}).get('engine') == 'advanced_gemini'
            performance_ok = response_time < 5.0
            no_errors = response.status_code == 200
            
            print(f"   ✅ Title field fixed" if title_ok else "   ❌ Title field still broken")
            print(f"   ✅ Notes field fixed" if notes_ok else "   ⚠️ Notes field still has issues")
            print(f"   ✅ Engine type fixed (shows 'advanced_gemini')" if engine_ok else "   ❌ Engine type still wrong")
            print(f"   ✅ Performance acceptable" if performance_ok else "   ⚠️ Performance still slow")
            print(f"   ✅ No errors detected" if no_errors else "   ❌ Errors detected")
            
            # Check for specific error patterns
            if "No content available" in str(sample.get('title', '')) or "No content available" in str(sample.get('notes', '')):
                print("   ⚠️ Content fetching still needs work")
            else:
                print("   ✅ Content fetching working")
                
        else:
            print("   ❌ No recommendations returned")
            
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    test_gemini_fixes() 