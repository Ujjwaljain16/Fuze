import requests
import json

BASE_URL = "http://localhost:5000"

def test_api():
    print("🧪 Testing Fuze API...\n")
    
    # Test 1: Register user
    print("1. Testing user registration...")
    register_data = {
        "username": "testuser",
        "password": "password123"
    }
    response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")
    
    # Test 2: Login
    print("2. Testing user login...")
    login_data = {
        "username": "testuser",
        "password": "password123"
    }
    response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        token = response.json().get('access_token')
        print(f"   ✅ Login successful! Token received.\n")
    else:
        print(f"   ❌ Login failed: {response.json()}\n")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 3: Create project
    print("3. Testing project creation...")
    project_data = {
        "title": "Test Project",
        "description": "A test project for API testing",
        "technologies": "Python, Flask, PostgreSQL"
    }
    response = requests.post(f"{BASE_URL}/api/projects", json=project_data, headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 201:
        project_id = response.json().get('project_id')
        print(f"   ✅ Project created! ID: {project_id}\n")
    else:
        print(f"   ❌ Project creation failed: {response.json()}\n")
        return
    
    # Test 4: Save bookmark
    print("4. Testing bookmark saving...")
    bookmark_data = {
        "url": "https://example.com",
        "title": "Example Website",
        "description": "A test bookmark"
    }
    response = requests.post(f"{BASE_URL}/api/bookmarks", json=bookmark_data, headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 201:
        bookmark_id = response.json().get('bookmark_id')
        print(f"   ✅ Bookmark saved! ID: {bookmark_id}\n")
    else:
        print(f"   ❌ Bookmark saving failed: {response.json()}\n")
    
    # Test 5: Get user projects
    print("5. Testing get user projects...")
    response = requests.get(f"{BASE_URL}/api/projects/1", headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")
    
    # Test 6: Get bookmarks
    print("6. Testing get bookmarks...")
    response = requests.get(f"{BASE_URL}/api/bookmarks", headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")
    
    print("🎉 API testing complete!")

if __name__ == "__main__":
    test_api() 