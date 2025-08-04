#!/usr/bin/env python3
"""
Advanced Gemini Performance Test
Tests the new optimized Gemini engine with detailed metrics
"""

import requests
import time
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5000"
TEST_USER_ID = 1

def get_auth_token():
    """Get authentication token for testing"""
    try:
        # Try to login with test credentials
        login_data = {
            "email": "jainujjwal1609@gmail.com",
            "password": "Jainsahab@16"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('access_token')
        else:
            print(f"⚠️ Login failed: {response.status_code}")
            print("   Trying to create test user...")
            
            # Try to register a test user
            register_data = {
                "email": "test@example.com",
                "password": "test123",
                "name": "Test User"
            }
            
            register_response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data, timeout=10)
            
            if register_response.status_code == 201:
                result = register_response.json()
                return result.get('access_token')
            else:
                print(f"⚠️ Registration failed: {register_response.status_code}")
                return None
                
    except Exception as e:
        print(f"⚠️ Authentication error: {e}")
        return None

def test_endpoint(endpoint, method="GET", data=None, description="", auth_token=None):
    """Test an endpoint and return performance metrics"""
    url = f"{BASE_URL}{endpoint}"
    
    print(f"\n🔍 Testing: {description}")
    print(f"   URL: {url}")
    print(f"   Method: {method}")
    
    # Prepare headers with authentication
    headers = {}
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'
    
    start_time = time.time()
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        else:
            response = requests.post(url, json=data, headers=headers, timeout=30)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract key metrics
            recommendations = result.get('recommendations', [])
            context_analysis = result.get('context_analysis', {})
            processing_stats = context_analysis.get('processing_stats', {})
            
            enhanced_count = processing_stats.get('gemini_enhanced', 0)
            cache_hits = processing_stats.get('cache_hits', 0)
            cache_misses = processing_stats.get('cache_misses', 0)
            api_calls = processing_stats.get('api_calls', 0)
            engine_type = processing_stats.get('engine', 'unknown')
            
            print(f"   ✅ Success: {response_time:.3f}s")
            print(f"   📊 Recommendations: {len(recommendations)}")
            print(f"   🤖 Gemini Enhanced: {enhanced_count}")
            print(f"   🎯 Cache Hits: {cache_hits}, Misses: {cache_misses}")
            print(f"   📡 API Calls: {api_calls}")
            print(f"   ⚙️ Engine: {engine_type}")
            
            # Show sample recommendation
            if recommendations:
                sample = recommendations[0]
                print(f"   📝 Sample: {sample.get('title', 'N/A')[:50]}...")
                print(f"   🏷️ Enhanced: {sample.get('enhanced', False)}")
                print(f"   📈 Score: {sample.get('score', 0)}")
            
            return {
                'success': True,
                'response_time': response_time,
                'recommendations_count': len(recommendations),
                'enhanced_count': enhanced_count,
                'cache_hits': cache_hits,
                'cache_misses': cache_misses,
                'api_calls': api_calls,
                'engine_type': engine_type
            }
            
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   📄 Response: {response.text[:200]}...")
            return {
                'success': False,
                'response_time': response_time,
                'error': f"HTTP {response.status_code}"
            }
            
    except requests.exceptions.Timeout:
        print(f"   ⏰ Timeout after 30s")
        return {
            'success': False,
            'response_time': 30.0,
            'error': 'Timeout'
        }
    except Exception as e:
        print(f"   💥 Exception: {e}")
        return {
            'success': False,
            'response_time': time.time() - start_time,
            'error': str(e)
        }

def test_cache_stats(auth_token):
    """Test cache statistics endpoint"""
    return test_endpoint(
        "/api/recommendations/fast-gemini-cache-stats",
        "GET",
        description="Cache Statistics",
        auth_token=auth_token
    )

def clear_cache(auth_token):
    """Clear the cache"""
    return test_endpoint(
        "/api/recommendations/fast-gemini-clear-cache",
        "POST",
        description="Clear Cache",
        auth_token=auth_token
    )

