#!/usr/bin/env python3
"""
Test Production Performance
Quick test to verify the performance improvement
"""

import time
import requests
import json

# Configuration
BASE_URL = "http://127.0.0.1:5000"
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

def test_performance(headers):
    """Test performance of different endpoints"""
    print("🚀 Testing Production Performance...")
    print("=" * 50)
    
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
        for i in range(3):
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
    
    # Analysis
    print("\n" + "=" * 80)
    print("📊 PERFORMANCE ANALYSIS")
    print("=" * 80)
    
    for name, data in results.items():
        print(f"\n{name}:")
        print(f"  Average: {data['average']:.3f}s")
        print(f"  Min:     {data['min']:.3f}s")
        print(f"  Max:     {data['max']:.3f}s")
        
        if data['average'] < 0.1:
            print(f"  🎉 EXCELLENT performance!")
        elif data['average'] < 0.5:
            print(f"  ✅ Good performance")
        elif data['average'] < 1.0:
            print(f"  ⚠️ Acceptable performance")
        else:
            print(f"  ❌ Poor performance - needs optimization")
    
    # Save results
    with open('production_performance_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📊 Results saved to production_performance_results.json")

def main():
    """Main function"""
    # Login
    token = login()
    if not token:
        print("❌ Login failed. Please check your credentials.")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test performance
    test_performance(headers)

if __name__ == "__main__":
    main() 