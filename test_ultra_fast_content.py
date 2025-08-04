#!/usr/bin/env python3
"""
Test Ultra-Fast Engine Content
Check what content the ultra-fast engine is returning
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

def test_ultra_fast_content():
    """Test what content ultra-fast engine returns"""
    print("🔍 Testing Ultra-Fast Engine Content")
    print("=" * 40)
    
    # Get auth token
    auth_token = get_auth_token()
    if not auth_token:
        print("❌ Failed to get auth token")
        return
    
    print("✅ Got auth token")
    
    headers = {'Authorization': f'Bearer {auth_token}'}
    
    print(f"\n📤 Testing ultra-fast engine...")
    
    try:
        start_time = time.time()
        response = requests.get(
            f"{BASE_URL}/api/recommendations/optimized",
            headers=headers,
            timeout=30
        )
        end_time = time.time()
        
        print(f"⏱️ Response time: {end_time - start_time:.3f}s")
        print(f"📊 Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            recommendations = result.get('recommendations', [])
            print(f"\n📊 Found {len(recommendations)} recommendations")
            
            if recommendations:
                print(f"\n📝 Raw Recommendation Data:")
                sample = recommendations[0]
                for key, value in sample.items():
                    print(f"   {key}: {value}")
                
                # Check if we can get content from database
                print(f"\n🔍 Checking for content in database...")
                if sample.get('id'):
                    content_response = requests.get(
                        f"{BASE_URL}/api/content/{sample['id']}",
                        headers=headers,
                        timeout=10
                    )
                    if content_response.status_code == 200:
                        content_data = content_response.json()
                        print(f"   Database content: {content_data.get('content', 'No content')[:100]}...")
                    else:
                        print(f"   Could not fetch content from database")
            
        else:
            print(f"❌ Error response: {response.status_code}")
            print(f"📄 Error text: {response.text}")
            
    except Exception as e:
        print(f"💥 Exception: {e}")

if __name__ == "__main__":
    test_ultra_fast_content() 