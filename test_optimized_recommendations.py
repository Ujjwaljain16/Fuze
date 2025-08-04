#!/usr/bin/env python3
"""
Test script to verify optimized recommendation performance
"""

import time
import requests
import json

def test_recommendation_performance():
    """Test the performance of optimized recommendations"""
    
    # Test configuration
    base_url = "http://localhost:5000"
    test_user_id = 1  # Assuming user ID 1 exists
    
    # Test endpoints
    endpoints = [
        "/api/recommendations/general",
        "/api/recommendations/unified",
        "/api/recommendations/smart-recommendations"
    ]
    
    print("🚀 Testing Optimized Recommendation Performance")
    print("=" * 50)
    
    for endpoint in endpoints:
        print(f"\n📊 Testing: {endpoint}")
        
        # Test multiple times to get average
        times = []
        for i in range(3):
            start_time = time.time()
            
            try:
                if endpoint == "/api/recommendations/smart-recommendations":
                    # POST request with JSON body
                    response = requests.post(
                        f"{base_url}{endpoint}",
                        headers={"Authorization": "Bearer test-token"},
                        json={"user_input": {"technologies": "python,react"}},
                        timeout=30
                    )
                else:
                    # GET request
                    response = requests.get(
                        f"{base_url}{endpoint}",
                        headers={"Authorization": "Bearer test-token"},
                        timeout=30
                    )
                
                end_time = time.time()
                duration = (end_time - start_time) * 1000  # Convert to milliseconds
                times.append(duration)
                
                if response.status_code == 200:
                    print(f"  ✅ Request {i+1}: {duration:.2f}ms")
                else:
                    print(f"  ❌ Request {i+1}: HTTP {response.status_code} - {duration:.2f}ms")
                    
            except requests.exceptions.Timeout:
                print(f"  ⏰ Request {i+1}: Timeout (>30s)")
                times.append(30000)  # 30 seconds as timeout
            except Exception as e:
                print(f"  ❌ Request {i+1}: Error - {str(e)}")
                times.append(30000)
        
        # Calculate average
        if times:
            avg_time = sum(times) / len(times)
            print(f"  📈 Average: {avg_time:.2f}ms")
            
            if avg_time < 5000:
                print(f"  🎉 Performance: EXCELLENT (< 5s)")
            elif avg_time < 15000:
                print(f"  ✅ Performance: GOOD (< 15s)")
            else:
                print(f"  ⚠️  Performance: SLOW (> 15s)")
    
    print("\n" + "=" * 50)
    print("🎯 Optimization Summary:")
    print("✅ Removed direct Gemini API calls from basic recommendation engines")
    print("✅ Now using cached analysis from ContentAnalysis table")
    print("✅ Fallback to basic scoring when no cached analysis available")
    print("✅ Should see significant performance improvement!")

if __name__ == "__main__":
    test_recommendation_performance() 