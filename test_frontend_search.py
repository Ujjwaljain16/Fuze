#!/usr/bin/env python3
"""
Test script to verify the updated backend semantic search endpoint
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_semantic_search():
    """Test the semantic search endpoint"""
    
    # You'll need to get a valid JWT token first
    # For testing, you can either:
    # 1. Run the Flask app and get a token from the login endpoint
    # 2. Use a test token if you have one
    
    print("🧪 Testing Backend Semantic Search")
    print("=" * 50)
    
    # Test data
    test_queries = [
        "React hooks",
        "JavaScript promises", 
        "Python machine learning",
        "Database design"
    ]
    
    # Note: You'll need to replace this with a valid JWT token
    # You can get one by logging in through your frontend
    jwt_token = "YOUR_JWT_TOKEN_HERE"  # Replace with actual token
    
    if jwt_token == "YOUR_JWT_TOKEN_HERE":
        print("⚠️  Please replace 'YOUR_JWT_TOKEN_HERE' with a valid JWT token")
        print("   You can get one by:")
        print("   1. Starting your Flask app: python app.py")
        print("   2. Logging in through your frontend")
        print("   3. Getting the token from browser dev tools")
        return
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {jwt_token}'
    }
    
    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        
        try:
            response = requests.post(
                'http://localhost:5000/api/search/supabase-semantic',
                headers=headers,
                json={
                    'query': query,
                    'limit': 3
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success! Found {len(data.get('results', []))} results")
                
                results = data.get('results', [])
                for i, result in enumerate(results, 1):
                    print(f"   {i}. {result.get('title', 'No title')[:50]}...")
                    print(f"      Similarity: {result.get('similarity_percentage', 'N/A')}%")
                    print(f"      URL: {result.get('url', 'No URL')}")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Could not connect to Flask app")
            print("   Make sure to run: python app.py")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print(f"\n🎉 Backend semantic search test completed!")

def test_without_auth():
    """Test the endpoint structure without authentication"""
    
    print("🧪 Testing Endpoint Structure (without auth)")
    print("=" * 50)
    
    try:
        response = requests.post(
            'http://localhost:5000/api/search/supabase-semantic',
            headers={'Content-Type': 'application/json'},
            json={'query': 'test', 'limit': 3}
        )
        
        if response.status_code == 401:
            print("✅ Endpoint is working (requires authentication as expected)")
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Flask app")
        print("   Make sure to run: python app.py")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    """Main function"""
    print("Choose test option:")
    print("1. Test with authentication (requires JWT token)")
    print("2. Test endpoint structure (no auth)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        test_semantic_search()
    elif choice == "2":
        test_without_auth()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main() 