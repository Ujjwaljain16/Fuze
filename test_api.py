import requests
import json
import random
import string

BASE_URL = "http://localhost:5000"

def generate_username():
    """Generate a unique username for testing"""
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"testuser_{random_suffix}"

def test_api():
    print("🧪 Testing Fuze API...\n")
    
    # Generate unique username
    username = generate_username()
    password = "password123"
    
    print(f"Using test username: {username}\n")
    
    # Test 1: Try to login first (in case user exists)
    print("1. Testing user login...")
    login_data = {
        "username": username,
        "password": password
    }
    response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        token = response.json().get('access_token')
        print(f"   ✅ Login successful! User already exists.\n")
    else:
        print(f"   User doesn't exist, creating new user...\n")
        
        # Test 2: Register user
        print("2. Testing user registration...")
        register_data = {
            "username": username,
            "password": password
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
        
        if response.status_code == 201:
            # Test 3: Login with new user
            print("3. Testing login with new user...")
            response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                token = response.json().get('access_token')
                print(f"   ✅ Login successful! Token received.\n")
            else:
                print(f"   ❌ Login failed: {response.json()}\n")
                return
        else:
            print(f"   ❌ Registration failed: {response.json()}\n")
            return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 4: Create project
    print("4. Testing project creation...")
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
    
    # Test 5: Save bookmark
    print("5. Testing bookmark saving...")
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
    
    # Test 6: Get user projects
    print("6. Testing get user projects...")
    response = requests.get(f"{BASE_URL}/api/projects/1", headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")
    
    # Test 7: Get bookmarks
    print("7. Testing get bookmarks...")
    response = requests.get(f"{BASE_URL}/api/bookmarks", headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")
    
    print("🎉 API testing complete!")

if __name__ == "__main__":
    test_api() 