#!/usr/bin/env python3
"""
Test script for Projects API endpoints
Tests all CRUD operations: GET, POST, PUT, DELETE
"""

import requests
import json
import sys
from datetime import datetime

# API Configuration
BASE_URL = "http://localhost:5000"
AUTH_URL = f"{BASE_URL}/api/auth/login"
PROJECTS_URL = f"{BASE_URL}/api/projects"

def get_auth_token(username="testuser", password="testpass"):
    """Get authentication token"""
    try:
        response = requests.post(AUTH_URL, json={
            "username": username,
            "password": password
        })
        
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"❌ Authentication failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Authentication error: {str(e)}")
        return None

def test_projects_api():
    """Test all Projects API endpoints"""
    print("🧪 Testing Projects API Endpoints")
    print("=" * 50)
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("❌ Cannot proceed without authentication token")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: GET /api/projects (List projects)
    print("\n1️⃣ Testing GET /api/projects (List projects)")
    try:
        response = requests.get(PROJECTS_URL, headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: Found {len(data.get('projects', []))} projects")
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   ❌ Failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 2: POST /api/projects (Create project)
    print("\n2️⃣ Testing POST /api/projects (Create project)")
    test_project = {
        "title": f"Test Project {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "description": "This is a test project created by the API test script",
        "technologies": "Python, Flask, React, PostgreSQL"
    }
    
    try:
        response = requests.post(PROJECTS_URL, headers=headers, json=test_project)
        print(f"   Status: {response.status_code}")
        if response.status_code == 201:
            data = response.json()
            project_id = data.get("project_id")
            print(f"   ✅ Success: Created project with ID {project_id}")
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   ❌ Failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    # Test 3: GET /api/projects/{id} (Get specific project)
    print(f"\n3️⃣ Testing GET /api/projects/{project_id} (Get specific project)")
    try:
        response = requests.get(f"{PROJECTS_URL}/{project_id}", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: Retrieved project {project_id}")
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   ❌ Failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 4: PUT /api/projects/{id} (Update project)
    print(f"\n4️⃣ Testing PUT /api/projects/{project_id} (Update project)")
    updated_project = {
        "title": f"Updated Test Project {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "description": "This project has been updated by the API test script",
        "technologies": "Python, Flask, React, PostgreSQL, Docker"
    }
    
    try:
        response = requests.put(f"{PROJECTS_URL}/{project_id}", headers=headers, json=updated_project)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: Updated project {project_id}")
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   ❌ Failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 5: DELETE /api/projects/{id} (Delete project)
    print(f"\n5️⃣ Testing DELETE /api/projects/{project_id} (Delete project)")
    try:
        response = requests.delete(f"{PROJECTS_URL}/{project_id}", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: Deleted project {project_id}")
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   ❌ Failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 6: Verify project is deleted
    print(f"\n6️⃣ Testing GET /api/projects/{project_id} (Verify deletion)")
    try:
        response = requests.get(f"{PROJECTS_URL}/{project_id}", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 404:
            print(f"   ✅ Success: Project {project_id} not found (properly deleted)")
        else:
            print(f"   ⚠️  Warning: Project {project_id} still exists")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 Projects API Testing Complete!")
    return True

def test_error_handling():
    """Test error handling scenarios"""
    print("\n🔍 Testing Error Handling")
    print("=" * 30)
    
    # Test without authentication
    print("\n1️⃣ Testing without authentication")
    try:
        response = requests.get(PROJECTS_URL)
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Success: Properly rejected unauthenticated request")
        else:
            print(f"   ⚠️  Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test invalid project ID
    print("\n2️⃣ Testing invalid project ID")
    token = get_auth_token()
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.get(f"{PROJECTS_URL}/999999", headers=headers)
            print(f"   Status: {response.status_code}")
            if response.status_code == 404:
                print("   ✅ Success: Properly handled invalid project ID")
            else:
                print(f"   ⚠️  Unexpected status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting Projects API Tests")
    
    # Test main functionality
    success = test_projects_api()
    
    # Test error handling
    test_error_handling()
    
    if success:
        print("\n✅ All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1) 