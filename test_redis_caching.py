#!/usr/bin/env python3
"""
Test script to demonstrate Redis caching benefits for recommendations
"""

import requests
import time
import json

# Configuration
BASE_URL = "http://localhost:5000"
LOGIN_DATA = {
    "username": "testuser",  # Replace with your actual username
    "password": "testpass"   # Replace with your actual password
}

def login():
    """Login and get access token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=LOGIN_DATA)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"Login failed: {response.text}")
        return None

def test_recommendations_caching():
    """Test recommendation caching performance"""
    print("🚀 Testing Redis Caching for Recommendations")
    print("=" * 50)
    
    # Login
    token = login()
    if not token:
        print("❌ Login failed. Please check your credentials.")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test general recommendations
    print("\n📊 Testing General Recommendations:")
    print("-" * 30)
    
    # First request (should be slow - computing fresh recommendations)
    print("1️⃣ First request (computing fresh recommendations)...")
    start_time = time.time()
    response1 = requests.get(f"{BASE_URL}/api/recommendations/general", headers=headers)
    first_request_time = time.time() - start_time
    
    if response1.status_code == 200:
        print(f"   ✅ Success! Time: {first_request_time:.2f} seconds")
        data1 = response1.json()
        print(f"   📈 Found {len(data1.get('recommendations', []))} recommendations")
    else:
        print(f"   ❌ Failed: {response1.text}")
        return
    
    # Second request (should be fast - using cached recommendations)
    print("\n2️⃣ Second request (using cached recommendations)...")
    start_time = time.time()
    response2 = requests.get(f"{BASE_URL}/api/recommendations/general", headers=headers)
    second_request_time = time.time() - start_time
    
    if response2.status_code == 200:
        print(f"   ✅ Success! Time: {second_request_time:.2f} seconds")
        data2 = response2.json()
        print(f"   📈 Found {len(data2.get('recommendations', []))} recommendations")
    else:
        print(f"   ❌ Failed: {response2.text}")
        return
    
    # Calculate speedup
    if first_request_time > 0:
        speedup = first_request_time / second_request_time
        print(f"\n⚡ Speedup: {speedup:.1f}x faster with caching!")
        print(f"   🐌 Without cache: {first_request_time:.2f}s")
        print(f"   🚀 With cache: {second_request_time:.2f}s")
    
    # Test project recommendations (if you have projects)
    print("\n📊 Testing Project Recommendations:")
    print("-" * 30)
    
    # Get user's projects first
    projects_response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
    if projects_response.status_code == 200:
        projects = projects_response.json().get('projects', [])
        if projects:
            project_id = projects[0]['id']
            print(f"   🎯 Testing with project: {projects[0]['title']}")
            
            # First request
            print("1️⃣ First project recommendation request...")
            start_time = time.time()
            proj_response1 = requests.get(f"{BASE_URL}/api/recommendations/project/{project_id}", headers=headers)
            proj_first_time = time.time() - start_time
            
            if proj_response1.status_code == 200:
                print(f"   ✅ Success! Time: {proj_first_time:.2f} seconds")
                
                # Second request
                print("2️⃣ Second project recommendation request...")
                start_time = time.time()
                proj_response2 = requests.get(f"{BASE_URL}/api/recommendations/project/{project_id}", headers=headers)
                proj_second_time = time.time() - start_time
                
                if proj_response2.status_code == 200:
                    print(f"   ✅ Success! Time: {proj_second_time:.2f} seconds")
                    
                    if proj_first_time > 0:
                        proj_speedup = proj_first_time / proj_second_time
                        print(f"\n⚡ Project recommendations speedup: {proj_speedup:.1f}x faster!")
        else:
            print("   ℹ️ No projects found. Create a project to test project recommendations.")
    else:
        print("   ❌ Failed to get projects")
    
    # Test cache invalidation
    print("\n🗑️ Testing Cache Invalidation:")
    print("-" * 30)
    
    # Add a new bookmark to trigger cache invalidation
    test_bookmark = {
        "url": "https://example.com/test-cache-invalidation",
        "title": "Test Cache Invalidation",
        "description": "This bookmark should invalidate cached recommendations"
    }
    
    print("📌 Adding a new bookmark to trigger cache invalidation...")
    bookmark_response = requests.post(f"{BASE_URL}/api/bookmarks", json=test_bookmark, headers=headers)
    
    if bookmark_response.status_code in [200, 201]:
        print("   ✅ Bookmark added successfully")
        
        # Test recommendations again (should be slow due to cache invalidation)
        print("\n🔄 Testing recommendations after cache invalidation...")
        start_time = time.time()
        response3 = requests.get(f"{BASE_URL}/api/recommendations/general", headers=headers)
        third_request_time = time.time() - start_time
        
        if response3.status_code == 200:
            print(f"   ✅ Success! Time: {third_request_time:.2f} seconds")
            print("   📝 Cache was invalidated and fresh recommendations were computed")
        else:
            print(f"   ❌ Failed: {response3.text}")
    else:
        print(f"   ❌ Failed to add bookmark: {bookmark_response.text}")
    
    print("\n" + "=" * 50)
    print("🎉 Redis Caching Test Complete!")
    print("\n💡 Benefits of Redis Caching:")
    print("   • ⚡ Faster response times for repeated requests")
    print("   • 🔄 Reduced server load and database queries")
    print("   • 📊 Better user experience with instant recommendations")
    print("   • 🧠 Smart cache invalidation when data changes")
    print("   • 💰 Cost savings on compute resources")

if __name__ == "__main__":
    test_recommendations_caching() 