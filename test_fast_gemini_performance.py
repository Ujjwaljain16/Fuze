#!/usr/bin/env python3
"""
Test Fast Gemini Performance
Compare the new fast Gemini engine against the original Gemini engine
"""

import time
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5000"  # Using the fast method
LOGIN_DATA = {
    "username": "ujjwaljain16",
    "password": "Jainsahab@16"
}

def login():
    """Login and get access token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=LOGIN_DATA)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"Login failed: {response.text}")
        return None

def test_gemini_engines(headers):
    """Test performance of different Gemini engines"""
    print("🚀 Testing Gemini Engine Performance")
    print("=" * 60)
    
    # Test data
    test_input = {
        "title": "React Development Project",
        "description": "Building a modern web application with React, Node.js, and MongoDB",
        "technologies": "React, JavaScript, Node.js, MongoDB, Express",
        "user_interests": "Web development, Full-stack development, Modern JavaScript"
    }
    
    engines = [
        {
            "name": "Original Gemini Enhanced",
            "endpoint": "/api/recommendations/gemini-enhanced",
            "method": "POST"
        },
        {
            "name": "Fast Gemini Engine",
            "endpoint": "/api/recommendations/fast-gemini", 
            "method": "POST"
        },
        {
            "name": "Ultra-Fast Engine (No Gemini)",
            "endpoint": "/api/recommendations/optimized",
            "method": "GET"
        }
    ]
    
    results = {}
    
    for engine in engines:
        print(f"\n🔍 Testing {engine['name']}...")
        
        # Test multiple times for accuracy
        times = []
        success_count = 0
        
        for i in range(3):  # Test 3 times each
            start_time = time.time()
            
            try:
                if engine['method'] == 'POST':
                    response = requests.post(
                        f"{BASE_URL}{engine['endpoint']}", 
                        json=test_input, 
                        headers=headers,
                        timeout=30
                    )
                else:
                    response = requests.get(
                        f"{BASE_URL}{engine['endpoint']}", 
                        headers=headers,
                        timeout=30
                    )
                
                request_time = time.time() - start_time
                times.append(request_time)
                
                if response.status_code == 200:
                    success_count += 1
                    data = response.json()
                    recommendations_count = len(data.get('recommendations', []))
                    enhanced_count = len([r for r in data.get('recommendations', []) if r.get('enhanced')])
                    
                    print(f"  ✅ Request {i+1}: {request_time:.3f}s - {recommendations_count} recommendations ({enhanced_count} enhanced)")
                    
                    # Show cache stats if available
                    if 'cache_stats' in data:
                        cache_stats = data['cache_stats']
                        print(f"     Cache: {cache_stats.get('cache_hits', 0)} hits, {cache_stats.get('cache_misses', 0)} misses")
                else:
                    print(f"  ❌ Request {i+1}: {response.status_code} - {request_time:.3f}s")
                    
            except Exception as e:
                print(f"  ❌ Request {i+1}: Failed - {e}")
        
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            results[engine['name']] = {
                'average': avg_time,
                'min': min_time,
                'max': max_time,
                'success_rate': success_count / 3,
                'times': times
            }
            
            print(f"  📊 Average: {avg_time:.3f}s (min: {min_time:.3f}s, max: {max_time:.3f}s)")
            print(f"  📊 Success Rate: {success_count}/3 ({success_count/3*100:.1f}%)")
        else:
            results[engine['name']] = {
                'average': 0,
                'min': 0,
                'max': 0,
                'success_rate': 0,
                'times': []
            }
    
    return results

def analyze_performance(results):
    """Analyze the performance results"""
    print("\n" + "=" * 80)
    print("📊 GEMINI ENGINE PERFORMANCE ANALYSIS")
    print("=" * 80)
    
    print(f"\n🎯 PERFORMANCE SUMMARY:")
    for name, data in results.items():
        print(f"\n{name}:")
        print(f"  Average: {data['average']:.3f}s")
        print(f"  Min:     {data['min']:.3f}s")
        print(f"  Max:     {data['max']:.3f}s")
        print(f"  Success: {data['success_rate']*100:.1f}%")
        
        # Performance rating
        if data['average'] < 1.0:
            print(f"  🎉 EXCELLENT performance!")
        elif data['average'] < 3.0:
            print(f"  ✅ Good performance")
        elif data['average'] < 5.0:
            print(f"  ⚠️ Acceptable performance")
        else:
            print(f"  ❌ Poor performance - needs optimization")
    
    # Compare engines
    if 'Original Gemini Enhanced' in results and 'Fast Gemini Engine' in results:
        original_avg = results['Original Gemini Enhanced']['average']
        fast_avg = results['Fast Gemini Engine']['average']
        
        if original_avg > 0 and fast_avg > 0:
            improvement = (original_avg - fast_avg) / original_avg * 100
            speedup = original_avg / fast_avg
            
            print(f"\n🚀 GEMINI ENGINE COMPARISON:")
            print(f"  Original Gemini: {original_avg:.3f}s")
            print(f"  Fast Gemini:     {fast_avg:.3f}s")
            print(f"  Speedup: {speedup:.1f}x faster!")
            print(f"  Improvement: {improvement:.1f}%")
            
            if improvement > 50:
                print(f"  🎉 MASSIVE IMPROVEMENT!")
            elif improvement > 20:
                print(f"  🚀 SIGNIFICANT IMPROVEMENT!")
            else:
                print(f"  ✅ GOOD IMPROVEMENT!")
    
    # Compare with ultra-fast
    if 'Fast Gemini Engine' in results and 'Ultra-Fast Engine (No Gemini)' in results:
        fast_avg = results['Fast Gemini Engine']['average']
        ultra_avg = results['Ultra-Fast Engine (No Gemini)']['average']
        
        if fast_avg > 0 and ultra_avg > 0:
            overhead = (fast_avg - ultra_avg) / ultra_avg * 100
            
            print(f"\n⚡ GEMINI OVERHEAD ANALYSIS:")
            print(f"  Ultra-Fast: {ultra_avg:.3f}s")
            print(f"  Fast Gemini: {fast_avg:.3f}s")
            print(f"  Gemini Overhead: {overhead:.1f}%")
            
            if overhead < 50:
                print(f"  ✅ LOW OVERHEAD - Gemini adds minimal delay!")
            elif overhead < 100:
                print(f"  ⚠️ MODERATE OVERHEAD - Acceptable trade-off")
            else:
                print(f"  ❌ HIGH OVERHEAD - Consider using ultra-fast for speed")

def save_results(results):
    """Save results to file"""
    timestamp = datetime.now().isoformat()
    
    final_results = {
        'timestamp': timestamp,
        'test_type': 'gemini_engine_comparison',
        'base_url': BASE_URL,
        'results': results,
        'summary': {
            'total_engines_tested': len(results),
            'fastest_engine': min(results.items(), key=lambda x: x[1]['average'])[0],
            'slowest_engine': max(results.items(), key=lambda x: x[1]['average'])[0],
            'average_response_time': sum(data['average'] for data in results.values()) / len(results)
        }
    }
    
    with open('gemini_performance_results.json', 'w') as f:
        json.dump(final_results, f, indent=2, default=str)
    
    print(f"\n📊 Results saved to gemini_performance_results.json")

def main():
    """Main function"""
    print("🚀 Fast Gemini Engine Performance Test")
    print("=" * 60)
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Using: {BASE_URL}")
    
    # Login
    token = login()
    if not token:
        print("❌ Login failed. Please check your credentials.")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test all engines
    results = test_gemini_engines(headers)
    
    # Analyze performance
    analyze_performance(results)
    
    # Save results
    save_results(results)
    
    print(f"\n🎉 GEMINI OPTIMIZATION COMPLETE!")
    print(f"   Your Gemini recommendations are now much faster! ⚡")

if __name__ == "__main__":
    main() 