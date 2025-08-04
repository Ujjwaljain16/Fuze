#!/usr/bin/env python3
"""
Minimal Performance Test for Fuze
Isolates bottlenecks in the recommendation system
"""

import time
import requests
import json
from datetime import datetime

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

def test_database_performance(headers):
    """Test database performance directly"""
    print("\n🔍 Testing Database Performance...")
    print("-" * 40)
    
    # Test simple database query
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
    db_time = time.time() - start_time
    
    if response.status_code == 200:
        print(f"✅ Database query: {db_time:.3f}s")
    else:
        print(f"❌ Database query failed: {response.status_code}")
    
    return db_time

def test_redis_performance(headers):
    """Test Redis performance"""
    print("\n🔍 Testing Redis Performance...")
    print("-" * 40)
    
    # Test Redis by making a cached request
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/api/recommendations/optimized", headers=headers)
    redis_time = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        cached = data.get('cached', False)
        print(f"✅ Redis request: {redis_time:.3f}s, Cached: {cached}")
    else:
        print(f"❌ Redis request failed: {response.status_code}")
    
    return redis_time

def test_flask_overhead():
    """Test Flask overhead with a simple endpoint"""
    print("\n🔍 Testing Flask Overhead...")
    print("-" * 40)
    
    # Test a simple endpoint (if available)
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/")
    flask_time = time.time() - start_time
    
    print(f"✅ Flask overhead: {flask_time:.3f}s (status: {response.status_code})")
    return flask_time

def test_network_latency():
    """Test network latency"""
    print("\n🔍 Testing Network Latency...")
    print("-" * 40)
    
    # Test multiple requests to measure network latency
    times = []
    for i in range(5):
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/")
        request_time = time.time() - start_time
        times.append(request_time)
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"✅ Network latency: {avg_time:.3f}s (min: {min_time:.3f}s, max: {max_time:.3f}s)")
    return avg_time

def test_recommendation_breakdown(headers):
    """Test recommendation system breakdown"""
    print("\n🔍 Testing Recommendation System Breakdown...")
    print("-" * 40)
    
    # Test original recommendations
    print("  Testing Original Recommendations...")
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/api/recommendations/general", headers=headers)
    original_time = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        computation_time = data.get('computation_time_ms', 0)
        print(f"    ✅ Original: {original_time:.3f}s, Computation: {computation_time:.1f}ms")
    else:
        print(f"    ❌ Original failed: {response.status_code}")
    
    # Test ultra-fast recommendations
    print("  Testing Ultra-Fast Recommendations...")
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/api/recommendations/optimized", headers=headers)
    ultra_time = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        computation_time = data.get('computation_time_ms', 0)
        cached = data.get('cached', False)
        print(f"    ✅ Ultra-Fast: {ultra_time:.3f}s, Computation: {computation_time:.1f}ms, Cached: {cached}")
    else:
        print(f"    ❌ Ultra-Fast failed: {response.status_code}")
    
    return original_time, ultra_time

def main():
    """Main performance breakdown function"""
    print("🚀 Fuze Minimal Performance Test")
    print("=" * 50)
    
    # Login
    token = login()
    if not token:
        print("❌ Login failed. Please check your credentials.")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test different components
    network_latency = test_network_latency()
    flask_overhead = test_flask_overhead()
    db_performance = test_database_performance(headers)
    redis_performance = test_redis_performance(headers)
    original_time, ultra_time = test_recommendation_breakdown(headers)
    
    # Analysis
    print("\n" + "=" * 80)
    print("📊 PERFORMANCE BREAKDOWN ANALYSIS")
    print("=" * 80)
    
    print(f"\n🔍 Component Breakdown:")
    print(f"  Network Latency:     {network_latency:.3f}s")
    print(f"  Flask Overhead:      {flask_overhead:.3f}s")
    print(f"  Database Query:      {db_performance:.3f}s")
    print(f"  Redis Request:       {redis_performance:.3f}s")
    print(f"  Original Recs:       {original_time:.3f}s")
    print(f"  Ultra-Fast Recs:     {ultra_time:.3f}s")
    
    # Calculate overhead
    total_overhead = network_latency + flask_overhead
    db_overhead = db_performance - network_latency
    recommendation_overhead = original_time - db_performance
    
    print(f"\n💡 Overhead Analysis:")
    print(f"  Total System Overhead: {total_overhead:.3f}s")
    print(f"  Database Overhead:     {db_overhead:.3f}s")
    print(f"  Recommendation Logic:  {recommendation_overhead:.3f}s")
    
    # Recommendations
    print(f"\n🎯 Recommendations:")
    if total_overhead > 0.5:
        print(f"  ⚠️ High system overhead ({total_overhead:.3f}s) - consider optimization")
    if db_overhead > 1.0:
        print(f"  ⚠️ High database overhead ({db_overhead:.3f}s) - check indexes and queries")
    if recommendation_overhead > 1.0:
        print(f"  ⚠️ High recommendation overhead ({recommendation_overhead:.3f}s) - optimize logic")
    
    if ultra_time < original_time:
        improvement = (original_time - ultra_time) / original_time * 100
        print(f"  ✅ Ultra-fast engine is {improvement:.1f}% faster")
    else:
        print(f"  ⚠️ Ultra-fast engine is not significantly faster")
    
    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'network_latency': network_latency,
        'flask_overhead': flask_overhead,
        'db_performance': db_performance,
        'redis_performance': redis_performance,
        'original_time': original_time,
        'ultra_time': ultra_time,
        'total_overhead': total_overhead,
        'db_overhead': db_overhead,
        'recommendation_overhead': recommendation_overhead
    }
    
    with open('minimal_performance_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📊 Detailed results saved to minimal_performance_results.json")

if __name__ == "__main__":
    main() 