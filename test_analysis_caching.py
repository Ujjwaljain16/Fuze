#!/usr/bin/env python3
"""
Test script for the new analysis caching system
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = 'http://127.0.0.1:5000'

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_auth():
    """Test authentication and get token"""
    print("Testing authentication...")
    
    login_data = {
        'username': 'testuser',
        'password': 'testpass123'
    }
    
    try:
        response = requests.post(f'{BASE_URL}/api/auth/login', json=login_data)
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            if token:
                print("✅ Authentication successful")
                return token
            else:
                print("❌ No access token in response")
                return None
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None

def test_analysis_stats(token):
    """Test getting analysis statistics"""
    print("\nTesting analysis statistics...")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(f'{BASE_URL}/api/recommendations/analysis/stats', headers=headers)
        if response.status_code == 200:
            data = response.json()
            stats = data.get('analysis_stats', {})
            print("✅ Analysis stats retrieved successfully")
            print(f"   Total content: {stats.get('total_content', 0)}")
            print(f"   Analyzed content: {stats.get('analyzed_content', 0)}")
            print(f"   Coverage: {stats.get('coverage_percentage', 0):.1f}%")
            print(f"   Pending analysis: {stats.get('pending_analysis', 0)}")
            return True
        else:
            print(f"❌ Failed to get analysis stats: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting analysis stats: {e}")
        return False

def test_immediate_analysis(token):
    """Test immediate content analysis"""
    print("\nTesting immediate content analysis...")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # First, get some content to analyze
    try:
        response = requests.get(f'{BASE_URL}/api/bookmarks?per_page=1', headers=headers)
        if response.status_code == 200:
            data = response.json()
            bookmarks = data.get('bookmarks', [])
            if bookmarks:
                content_id = bookmarks[0]['id']
                print(f"   Analyzing content ID: {content_id}")
                
                # Analyze the content
                analysis_response = requests.post(
                    f'{BASE_URL}/api/recommendations/analysis/analyze-content/{content_id}',
                    headers=headers
                )
                
                if analysis_response.status_code == 200:
                    analysis_data = analysis_response.json()
                    print("✅ Content analyzed successfully")
                    print(f"   Analysis result: {analysis_data.get('analysis', {}).get('content_type', 'N/A')}")
                    return True
                else:
                    print(f"❌ Analysis failed: {analysis_response.status_code}")
                    return False
            else:
                print("❌ No bookmarks found to analyze")
                return False
        else:
            print(f"❌ Failed to get bookmarks: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error in immediate analysis: {e}")
        return False

def test_background_service(token):
    """Test starting background analysis service"""
    print("\nTesting background analysis service...")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.post(f'{BASE_URL}/api/recommendations/analysis/start-background', headers=headers)
        if response.status_code == 200:
            data = response.json()
            print("✅ Background analysis service started")
            print(f"   Message: {data.get('message', 'N/A')}")
            return True
        else:
            print(f"❌ Failed to start background service: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error starting background service: {e}")
        return False

def test_cached_recommendations(token):
    """Test recommendations with cached analysis"""
    print("\nTesting recommendations with cached analysis...")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        # Test Gemini-enhanced recommendations (should use cached analysis if available)
        response = requests.post(
            f'{BASE_URL}/api/recommendations/gemini-enhanced',
            headers=headers,
            json={'user_input': 'test query'}
        )
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print("✅ Gemini-enhanced recommendations retrieved")
            print(f"   Number of recommendations: {len(recommendations)}")
            
            # Check if any recommendations have cached analysis
            cached_count = sum(1 for rec in recommendations if rec.get('cached_analysis', False))
            print(f"   Recommendations with cached analysis: {cached_count}")
            
            if recommendations:
                first_rec = recommendations[0]
                print(f"   First recommendation reason: {first_rec.get('reason', 'N/A')}")
            
            return True
        else:
            print(f"❌ Failed to get recommendations: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing cached recommendations: {e}")
        return False

def main():
    """Main test function"""
    print_header("ANALYSIS CACHING SYSTEM TEST")
    print(f"Testing at: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    token = test_auth()
    if not token:
        print("Authentication failed. Exiting.")
        return
    
    tests = [
        test_analysis_stats,
        test_immediate_analysis,
        test_background_service,
        test_cached_recommendations
    ]
    
    results = {}
    for test in tests:
        try:
            result = test(token)
            results[test.__name__] = result
        except Exception as e:
            print(f"Test {test.__name__} failed with exception: {e}")
            results[test.__name__] = False
    
    print_header("TEST SUMMARY")
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {test_name}: {status}")
    
    print_header("TEST COMPLETED")

if __name__ == "__main__":
    main() 