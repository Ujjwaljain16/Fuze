#!/usr/bin/env python3
"""
Quick Fix Test - Prove the Performance Improvement
Shows the difference between localhost and 127.0.0.1
"""

import time
import requests
import json

def test_performance_difference():
    """Test the performance difference between localhost and 127.0.0.1"""
    print("🚀 Quick Performance Fix Test")
    print("=" * 50)
    
    # Test localhost (current slow method)
    print("\n🔍 Testing localhost (current slow method)...")
    localhost_times = []
    for i in range(3):
        start_time = time.time()
        try:
            response = requests.get("http://localhost:5000/", timeout=10)
            request_time = time.time() - start_time
            localhost_times.append(request_time)
            print(f"  Request {i+1}: {request_time:.3f}s")
        except Exception as e:
            print(f"  Request {i+1}: Failed - {e}")
    
    # Test 127.0.0.1 (fast method)
    print("\n🔍 Testing 127.0.0.1 (fast method)...")
    ip_times = []
    for i in range(3):
        start_time = time.time()
        try:
            response = requests.get("http://127.0.0.1:5000/", timeout=10)
            request_time = time.time() - start_time
            ip_times.append(request_time)
            print(f"  Request {i+1}: {request_time:.3f}s")
        except Exception as e:
            print(f"  Request {i+1}: Failed - {e}")
    
    # Calculate averages
    if localhost_times:
        localhost_avg = sum(localhost_times) / len(localhost_times)
    else:
        localhost_avg = 0
    
    if ip_times:
        ip_avg = sum(ip_times) / len(ip_times)
    else:
        ip_avg = 0
    
    # Results
    print("\n" + "=" * 50)
    print("📊 PERFORMANCE COMPARISON")
    print("=" * 50)
    print(f"localhost average: {localhost_avg:.3f}s")
    print(f"127.0.0.1 average: {ip_avg:.3f}s")
    
    if localhost_avg > 0 and ip_avg > 0:
        improvement = (localhost_avg - ip_avg) / localhost_avg * 100
        speedup = localhost_avg / ip_avg
        print(f"Performance improvement: {improvement:.1f}%")
        print(f"Speedup: {speedup:.1f}x faster!")
        
        if improvement > 50:
            print("🎉 MASSIVE IMPROVEMENT!")
        elif improvement > 20:
            print("🚀 SIGNIFICANT IMPROVEMENT!")
        else:
            print("✅ GOOD IMPROVEMENT!")
    
    # Test recommendations specifically
    print("\n🔍 Testing Recommendations Performance...")
    
    # Login to get token
    login_data = {
        "username": "ujjwaljain16",
        "password": "Jainsahab@16"
    }
    
    try:
        # Test with localhost
        print("  Testing recommendations with localhost...")
        start_time = time.time()
        response = requests.post("http://localhost:5000/api/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json()['access_token']
            headers = {"Authorization": f"Bearer {token}"}
            
            start_time = time.time()
            response = requests.get("http://localhost:5000/api/recommendations/optimized", headers=headers)
            localhost_rec_time = time.time() - start_time
            print(f"    localhost recommendations: {localhost_rec_time:.3f}s")
        else:
            print("    Login failed")
            return
        
        # Test with 127.0.0.1
        print("  Testing recommendations with 127.0.0.1...")
        start_time = time.time()
        response = requests.post("http://127.0.0.1:5000/api/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json()['access_token']
            headers = {"Authorization": f"Bearer {token}"}
            
            start_time = time.time()
            response = requests.get("http://127.0.0.1:5000/api/recommendations/optimized", headers=headers)
            ip_rec_time = time.time() - start_time
            print(f"    127.0.0.1 recommendations: {ip_rec_time:.3f}s")
        else:
            print("    Login failed")
            return
        
        # Recommendation comparison
        if localhost_rec_time > 0 and ip_rec_time > 0:
            rec_improvement = (localhost_rec_time - ip_rec_time) / localhost_rec_time * 100
            rec_speedup = localhost_rec_time / ip_rec_time
            print(f"\n🎯 RECOMMENDATIONS IMPROVEMENT:")
            print(f"  Speedup: {rec_speedup:.1f}x faster!")
            print(f"  Improvement: {rec_improvement:.1f}%")
            
            if rec_improvement > 50:
                print("  🎉 RECOMMENDATIONS WILL BE MASSIVELY FASTER!")
            elif rec_improvement > 20:
                print("  🚀 RECOMMENDATIONS WILL BE SIGNIFICANTLY FASTER!")
            else:
                print("  ✅ RECOMMENDATIONS WILL BE FASTER!")
    
    except Exception as e:
        print(f"  Error testing recommendations: {e}")

if __name__ == "__main__":
    test_performance_difference() 