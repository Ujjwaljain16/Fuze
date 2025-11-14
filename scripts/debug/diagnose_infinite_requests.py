#!/usr/bin/env python3
"""
Diagnostic script to identify the source of infinite requests
"""

import requests
import time
import threading
from datetime import datetime

BASE_URL = 'http://127.0.0.1:5000'

def print_header(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def test_single_request():
    """Test a single request to see if it completes normally"""
    try:
        print("Testing single request...")
        start_time = time.time()
        
        response = requests.get(f'{BASE_URL}/api/recommendations/general', timeout=30)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Request completed in {duration:.2f} seconds")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print(f"Received {len(recommendations)} recommendations")
            return True
        else:
            print(f"Request failed with status {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def monitor_server_activity():
    """Monitor server activity for a short period"""
    print("Monitoring server activity for 10 seconds...")
    
    # Make a few requests and monitor timing
    for i in range(3):
        print(f"\n--- Request {i+1} ---")
        start_time = time.time()
        
        try:
            response = requests.get(f'{BASE_URL}/api/recommendations/general', timeout=10)
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Request {i+1} completed in {duration:.2f} seconds")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                recommendations = data.get('recommendations', [])
                print(f"Recommendations: {len(recommendations)}")
            
        except Exception as e:
            print(f"Request {i+1} failed: {e}")
        
        time.sleep(1)  # Wait between requests

def check_background_service():
    """Check if background service is running and causing issues"""
    print("\nChecking background analysis service...")
    
    try:
        # Check if the service is running by trying to get stats
        response = requests.get(f'{BASE_URL}/api/recommendations/analysis/stats', timeout=5)
        
        if response.status_code == 200:
            stats = response.json()
            print("✅ Background service is accessible")
            print(f"Stats: {stats}")
        else:
            print(f"❌ Background service returned status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Background service check failed: {e}")

def test_concurrent_requests():
    """Test multiple concurrent requests to see if they cause issues"""
    print("\nTesting concurrent requests...")
    
    def make_request(request_id):
        try:
            start_time = time.time()
            response = requests.get(f'{BASE_URL}/api/recommendations/general', timeout=15)
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Request {request_id}: {duration:.2f}s, Status: {response.status_code}")
            return True
        except Exception as e:
            print(f"Request {request_id} failed: {e}")
            return False
    
    # Start 3 concurrent requests
    threads = []
    for i in range(3):
        thread = threading.Thread(target=make_request, args=(i+1,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print("Concurrent requests completed")

def main():
    """Main diagnostic function"""
    print_header("INFINITE REQUEST DIAGNOSTIC")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing server: {BASE_URL}")
    
    # Test 1: Single request
    print_header("TEST 1: SINGLE REQUEST")
    single_success = test_single_request()
    
    # Test 2: Monitor activity
    print_header("TEST 2: SERVER ACTIVITY MONITORING")
    monitor_server_activity()
    
    # Test 3: Background service check
    print_header("TEST 3: BACKGROUND SERVICE CHECK")
    check_background_service()
    
    # Test 4: Concurrent requests
    print_header("TEST 4: CONCURRENT REQUESTS")
    test_concurrent_requests()
    
    print_header("DIAGNOSTIC COMPLETED")
    
    if single_success:
        print("✅ Single requests work normally")
        print("💡 If you're experiencing infinite requests, it might be:")
        print("   - Frontend useEffect loops")
        print("   - Background service issues")
        print("   - Network connectivity problems")
        print("   - Browser caching issues")
    else:
        print("❌ Single requests are failing")
        print("💡 Check server logs for errors")

if __name__ == "__main__":
    main() 