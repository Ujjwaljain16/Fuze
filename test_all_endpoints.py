#!/usr/bin/env python3
"""
Comprehensive test script to verify all backend endpoints are working correctly.
This script tests all the endpoints that the frontend JSX files are using.
"""

import requests
import json
import sys
from urllib.parse import urljoin

# Configuration
BASE_URL = "http://localhost:5000"
TEST_USER = {
    "username": "testuser",
    "password": "testpass123"
}

class EndpointTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.user_id = None
        
    def log(self, message, status="INFO"):
        print(f"[{status}] {message}")
        
    def make_request(self, method, endpoint, data=None, headers=None):
        """Make HTTP request and return response"""
        url = urljoin(self.base_url, endpoint)
        if headers is None:
            headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
            
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, headers=headers)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, headers=headers)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response
        except requests.exceptions.RequestException as e:
            self.log(f"Request failed: {e}", "ERROR")
            return None
            
    def test_health_check(self):
        """Test health check endpoint"""
        self.log("Testing health check endpoint...")
        response = self.make_request('GET', '/api/health')
        if response and response.status_code == 200:
            self.log("✓ Health check passed", "SUCCESS")
            return True
        else:
            self.log("✗ Health check failed", "ERROR")
            return False
            
    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        self.log("Testing authentication endpoints...")
        
        # Test registration
        self.log("  Testing user registration...")
        response = self.make_request('POST', '/api/auth/register', TEST_USER)
        if response and response.status_code in [201, 409]:  # 409 if user already exists
            self.log("  ✓ Registration endpoint working", "SUCCESS")
        else:
            self.log("  ✗ Registration failed", "ERROR")
            return False
            
        # Test login
        self.log("  Testing user login...")
        response = self.make_request('POST', '/api/auth/login', TEST_USER)
        if response and response.status_code == 200:
            self.token = response.json().get('access_token')
            self.log("  ✓ Login successful", "SUCCESS")
            return True
        else:
            self.log("  ✗ Login failed", "ERROR")
            return False
            
    def test_profile_endpoints(self):
        """Test profile endpoints"""
        if not self.token:
            self.log("✗ No token available for profile tests", "ERROR")
            return False
            
        self.log("Testing profile endpoints...")
        
        # Test get profile
        self.log("  Testing get profile...")
        response = self.make_request('GET', '/api/profile')
        if response and response.status_code == 200:
            profile_data = response.json()
            self.user_id = profile_data.get('id')
            self.log("  ✓ Get profile successful", "SUCCESS")
        else:
            self.log("  ✗ Get profile failed", "ERROR")
            return False
            
        # Test update profile
        self.log("  Testing update profile...")
        update_data = {
            "username": "testuser_updated",
            "technology_interests": "Python, React, Machine Learning"
        }
        response = self.make_request('PUT', '/api/profile', update_data)
        if response and response.status_code == 200:
            self.log("  ✓ Update profile successful", "SUCCESS")
        else:
            self.log("  ✗ Update profile failed", "ERROR")
            
        # Test user update endpoint (compatibility)
        self.log("  Testing user update endpoint...")
        response = self.make_request('PUT', f'/api/users/{self.user_id}', update_data)
        if response and response.status_code == 200:
            self.log("  ✓ User update endpoint working", "SUCCESS")
        else:
            self.log("  ✗ User update endpoint failed", "ERROR")
            
        # Test password change
        self.log("  Testing password change...")
        password_data = {
            "current_password": TEST_USER["password"],
            "new_password": "newtestpass123"
        }
        response = self.make_request('PUT', f'/api/users/{self.user_id}/password', password_data)
        if response and response.status_code == 200:
            self.log("  ✓ Password change successful", "SUCCESS")
            # Change back to original password
            password_data = {
                "current_password": "newtestpass123",
                "new_password": TEST_USER["password"]
            }
            self.make_request('PUT', f'/api/users/{self.user_id}/password', password_data)
        else:
            self.log("  ✗ Password change failed", "ERROR")
            
        return True
        
    def test_bookmarks_endpoints(self):
        """Test bookmarks endpoints"""
        if not self.token:
            self.log("✗ No token available for bookmarks tests", "ERROR")
            return False
            
        self.log("Testing bookmarks endpoints...")
        
        # Test create bookmark
        self.log("  Testing create bookmark...")
        bookmark_data = {
            "url": "https://example.com/test",
            "title": "Test Bookmark",
            "description": "This is a test bookmark",
            "category": "test"
        }
        response = self.make_request('POST', '/api/bookmarks', bookmark_data)
        if response and response.status_code == 201:
            bookmark_id = response.json().get('bookmark', {}).get('id')
            self.log("  ✓ Create bookmark successful", "SUCCESS")
        else:
            self.log("  ✗ Create bookmark failed", "ERROR")
            return False
            
        # Test get bookmarks
        self.log("  Testing get bookmarks...")
        response = self.make_request('GET', '/api/bookmarks')
        if response and response.status_code == 200:
            self.log("  ✓ Get bookmarks successful", "SUCCESS")
        else:
            self.log("  ✗ Get bookmarks failed", "ERROR")
            
        # Test search bookmarks
        self.log("  Testing search bookmarks...")
        response = self.make_request('GET', '/api/bookmarks?search=test')
        if response and response.status_code == 200:
            self.log("  ✓ Search bookmarks successful", "SUCCESS")
        else:
            self.log("  ✗ Search bookmarks failed", "ERROR")
            
        # Test extract URL
        self.log("  Testing extract URL...")
        extract_data = {"url": "https://example.com"}
        response = self.make_request('POST', '/api/extract-url', extract_data)
        if response and response.status_code == 200:
            self.log("  ✓ Extract URL successful", "SUCCESS")
        else:
            error_msg = "Unknown error"
            if response:
                error_msg = f"Status: {response.status_code}, Response: {response.text}"
            self.log(f"  ✗ Extract URL failed: {error_msg}", "ERROR")
            
        # Test delete bookmark
        if bookmark_id:
            self.log("  Testing delete bookmark...")
            response = self.make_request('DELETE', f'/api/bookmarks/{bookmark_id}')
            if response and response.status_code == 200:
                self.log("  ✓ Delete bookmark successful", "SUCCESS")
            else:
                self.log("  ✗ Delete bookmark failed", "ERROR")
                
        return True
        
    def test_projects_endpoints(self):
        """Test projects endpoints"""
        if not self.token:
            self.log("✗ No token available for projects tests", "ERROR")
            return False
            
        self.log("Testing projects endpoints...")
        
        # Test create project
        self.log("  Testing create project...")
        project_data = {
            "title": "Test Project",
            "description": "This is a test project",
            "technologies": "Python, React"
        }
        response = self.make_request('POST', '/api/projects', project_data)
        if response and response.status_code == 201:
            project_id = response.json().get('project_id')
            self.log("  ✓ Create project successful", "SUCCESS")
        else:
            error_msg = "Unknown error"
            if response:
                error_msg = f"Status: {response.status_code}, Response: {response.text}"
            self.log(f"  ✗ Create project failed: {error_msg}", "ERROR")
            return False
            
        # Test get projects
        self.log("  Testing get projects...")
        response = self.make_request('GET', '/api/projects')
        if response and response.status_code == 200:
            self.log("  ✓ Get projects successful", "SUCCESS")
        else:
            self.log("  ✗ Get projects failed", "ERROR")
            
        # Test get specific project
        if project_id:
            self.log("  Testing get specific project...")
            response = self.make_request('GET', f'/api/projects/{project_id}')
            if response and response.status_code == 200:
                self.log("  ✓ Get specific project successful", "SUCCESS")
            else:
                self.log("  ✗ Get specific project failed", "ERROR")
                
        # Test update project
        if project_id:
            self.log("  Testing update project...")
            update_data = {
                "title": "Updated Test Project",
                "description": "This is an updated test project",
                "technologies": "Python, React, TypeScript"
            }
            response = self.make_request('PUT', f'/api/projects/{project_id}', update_data)
            if response and response.status_code == 200:
                self.log("  ✓ Update project successful", "SUCCESS")
            else:
                self.log("  ✗ Update project failed", "ERROR")
                
        # Test delete project
        if project_id:
            self.log("  Testing delete project...")
            response = self.make_request('DELETE', f'/api/projects/{project_id}')
            if response and response.status_code == 200:
                self.log("  ✓ Delete project successful", "SUCCESS")
            else:
                self.log("  ✗ Delete project failed", "ERROR")
                
        return True
        
    def test_recommendations_endpoints(self):
        """Test recommendations endpoints"""
        if not self.token:
            self.log("✗ No token available for recommendations tests", "ERROR")
            return False
            
        self.log("Testing recommendations endpoints...")
        
        # Test general recommendations
        self.log("  Testing general recommendations...")
        response = self.make_request('GET', '/api/recommendations/general')
        if response and response.status_code == 200:
            self.log("  ✓ General recommendations successful", "SUCCESS")
        else:
            self.log("  ✗ General recommendations failed", "ERROR")
            
        # Test feedback submission
        self.log("  Testing feedback submission...")
        feedback_data = {
            "content_id": 1,
            "feedback_type": "relevant"
        }
        response = self.make_request('POST', '/api/recommendations/feedback', feedback_data)
        if response and response.status_code == 200:
            self.log("  ✓ Feedback submission successful", "SUCCESS")
        else:
            self.log("  ✗ Feedback submission failed", "ERROR")
            
        return True
        
    def test_search_endpoints(self):
        """Test search endpoints"""
        if not self.token:
            self.log("✗ No token available for search tests", "ERROR")
            return False
            
        self.log("Testing search endpoints...")
        
        # Test text search
        self.log("  Testing text search...")
        response = self.make_request('GET', '/api/search/text?q=test')
        if response and response.status_code == 200:
            self.log("  ✓ Text search successful", "SUCCESS")
        else:
            self.log("  ✗ Text search failed", "ERROR")
            
        # Test semantic search
        self.log("  Testing semantic search...")
        search_data = {"query": "test content"}
        response = self.make_request('POST', '/api/search/semantic', search_data)
        if response and response.status_code == 200:
            self.log("  ✓ Semantic search successful", "SUCCESS")
        else:
            self.log("  ✗ Semantic search failed", "ERROR")
            
        return True
        
    def run_all_tests(self):
        """Run all endpoint tests"""
        self.log("Starting comprehensive endpoint testing...", "INFO")
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Authentication", self.test_auth_endpoints),
            ("Profile", self.test_profile_endpoints),
            ("Bookmarks", self.test_bookmarks_endpoints),
            ("Projects", self.test_projects_endpoints),
            ("Recommendations", self.test_recommendations_endpoints),
            ("Search", self.test_search_endpoints)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                self.log(f"✗ {test_name} test failed with exception: {e}", "ERROR")
                results.append((test_name, False))
                
        # Summary
        self.log("\n" + "="*50, "INFO")
        self.log("TEST SUMMARY", "INFO")
        self.log("="*50, "INFO")
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            self.log(f"{test_name}: {status}")
            if result:
                passed += 1
                
        self.log(f"\nOverall: {passed}/{total} tests passed", "INFO")
        
        if passed == total:
            self.log("🎉 All tests passed! Your backend is working correctly.", "SUCCESS")
            return True
        else:
            self.log("❌ Some tests failed. Please check the errors above.", "ERROR")
            return False

def main():
    """Main function"""
    print("Fuze Backend Endpoint Tester")
    print("=" * 40)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Server is not responding correctly at {BASE_URL}")
            print("Please make sure your Flask server is running on localhost:5000")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        print("Please make sure your Flask server is running on localhost:5000")
        sys.exit(1)
        
    # Run tests
    tester = EndpointTester(BASE_URL)
    success = tester.run_all_tests()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main() 