#!/usr/bin/env python3
"""
Quick Server Status Test
Tests if the Flask server is running and accessible
"""

import requests
import time

BASE_URL = "http://127.0.0.1:5000"

def test_server_status():
    """Test if the server is running"""
    print("🔍 Testing server status...")
    print(f"🌐 Base URL: {BASE_URL}")
    
    try:
        # Test basic connectivity
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/", timeout=5)
        end_time = time.time()
        
        print(f"✅ Server is running!")
        print(f"   Response time: {end_time - start_time:.3f}s")
        print(f"   Status code: {response.status_code}")
        
        # Test health endpoint if available
        try:
            health_response = requests.get(f"{BASE_URL}/health", timeout=5)
            if health_response.status_code == 200:
                print("✅ Health endpoint accessible")
            else:
                print("⚠️ Health endpoint not available")
        except:
            print("⚠️ Health endpoint not available")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running or not accessible")
        print("   Please start the Flask server first:")
        print("   python app.py")
        return False
        
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return False

def test_auth_endpoints():
    """Test authentication endpoints"""
    print("\n🔐 Testing authentication endpoints...")
    
    try:
        # Test login endpoint
        login_data = {
            "email": "jainujjwal1609@gmail.com",
            "password": "Jainsahab@16"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data, timeout=5)
        
        if response.status_code == 200:
            print("✅ Login endpoint working")
            return True
        elif response.status_code == 401:
            print("⚠️ Login failed (expected for test user)")
            print("   Will try to register test user during performance test")
            return True
        else:
            print(f"⚠️ Login endpoint returned: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Auth endpoint error: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Quick Server Status Test")
    print("=" * 40)
    
    # Test server status
    server_ok = test_server_status()
    
    if server_ok:
        # Test auth endpoints
        auth_ok = test_auth_endpoints()
        
        if auth_ok:
            print("\n✅ Server is ready for testing!")
            print("   You can now run: python test_advanced_gemini_performance.py")
        else:
            print("\n⚠️ Server is running but auth endpoints may have issues")
    else:
        print("\n❌ Server is not ready for testing")
        print("   Please start the Flask server first")

if __name__ == "__main__":
    main() 