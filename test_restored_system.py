#!/usr/bin/env python3
"""
Test script for the restored recommendation system
Verifies that all endpoints work correctly with optimizations
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = 'http://127.0.0.1:5000'
LOGIN_DATA = {
    'email': 'test@example.com',
    'password': 'testpassword123'
}

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_section(title):
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")

def test_auth():
    """Test authentication"""
    print_section("Testing Authentication")
    
    try:
        # Try to register first
        register_response = requests.post(f'{BASE_URL}/api/auth/register', json=LOGIN_DATA)
        print(f"Register response: {register_response.status_code}")
        
        # Login
        login_response = requests.post(f'{BASE_URL}/api/auth/login', json=LOGIN_DATA)
        print(f"Login response: {login_response.status_code}")
        
        if login_response.status_code == 200:
            data = login_response.json()
            token = data.get('access_token')
            print(f"Token received: {'Yes' if token else 'No'}")
            return token
        else:
            print(f"Login failed: {login_response.text}")
            return None
            
    except Exception as e:
        print(f"Auth error: {e}")
        return None

def test_general_recommendations(token):
    """Test general recommendations endpoint"""
    print_section("Testing General Recommendations")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        # Test general recommendations
        response = requests.get(f'{BASE_URL}/api/recommendations/general', headers=headers)
        print(f"General recommendations status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print(f"Recommendations count: {len(recommendations)}")
            print(f"Cached: {data.get('cached', False)}")
            print(f"Computation time: {data.get('computation_time_ms', 0):.2f}ms")
            
            if recommendations:
                print(f"First recommendation: {recommendations[0].get('title', 'N/A')}")
                print(f"Reason: {recommendations[0].get('reason', 'N/A')}")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"General recommendations error: {e}")
        return False

def test_unified_recommendations(token):
    """Test unified recommendations endpoint"""
    print_section("Testing Unified Recommendations")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(f'{BASE_URL}/api/recommendations/unified', headers=headers)
        print(f"Unified recommendations status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print(f"Recommendations count: {len(recommendations)}")
            print(f"Cached: {data.get('cached', False)}")
            print(f"Computation time: {data.get('computation_time_ms', 0):.2f}ms")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Unified recommendations error: {e}")
        return False

def test_gemini_enhanced_recommendations(token):
    """Test Gemini-enhanced recommendations endpoint"""
    print_section("Testing Gemini-Enhanced Recommendations")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        # Test data for Gemini enhancement
        test_data = {
            'title': 'Learning Python Development',
            'description': 'I want to improve my Python skills',
            'technologies': 'python, flask, sqlalchemy',
            'user_interests': 'web development, backend, api design'
        }
        
        response = requests.post(f'{BASE_URL}/api/recommendations/gemini-enhanced', 
                               json=test_data, headers=headers)
        print(f"Gemini-enhanced recommendations status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print(f"Recommendations count: {len(recommendations)}")
            print(f"Cached: {data.get('cached', False)}")
            print(f"Computation time: {data.get('computation_time_ms', 0):.2f}ms")
            
            if recommendations:
                print(f"First recommendation: {recommendations[0].get('title', 'N/A')}")
                print(f"Reason: {recommendations[0].get('reason', 'N/A')}")
                if 'technologies' in recommendations[0]:
                    print(f"Technologies: {recommendations[0]['technologies']}")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Gemini-enhanced recommendations error: {e}")
        return False

def test_project_recommendations(token):
    """Test project-specific recommendations"""
    print_section("Testing Project Recommendations")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        # Test with a sample project ID (you may need to adjust this)
        project_id = 1
        
        # Test unified project recommendations
        response = requests.get(f'{BASE_URL}/api/recommendations/unified-project/{project_id}', 
                              headers=headers)
        print(f"Unified project recommendations status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print(f"Recommendations count: {len(recommendations)}")
            print(f"Project ID: {data.get('project_id')}")
            print(f"Computation time: {data.get('computation_time_ms', 0):.2f}ms")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Project recommendations error: {e}")
        return False

def test_gemini_project_recommendations(token):
    """Test Gemini-enhanced project recommendations"""
    print_section("Testing Gemini-Enhanced Project Recommendations")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        project_id = 1
        test_data = {
            'title': 'Python Web App Project',
            'description': 'Building a Flask web application',
            'technologies': 'python, flask, sqlalchemy, postgresql'
        }
        
        response = requests.post(f'{BASE_URL}/api/recommendations/gemini-enhanced-project/{project_id}', 
                               json=test_data, headers=headers)
        print(f"Gemini-enhanced project recommendations status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print(f"Recommendations count: {len(recommendations)}")
            print(f"Project ID: {data.get('project_id')}")
            print(f"Computation time: {data.get('computation_time_ms', 0):.2f}ms")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Gemini-enhanced project recommendations error: {e}")
        return False

def test_cache_operations(token):
    """Test cache operations"""
    print_section("Testing Cache Operations")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        # Test cache clearing
        response = requests.post(f'{BASE_URL}/api/recommendations/cache/clear', headers=headers)
        print(f"Cache clear status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Cache clear message: {data.get('message', 'N/A')}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Cache operations error: {e}")
        return False

def test_performance_comparison(token):
    """Test performance comparison between different endpoints"""
    print_section("Performance Comparison")
    
    headers = {'Authorization': f'Bearer {token}'}
    results = {}
    
    endpoints = [
        ('general', 'GET', None),
        ('unified', 'GET', None),
        ('gemini-enhanced', 'POST', {
            'title': 'Performance Test',
            'description': 'Testing recommendation performance',
            'technologies': 'python, javascript, react'
        })
    ]
    
    for name, method, data in endpoints:
        try:
            start_time = time.time()
            
            if method == 'GET':
                response = requests.get(f'{BASE_URL}/api/recommendations/{name}', headers=headers)
            else:
                response = requests.post(f'{BASE_URL}/api/recommendations/{name}', 
                                       json=data, headers=headers)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                response_data = response.json()
                computation_time = response_data.get('computation_time_ms', 0)
                cached = response_data.get('cached', False)
                recommendations_count = len(response_data.get('recommendations', []))
                
                results[name] = {
                    'response_time_ms': response_time,
                    'computation_time_ms': computation_time,
                    'cached': cached,
                    'recommendations_count': recommendations_count
                }
                
                print(f"{name}: {response_time:.2f}ms total, {computation_time:.2f}ms computation, "
                      f"{recommendations_count} recommendations, cached: {cached}")
            else:
                print(f"{name}: Failed - {response.status_code}")
                
        except Exception as e:
            print(f"{name}: Error - {e}")
    
    return results

def main():
    """Main test function"""
    print_header("RESTORED RECOMMENDATION SYSTEM TEST")
    print(f"Testing at: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test authentication
    token = test_auth()
    if not token:
        print("Authentication failed. Exiting.")
        return
    
    # Test all endpoints
    tests = [
        test_general_recommendations,
        test_unified_recommendations,
        test_gemini_enhanced_recommendations,
        test_project_recommendations,
        test_gemini_project_recommendations,
        test_cache_operations
    ]
    
    results = {}
    for test in tests:
        try:
            result = test(token)
            results[test.__name__] = result
        except Exception as e:
            print(f"Test {test.__name__} failed with exception: {e}")
            results[test.__name__] = False
    
    # Performance comparison
    performance_results = test_performance_comparison(token)
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {test_name}: {status}")
    
    if performance_results:
        print("\nPerformance Results:")
        for endpoint, metrics in performance_results.items():
            print(f"  {endpoint}: {metrics['response_time_ms']:.2f}ms total, "
                  f"{metrics['computation_time_ms']:.2f}ms computation")
    
    print_header("TEST COMPLETED")

if __name__ == "__main__":
    main() 