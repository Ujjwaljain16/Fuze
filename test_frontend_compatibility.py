#!/usr/bin/env python3
"""
Frontend Compatibility Test
Tests all endpoints that the frontend uses to ensure seamless integration
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def get_auth_token():
    """Get authentication token"""
    try:
        login_data = {
            "username": "ujjwaljain16",
            "password": "Jainsahab@16"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        
        if response.status_code == 200:
            return response.json().get('access_token')
        
        return None
        
    except Exception as e:
        print(f"❌ Auth error: {e}")
        return None

def test_frontend_compatibility():
    """Test all frontend endpoints"""
    print("🌐 Frontend Compatibility Test")
    print("=" * 40)
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("❌ Failed to get auth token")
        return
    
    print("✅ Got auth token")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test 1: Gemini Status Check
    print("\n🔍 Test 1: Gemini Status Check")
    print("-" * 30)
    try:
        response = requests.get(f"{BASE_URL}/api/recommendations/gemini-status", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Gemini Status: {data.get('gemini_available', False)}")
            print(f"   Status: {data.get('status', 'unknown')}")
        else:
            print(f"❌ Gemini Status failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Gemini Status error: {e}")
    
    # Test 2: Projects Endpoint
    print("\n📁 Test 2: Projects Endpoint")
    print("-" * 30)
    try:
        response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        if response.status_code == 200:
            data = response.json()
            projects = data.get('projects', [])
            print(f"✅ Projects: {len(projects)} found")
            if projects:
                print(f"   Sample: {projects[0].get('title', 'N/A')}")
        else:
            print(f"❌ Projects failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Projects error: {e}")
    
    # Test 3: Fast Gemini Recommendations (POST)
    print("\n🚀 Test 3: Fast Gemini Recommendations (POST)")
    print("-" * 45)
    try:
        test_data = {
            "title": "Frontend Test",
            "technologies": "React, JavaScript, TypeScript",
            "description": "Testing frontend compatibility",
            "max_recommendations": 5
        }
        
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/api/recommendations/fast-gemini", json=test_data, headers=headers)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            context_analysis = data.get('context_analysis', {})
            processing_stats = context_analysis.get('processing_stats', {})
            
            print(f"✅ Fast Gemini: {len(recommendations)} recommendations")
            print(f"   Response Time: {response_time:.3f}s")
            print(f"   Engine: {processing_stats.get('engine', 'unknown')}")
            print(f"   Gemini Enhanced: {processing_stats.get('gemini_enhanced', 0)}")
            print(f"   API Calls: {processing_stats.get('api_calls', 0)}")
            
            if recommendations:
                sample = recommendations[0]
                print(f"   Sample: {sample.get('title', 'N/A')}")
                print(f"   Enhanced: {sample.get('enhanced', False)}")
        else:
            print(f"❌ Fast Gemini failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Fast Gemini error: {e}")
    
    # Test 4: Optimized Recommendations (GET)
    print("\n⚡ Test 4: Optimized Recommendations (GET)")
    print("-" * 40)
    try:
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/api/recommendations/optimized", headers=headers)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            
            print(f"✅ Optimized: {len(recommendations)} recommendations")
            print(f"   Response Time: {response_time:.3f}s")
            
            if recommendations:
                sample = recommendations[0]
                print(f"   Sample: {sample.get('title', 'N/A')}")
        else:
            print(f"❌ Optimized failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Optimized error: {e}")
    
    # Test 5: Fast Gemini Project Recommendations (GET)
    print("\n🎯 Test 5: Fast Gemini Project Recommendations (GET)")
    print("-" * 50)
    try:
        # First get a project ID
        projects_response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        if projects_response.status_code == 200:
            projects = projects_response.json().get('projects', [])
            if projects:
                project_id = projects[0]['id']
                
                start_time = time.time()
                response = requests.get(f"{BASE_URL}/api/recommendations/fast-gemini-project/{project_id}", headers=headers)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    recommendations = data.get('recommendations', [])
                    context_analysis = data.get('context_analysis', {})
                    processing_stats = context_analysis.get('processing_stats', {})
                    
                    print(f"✅ Fast Gemini Project: {len(recommendations)} recommendations")
                    print(f"   Project ID: {project_id}")
                    print(f"   Response Time: {response_time:.3f}s")
                    print(f"   Engine: {processing_stats.get('engine', 'unknown')}")
                    print(f"   Gemini Enhanced: {processing_stats.get('gemini_enhanced', 0)}")
                    
                    if recommendations:
                        sample = recommendations[0]
                        print(f"   Sample: {sample.get('title', 'N/A')}")
                else:
                    print(f"❌ Fast Gemini Project failed: {response.status_code}")
            else:
                print("⚠️ No projects found for testing")
        else:
            print(f"❌ Could not fetch projects: {projects_response.status_code}")
    except Exception as e:
        print(f"❌ Fast Gemini Project error: {e}")
    
    # Test 6: Optimized Project Recommendations (GET)
    print("\n⚡ Test 6: Optimized Project Recommendations (GET)")
    print("-" * 45)
    try:
        # Use the same project ID from previous test
        projects_response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        if projects_response.status_code == 200:
            projects = projects_response.json().get('projects', [])
            if projects:
                project_id = projects[0]['id']
                
                start_time = time.time()
                response = requests.get(f"{BASE_URL}/api/recommendations/optimized-project/{project_id}", headers=headers)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    recommendations = data.get('recommendations', [])
                    
                    print(f"✅ Optimized Project: {len(recommendations)} recommendations")
                    print(f"   Project ID: {project_id}")
                    print(f"   Response Time: {response_time:.3f}s")
                    
                    if recommendations:
                        sample = recommendations[0]
                        print(f"   Sample: {sample.get('title', 'N/A')}")
                else:
                    print(f"❌ Optimized Project failed: {response.status_code}")
            else:
                print("⚠️ No projects found for testing")
        else:
            print(f"❌ Could not fetch projects: {projects_response.status_code}")
    except Exception as e:
        print(f"❌ Optimized Project error: {e}")
    
    # Test 7: Cache Stats
    print("\n📊 Test 7: Cache Statistics")
    print("-" * 25)
    try:
        response = requests.get(f"{BASE_URL}/api/recommendations/fast-gemini-cache-stats", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Cache Stats: {data}")
        else:
            print(f"❌ Cache Stats failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Cache Stats error: {e}")
    
    # Test 8: Clear Cache
    print("\n🧹 Test 8: Clear Cache")
    print("-" * 20)
    try:
        response = requests.post(f"{BASE_URL}/api/recommendations/fast-gemini-clear-cache", headers=headers)
        if response.status_code == 200:
            print("✅ Cache cleared successfully")
        else:
            print(f"❌ Clear Cache failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Clear Cache error: {e}")
    
    print("\n" + "=" * 40)
    print("🎉 Frontend Compatibility Test Complete!")
    print("=" * 40)

if __name__ == "__main__":
    test_frontend_compatibility() 