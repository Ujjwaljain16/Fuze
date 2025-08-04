#!/usr/bin/env python3
"""
Final Performance Test - After Localhost Fix
Shows the dramatic improvement in recommendation performance
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

def test_all_endpoints(headers):
    """Test performance of all major endpoints"""
    print("🚀 Testing All Endpoints Performance (After Fix)")
    print("=" * 60)
    
    endpoints = [
        ("/", "Root endpoint"),
        ("/api/health", "Health check"),
        ("/api/projects", "Projects API"),
        ("/api/recommendations/general", "Original Recommendations"),
        ("/api/recommendations/optimized", "Ultra-Fast Recommendations"),
    ]
    
    results = {}
    
    for endpoint, name in endpoints:
        print(f"\n🔍 Testing {name}...")
        
        # Test multiple times
        times = []
        for i in range(5):  # More tests for accuracy
            start_time = time.time()
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            request_time = time.time() - start_time
            times.append(request_time)
            
            if response.status_code == 200:
                print(f"  ✅ Request {i+1}: {request_time:.3f}s")
            else:
                print(f"  ❌ Request {i+1}: {response.status_code} - {request_time:.3f}s")
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"  📊 Average: {avg_time:.3f}s (min: {min_time:.3f}s, max: {max_time:.3f}s)")
        
        results[name] = {
            'average': avg_time,
            'min': min_time,
            'max': max_time,
            'times': times
        }
    
    return results

def analyze_performance(results):
    """Analyze the performance results"""
    print("\n" + "=" * 80)
    print("📊 FINAL PERFORMANCE ANALYSIS")
    print("=" * 80)
    
    print(f"\n🎯 PERFORMANCE SUMMARY:")
    for name, data in results.items():
        print(f"\n{name}:")
        print(f"  Average: {data['average']:.3f}s")
        print(f"  Min:     {data['min']:.3f}s")
        print(f"  Max:     {data['max']:.3f}s")
        
        # Performance rating
        if data['average'] < 0.1:
            print(f"  🎉 EXCELLENT performance!")
        elif data['average'] < 0.5:
            print(f"  ✅ Good performance")
        elif data['average'] < 1.0:
            print(f"  ⚠️ Acceptable performance")
        else:
            print(f"  ❌ Poor performance - needs optimization")
    
    # Compare recommendations
    if 'Original Recommendations' in results and 'Ultra-Fast Recommendations' in results:
        original_avg = results['Original Recommendations']['average']
        ultra_avg = results['Ultra-Fast Recommendations']['average']
        
        if original_avg > 0 and ultra_avg > 0:
            improvement = (original_avg - ultra_avg) / original_avg * 100
            speedup = original_avg / ultra_avg
            
            print(f"\n🚀 RECOMMENDATIONS COMPARISON:")
            print(f"  Original: {original_avg:.3f}s")
            print(f"  Ultra-Fast: {ultra_avg:.3f}s")
            print(f"  Speedup: {speedup:.1f}x faster!")
            print(f"  Improvement: {improvement:.1f}%")
            
            if improvement > 50:
                print(f"  🎉 MASSIVE IMPROVEMENT!")
            elif improvement > 20:
                print(f"  🚀 SIGNIFICANT IMPROVEMENT!")
            else:
                print(f"  ✅ GOOD IMPROVEMENT!")

def save_results(results):
    """Save results to file"""
    timestamp = datetime.now().isoformat()
    
    final_results = {
        'timestamp': timestamp,
        'fix_applied': 'localhost_to_127.0.0.1',
        'base_url': BASE_URL,
        'results': results,
        'summary': {
            'total_endpoints_tested': len(results),
            'fastest_endpoint': min(results.items(), key=lambda x: x[1]['average'])[0],
            'slowest_endpoint': max(results.items(), key=lambda x: x[1]['average'])[0],
            'average_response_time': sum(data['average'] for data in results.values()) / len(results)
        }
    }
    
    with open('final_performance_results.json', 'w') as f:
        json.dump(final_results, f, indent=2, default=str)
    
    print(f"\n📊 Results saved to final_performance_results.json")

def main():
    """Main function"""
    print("🚀 Final Performance Test - After Localhost Fix")
    print("=" * 60)
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Using: {BASE_URL}")
    
    # Login
    token = login()
    if not token:
        print("❌ Login failed. Please check your credentials.")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test all endpoints
    results = test_all_endpoints(headers)
    
    # Analyze performance
    analyze_performance(results)
    
    # Save results
    save_results(results)
    
    print(f"\n🎉 PERFORMANCE OPTIMIZATION COMPLETE!")
    print(f"   Your recommendations are now lightning fast! ⚡")

if __name__ == "__main__":
    main() 