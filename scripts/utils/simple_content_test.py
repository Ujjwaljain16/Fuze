#!/usr/bin/env python3
"""
Simple test to add content and test recommendations
"""

import requests
import time

def add_test_content():
    """Add some test content to the database"""
    print("📝 Adding test content...")
    
    # First login
    login_data = {
        "username": "testuser",  # Use existing user
        "password": "testpass123"
    }
    
    try:
        login_response = requests.post("http://localhost:5000/api/auth/login", 
                                     json=login_data, timeout=15)
        
        if login_response.status_code == 200:
            token = login_response.json().get('access_token')
            print("   ✅ Login successful")
            
            # Add test bookmark
            headers = {"Authorization": f"Bearer {token}"}
            bookmark_data = {
                "url": "https://example.com/test",
                "title": "Test Content for Recommendations",
                "source": "test",
                "extracted_text": "This is test content about Python programming and web development. It covers topics like Flask, React, and database design.",
                "tags": "python, flask, react, database",
                "category": "programming",
                "notes": "Test content for recommendations system",
                "quality_score": 8
            }
            
            response = requests.post("http://localhost:5000/api/bookmarks", 
                                   json=bookmark_data, headers=headers, timeout=15)
            
            if response.status_code in [200, 201]:
                print("   ✅ Test content added")
                return token
            else:
                print(f"   ❌ Failed to add content: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
        else:
            print(f"   ❌ Login failed: {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def test_recommendations(token):
    """Test if recommendations work now"""
    print("\n🎯 Testing recommendations...")
    
    headers = {"Authorization": f"Bearer {token}"}
    test_data = {
        "title": "Python Web Development",
        "description": "Learning Flask and React",
        "technologies": "Python, Flask, React",
        "max_recommendations": 3
    }
    
    try:
        print("   Sending request to /api/recommendations/unified-orchestrator...")
        start_time = time.time()
        
        response = requests.post(
            "http://localhost:5000/api/recommendations/unified-orchestrator",
            json=test_data,
            headers=headers,
            timeout=20
        )
        
        duration = time.time() - start_time
        print(f"   Request took: {duration:.2f} seconds")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print(f"   ✅ SUCCESS! Got {len(recommendations)} recommendations")
            
            if recommendations:
                print("   First recommendation:")
                rec = recommendations[0]
                print(f"     Title: {rec.get('title', 'N/A')}")
                print(f"     Score: {rec.get('score', 'N/A')}")
                print(f"     Engine: {rec.get('engine_used', 'N/A')}")
            else:
                print("   ⚠️ No recommendations returned")
                
        elif response.status_code == 500:
            print(f"   ❌ Server error: {response.text}")
            print("   This means the backend is crashing when processing recommendations")
            
        elif response.status_code == 401:
            print("   ❌ Unauthorized - token issue")
            
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("   ❌ Request timed out after 20 seconds")
        print("   The recommendations system is hanging")
        
    except Exception as e:
        print(f"   ❌ Request error: {e}")

def main():
    """Main test function"""
    print("🚀 Simple Recommendations Test")
    print("=" * 50)
    
    # Add test content
    token = add_test_content()
    if not token:
        print("❌ Cannot proceed without content")
        return
    
    # Test recommendations
    test_recommendations(token)
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")
    print("\n💡 Next steps:")
    print("   - If recommendations work: Great! Add more real content")
    print("   - If recommendations fail: Check server logs for errors")
    print("   - If timeout: Check if database has enough content")

if __name__ == "__main__":
    main()
