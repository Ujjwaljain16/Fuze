#!/usr/bin/env python3
"""
Test database performance after fixes
"""

import time
import requests

def test_database_performance():
    """Test if database performance improved"""
    print("Testing Database Performance After Fixes...")
    
    # Test 1: Simple GET (should be fast)
    try:
        start = time.time()
        response = requests.get("http://localhost:5000/", timeout=10)
        duration = time.time() - start
        print(f"   Simple GET: {duration:.2f}s")
    except Exception as e:
        print(f"   Simple GET failed: {e}")
    
    # Test 2: Wrong credentials (should fail fast)
    try:
        start = time.time()
        response = requests.post("http://localhost:5000/api/auth/login", 
                               json={"username": "nonexistent", "password": "wrong"}, 
                               timeout=10)
        duration = time.time() - start
        print(f"   Wrong login: {duration:.2f}s (status: {response.status_code})")
    except Exception as e:
        print(f"   Wrong login failed: {e}")
    
    # Test 3: Try with admin user
    try:
        start = time.time()
        response = requests.post("http://localhost:5000/api/auth/login", 
                               json={"username": "ujjwaljain16", "password": "Jainsahab@16"}, 
                               timeout=15)
        duration = time.time() - start
        
        if response.status_code == 200:
            print(f"   Admin login: {duration:.2f}s - SUCCESS!")
            token = response.json().get('access_token')
            
            # Test recommendations
            print("Testing recommendations...")
            headers = {"Authorization": f"Bearer {token}"}
            test_data = {
                "title": "Test Project",
                "description": "Testing recommendations",
                "max_recommendations": 3
            }
            
            start = time.time()
            rec_response = requests.post(
                "http://localhost:5000/api/recommendations/unified-orchestrator",
                json=test_data,
                headers=headers,
                timeout=20
            )
            rec_duration = time.time() - start
            
            print(f"   Recommendations: {rec_duration:.2f}s (status: {rec_response.status_code})")
            
            if rec_response.status_code == 200:
                data = rec_response.json()
                recommendations = data.get('recommendations', [])
                print(f"   Got {len(recommendations)} recommendations!")
            else:
                print(f"   Recommendations failed: {rec_response.text}")
                
        elif response.status_code == 401:
            print(f"   Admin login: {duration:.2f}s - Wrong credentials")
        else:
            print(f"   Admin login: {duration:.2f}s - Status: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("   Admin login: TIMEOUT after 15s")
    except Exception as e:
        print(f"   Admin login failed: {e}")

def main():
    """Main test function"""
    print("Database Performance Test After Fixes")
    print("=" * 60)
    
    test_database_performance()
    
    print("=" * 60)
    print("Test completed!")
    print("If performance improved:")
    print("   - Restart your Flask server")
    print("   - Try the frontend again")
    print("If still slow:")
    print("   - Check Supabase dashboard")
    print("   - Consider upgrading your Supabase plan")

if __name__ == "__main__":
    main()
