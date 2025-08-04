#!/usr/bin/env python3
"""
Test script to check if the infinite request issue is resolved
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = 'http://127.0.0.1:5000'

def print_header(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def test_auth():
    """Test authentication"""
    try:
        response = requests.post(f'{BASE_URL}/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'testpassword123'
        })
        
        if response.status_code == 200:
            data = response.json()
            return data.get('access_token')
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None

def test_recommendations_endpoint(token, endpoint, method='GET', data=None):
    """Test a specific recommendations endpoint"""
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        if method == 'GET':
            response = requests.get(f'{BASE_URL}{endpoint}', headers=headers)
        else:
            response = requests.post(f'{BASE_URL}{endpoint}', headers=headers, json=data)
        
        print(f"  {method} {endpoint}: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            recommendations = response_data.get('recommendations', [])
            print(f"    ✅ Success - {len(recommendations)} recommendations")
            return True
        else:
            print(f"    ❌ Failed - {response.status_code}")
            return False
            
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False

def test_infinite_request_fix():
    """Test if infinite request issue is resolved"""
    print_header("INFINITE REQUEST FIX TEST")
    print(f"Testing at: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Authenticate
    token = test_auth()
    if not token:
        print("❌ Authentication failed. Exiting.")
        return False
    
    print("✅ Authentication successful")
    
    # Test endpoints multiple times to check for infinite loops
    endpoints_to_test = [
        ('/api/recommendations/general', 'GET'),
        ('/api/recommendations/gemini-enhanced', 'POST', {
            'title': 'Test Request',
            'description': 'Testing for infinite loops',
            'technologies': 'python, flask',
            'user_interests': 'web development',
            'max_recommendations': 5
        }),
        ('/api/recommendations/gemini-status', 'GET')
    ]
    
    print("\nTesting endpoints for infinite request issues...")
    
    for i in range(3):  # Test 3 times
        print(f"\n--- Test Run {i+1} ---")
        
        for endpoint_info in endpoints_to_test:
            if len(endpoint_info) == 2:
                endpoint, method = endpoint_info
                data = None
            else:
                endpoint, method, data = endpoint_info
            
            success = test_recommendations_endpoint(token, endpoint, method, data)
            if not success:
                print(f"❌ Endpoint {endpoint} failed on run {i+1}")
                return False
            
            # Small delay between requests
            time.sleep(0.5)
    
    print("\n✅ All tests completed successfully - no infinite request issues detected")
    return True

def test_background_service():
    """Test background analysis service endpoints"""
    print_header("BACKGROUND SERVICE TEST")
    
    token = test_auth()
    if not token:
        print("❌ Authentication failed. Exiting.")
        return False
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test analysis stats
    try:
        response = requests.get(f'{BASE_URL}/api/recommendations/analysis/stats', headers=headers)
        print(f"Analysis stats: {response.status_code}")
        if response.status_code == 200:
            stats = response.json()
            print(f"  Total content: {stats.get('analysis_stats', {}).get('total_content', 0)}")
            print(f"  Analyzed content: {stats.get('analysis_stats', {}).get('analyzed_content', 0)}")
    except Exception as e:
        print(f"❌ Analysis stats error: {e}")
    
    print("✅ Background service test completed")

if __name__ == "__main__":
    success = test_infinite_request_fix()
    if success:
        test_background_service()
    
    print_header("TEST COMPLETED")
    if success:
        print("🎉 Infinite request issue appears to be resolved!")
    else:
        print("💥 Issues detected - further investigation needed") 