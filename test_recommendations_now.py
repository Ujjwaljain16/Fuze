#!/usr/bin/env python3
"""
Test recommendations now that database performance is fixed
"""

import requests
import time

def test_with_existing_user():
    """Test with users that might exist"""
    print("Testing with existing users...")
    
    # Try common usernames
    test_users = [
        {"username": "ujjwaljain16", "password": "Jainsahab@16"},
        {"username": "ujjwaljain16", "password": "Jainsahab@16"},
    ]
    
    for user_data in test_users:
        try:
            print(f"\nTrying user: {user_data['username']}")
            start = time.time()
            
            response = requests.post("http://localhost:5000/api/auth/login", 
                                   json=user_data, timeout=10)
            duration = time.time() - start
            
            print(f"   Login: {duration:.2f}s (status: {response.status_code})")
            
            if response.status_code == 200:
                token = response.json().get('access_token')
                print(f"   ✅ SUCCESS! Got token: {token[:20]}...")
                
                # Test recommendations
                print("   Testing recommendations...")
                headers = {"Authorization": f"Bearer {token}"}
                test_data = {
                    "title": "Python Web Development",
                    "description": "Learning Flask and React",
                    "technologies": "Python, Flask, React",
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
                    print(f"   🎉 SUCCESS! Got {len(recommendations)} recommendations!")
                    
                    if recommendations:
                        print("   First recommendation:")
                        rec = recommendations[0]
                        print(f"     Title: {rec.get('title', 'N/A')}")
                        print(f"     Score: {rec.get('score', 'N/A')}")
                        print(f"     Engine: {rec.get('engine_used', 'N/A')}")
                    
                    return True
                else:
                    print(f"   ❌ Recommendations failed: {rec_response.text}")
                    
            elif response.status_code == 401:
                print(f"   ⚠️ Wrong credentials")
            else:
                print(f"   ❌ Unexpected status: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"   ❌ TIMEOUT after 10s")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return False

def create_test_user():
    """Create a test user if none exist"""
    print("\nCreating test user...")
    
    user_data = {
        "username": f"testuser{int(time.time())}",
        "email": f"test{int(time.time())}@example.com",
        "password": "testpass123"
    }
    
    try:
        start = time.time()
        response = requests.post("http://localhost:5000/api/auth/register", 
                               json=user_data, timeout=15)
        duration = time.time() - start
        
        print(f"   Registration: {duration:.2f}s (status: {response.status_code})")
        
        if response.status_code in [201, 409]:
            print(f"   ✅ User created/exists: {user_data['username']}")
            return user_data
        else:
            print(f"   ❌ Registration failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ Registration error: {e}")
        return None

def main():
    """Main test function"""
    print("🚀 Testing Recommendations After Database Fix")
    print("=" * 60)
    
    # First try with existing users
    success = test_with_existing_user()
    
    if not success:
        print("\nNo existing users found, creating test user...")
        user_data = create_test_user()
        
        if user_data:
            print("\nNow testing with new user...")
            success = test_with_existing_user()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 RECOMMENDATIONS ARE WORKING!")
        print("💡 The database performance fix solved the issue!")
        print("💡 You can now use your frontend normally")
    else:
        print("❌ Recommendations still not working")
        print("💡 Check if you have content in your database")
        print("💡 The issue might be lack of content, not performance")

if __name__ == "__main__":
    main()
