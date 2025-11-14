#!/usr/bin/env python3
"""
Quick test to see which endpoints are working and which are slow
"""

import requests
import time

def test_endpoint(url, method="GET", data=None, timeout=10):
    """Test a single endpoint"""
    try:
        start_time = time.time()
        
        if method == "GET":
            response = requests.get(url, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=timeout)
        
        duration = time.time() - start_time
        
        if response.status_code < 400:
            print(f"   ✅ {method} {url} - {response.status_code} ({duration:.2f}s)")
        else:
            print(f"   ⚠️  {method} {url} - {response.status_code} ({duration:.2f}s)")
            
        return True, duration
        
    except requests.exceptions.Timeout:
        print(f"   ❌ {method} {url} - TIMEOUT after {timeout}s")
        return False, timeout
    except Exception as e:
        print(f"   ❌ {method} {url} - ERROR: {e}")
        return False, 0

def main():
    """Test all endpoints quickly"""
    print("🚀 Quick Endpoint Test")
    print("=" * 50)
    
    endpoints = [
        ("GET", "http://localhost:5000/"),
        ("GET", "http://localhost:5000/api/profile"),
        ("POST", "http://localhost:5000/api/auth/login", {"username": "testuser", "password": "testpass123"}),
        ("GET", "http://localhost:5000/api/recommendations/gemini-status"),
    ]
    
    results = []
    
    for endpoint in endpoints:
        if len(endpoint) == 2:
            method, url = endpoint
            data = None
        else:
            method, url, data = endpoint
            
        success, duration = test_endpoint(url, method, data, timeout=5)
        results.append((url, success, duration))
    
    print("\n" + "=" * 50)
    print("📊 Results Summary:")
    
    working = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"   Working endpoints: {working}/{total}")
    
    if working == 0:
        print("   ❌ All endpoints are failing!")
        print("   💡 Check if your server is actually running")
    elif working < total:
        print("   ⚠️  Some endpoints are failing")
        print("   💡 Check server logs for specific errors")
    else:
        print("   ✅ All endpoints working!")
        print("   💡 The issue might be in the frontend")

if __name__ == "__main__":
    main()