def main():
    """Run comprehensive performance tests"""
    print("🚀 Advanced Gemini Performance Test")
    print("=" * 50)
    print(f"📅 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Base URL: {BASE_URL}")
    
    # Get authentication token
    print("\n🔐 Getting authentication token...")
    auth_token = get_auth_token()
    
    if not auth_token:
        print("❌ Failed to get authentication token")
        print("   Please ensure the Flask server is running and accessible")
        print("   You may need to manually create a test user first")
        return
    
    print("✅ Authentication successful")
    
    # Test data for POST requests
    test_data = {
        "user_id": TEST_USER_ID,
        "title": "React Development",
        "technologies": "react,javascript,typescript",
        "content_type": "tutorial",
        "difficulty": "intermediate"
    }
    
    results = []
    
    # Test 1: Clear cache first
    print("\n🧹 Step 1: Clearing cache...")
    clear_result = clear_cache(auth_token)
    results.append(("Clear Cache", clear_result))
    
    # Test 2: First request (should be cache miss)
    print("\n🔄 Step 2: First request (cache miss)...")
    first_result = test_endpoint(
        "/api/recommendations/fast-gemini",
        "POST",
        test_data,
        "Advanced Gemini Engine - First Request",
        auth_token
    )
    results.append(("First Request", first_result))
    
    # Test 3: Second request (should be cache hit)
    print("\n🔄 Step 3: Second request (cache hit)...")
    second_result = test_endpoint(
        "/api/recommendations/fast-gemini",
        "POST",
        test_data,
        "Advanced Gemini Engine - Second Request",
        auth_token
    )
    results.append(("Second Request", second_result))
    
    # Test 4: Different request (should be cache miss)
    print("\n🔄 Step 4: Different request (cache miss)...")
    different_data = {
        "user_id": TEST_USER_ID,
        "title": "Python Machine Learning",
        "technologies": "python,scikit-learn,tensorflow",
        "content_type": "course",
        "difficulty": "advanced"
    }
    different_result = test_endpoint(
        "/api/recommendations/fast-gemini",
        "POST",
        different_data,
        "Advanced Gemini Engine - Different Request",
        auth_token
    )
    results.append(("Different Request", different_result))
    
    # Test 5: Project-specific recommendations
    print("\n🔄 Step 5: Project recommendations...")
    project_result = test_endpoint(
        "/api/recommendations/fast-gemini-project/1",
        "GET",
        description="Advanced Gemini Engine - Project Recommendations",
        auth_token=auth_token
    )
    results.append(("Project Request", project_result))
    
    # Test 6: Cache statistics
    print("\n🔄 Step 6: Cache statistics...")
    stats_result = test_cache_stats(auth_token)
    results.append(("Cache Stats", stats_result))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 50)
    
    successful_tests = [r for r in results if r[1]['success']]
    failed_tests = [r for r in results if not r[1]['success']]
    
    print(f"✅ Successful Tests: {len(successful_tests)}/{len(results)}")
    print(f"❌ Failed Tests: {len(failed_tests)}/{len(results)}")
    
    if successful_tests:
        avg_response_time = sum(r[1]['response_time'] for r in successful_tests) / len(successful_tests)
        print(f"⏱️ Average Response Time: {avg_response_time:.3f}s")
        
        # Find fastest and slowest
        fastest = min(successful_tests, key=lambda x: x[1]['response_time'])
        slowest = max(successful_tests, key=lambda x: x[1]['response_time'])
        
        print(f"⚡ Fastest: {fastest[0]} ({fastest[1]['response_time']:.3f}s)")
        print(f"🐌 Slowest: {slowest[0]} ({slowest[1]['response_time']:.3f}s)")
        
        # Gemini-specific metrics
        gemini_tests = [r for r in successful_tests if 'gemini' in r[0].lower()]
        if gemini_tests:
            total_api_calls = sum(r[1].get('api_calls', 0) for r in gemini_tests)
            total_enhanced = sum(r[1].get('enhanced_count', 0) for r in gemini_tests)
            total_cache_hits = sum(r[1].get('cache_hits', 0) for r in gemini_tests)
            total_cache_misses = sum(r[1].get('cache_misses', 0) for r in gemini_tests)
            
            print(f"\n🤖 Gemini Metrics:")
            print(f"   📡 Total API Calls: {total_api_calls}")
            print(f"   🎯 Total Enhanced: {total_enhanced}")
            print(f"   💾 Cache Hits: {total_cache_hits}")
            print(f"   ❌ Cache Misses: {total_cache_misses}")
            
            if total_cache_hits + total_cache_misses > 0:
                hit_rate = total_cache_hits / (total_cache_hits + total_cache_misses) * 100
                print(f"   📈 Cache Hit Rate: {hit_rate:.1f}%")
    
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for test_name, result in failed_tests:
            print(f"   {test_name}: {result.get('error', 'Unknown error')}")
    
    print(f"\n🎯 Performance Assessment:")
    
    if successful_tests:
        avg_time = sum(r[1]['response_time'] for r in successful_tests) / len(successful_tests)
        
        if avg_time < 1.0:
            print("   🟢 EXCELLENT: Sub-second response times!")
        elif avg_time < 3.0:
            print("   🟡 GOOD: Response times under 3 seconds")
        elif avg_time < 5.0:
            print("   🟠 ACCEPTABLE: Response times under 5 seconds")
        else:
            print("   🔴 NEEDS IMPROVEMENT: Response times over 5 seconds")
    
    print("\n✨ Test completed!")

if __name__ == "__main__":
    main() 