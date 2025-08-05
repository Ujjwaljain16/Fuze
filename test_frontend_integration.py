#!/usr/bin/env python3
"""
Test Frontend Integration with Unified Orchestrator
Tests the new unified orchestrator endpoint that the frontend will use.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5000"
TEST_USER_ID = 1  # Assuming test user exists

def test_unified_orchestrator_endpoint():
    """Test the main unified orchestrator endpoint"""
    print("🧪 Testing Unified Orchestrator Endpoint")
    print("=" * 50)
    
    # Test data similar to what frontend would send
    test_cases = [
        {
            "name": "Dashboard Recommendations",
            "data": {
                "title": "Dashboard Recommendations",
                "description": "General learning recommendations for dashboard",
                "technologies": "",
                "user_interests": "General learning and skill development",
                "max_recommendations": 5,
                "engine_preference": "fast",
                "diversity_weight": 0.3,
                "quality_threshold": 6,
                "include_global_content": True,
                "enhance_with_gemini": False
            }
        },
        {
            "name": "Project-Specific Recommendations",
            "data": {
                "title": "React Learning Project",
                "description": "Building a modern web application with React",
                "technologies": "React, JavaScript, HTML, CSS",
                "user_interests": "Frontend development and modern web technologies",
                "project_id": 1,
                "max_recommendations": 10,
                "engine_preference": "auto",
                "diversity_weight": 0.3,
                "quality_threshold": 6,
                "include_global_content": True,
                "enhance_with_gemini": True
            }
        },
        {
            "name": "Technology-Specific Recommendations",
            "data": {
                "title": "Python Development",
                "description": "Learning Python for data science and web development",
                "technologies": "Python, Django, Flask, Pandas",
                "user_interests": "Data science and web development",
                "max_recommendations": 8,
                "engine_preference": "auto",
                "diversity_weight": 0.4,
                "quality_threshold": 7,
                "include_global_content": True,
                "enhance_with_gemini": True
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test Case {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{BASE_URL}/api/recommendations/unified-orchestrator",
                json=test_case['data'],
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer test_token_{TEST_USER_ID}'  # Mock token
                },
                timeout=30
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            print(f"⏱️  Response Time: {response_time:.1f}ms")
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                recommendations = data.get('recommendations', [])
                performance_metrics = data.get('performance_metrics', {})
                
                print(f"✅ Success! Found {len(recommendations)} recommendations")
                print(f"🔧 Engine Used: {data.get('engine_used', 'Unknown')}")
                
                if recommendations:
                    print("\n📚 Sample Recommendations:")
                    for j, rec in enumerate(recommendations[:3], 1):
                        print(f"  {j}. {rec.get('title', 'No title')}")
                        print(f"     Score: {rec.get('score', 0):.2f}")
                        print(f"     Engine: {rec.get('engine_used', 'Unknown')}")
                        print(f"     Cached: {rec.get('cached', False)}")
                
                if performance_metrics:
                    print(f"\n📈 Performance Metrics:")
                    print(f"  Total Requests: {performance_metrics.get('total_requests', 0)}")
                    print(f"  Average Response Time: {performance_metrics.get('average_response_time_ms', 0):.1f}ms")
                    print(f"  Cache Hit Rate: {performance_metrics.get('cache_hit_rate', 0):.1%}")
                
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

def test_status_endpoint():
    """Test the status endpoint"""
    print("\n\n🔍 Testing Status Endpoint")
    print("=" * 30)
    
    try:
        response = requests.get(f"{BASE_URL}/api/recommendations/status")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Status endpoint working")
            print(f"🔧 Unified Orchestrator: {data.get('unified_orchestrator_available', False)}")
            print(f"🤖 Gemini Integration: {data.get('gemini_integration_available', False)}")
            print(f"📊 Total Engines: {data.get('total_engines_available', 0)}")
            print(f"⭐ Recommended Engine: {data.get('recommended_engine', 'None')}")
        else:
            print(f"❌ Status endpoint failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Status endpoint error: {e}")

def test_performance_metrics_endpoint():
    """Test the performance metrics endpoint"""
    print("\n\n📊 Testing Performance Metrics Endpoint")
    print("=" * 40)
    
    try:
        response = requests.get(f"{BASE_URL}/api/recommendations/performance-metrics")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Performance metrics endpoint working")
            
            if 'unified_orchestrator' in data:
                metrics = data['unified_orchestrator']
                print(f"🔧 Total Requests: {metrics.get('total_requests', 0)}")
                print(f"⏱️  Average Response Time: {metrics.get('average_response_time_ms', 0):.1f}ms")
                print(f"💾 Cache Hit Rate: {metrics.get('cache_hit_rate', 0):.1%}")
                print(f"🤖 Gemini Enhancements: {metrics.get('gemini_enhancements', 0)}")
            
            if 'gemini_integration' in data:
                gemini_metrics = data['gemini_integration']
                print(f"🤖 Gemini API Calls: {gemini_metrics.get('total_calls', 0)}")
                print(f"🤖 Gemini Success Rate: {gemini_metrics.get('success_rate', 0):.1%}")
                
        else:
            print(f"❌ Performance metrics failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Performance metrics error: {e}")

def test_frontend_compatibility():
    """Test that the response format is compatible with frontend expectations"""
    print("\n\n🎨 Testing Frontend Compatibility")
    print("=" * 35)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/recommendations/unified-orchestrator",
            json={
                "title": "Frontend Compatibility Test",
                "description": "Testing response format compatibility",
                "technologies": "React, JavaScript",
                "user_interests": "Frontend development",
                "max_recommendations": 3,
                "engine_preference": "fast",
                "diversity_weight": 0.3,
                "quality_threshold": 6,
                "include_global_content": True,
                "enhance_with_gemini": False
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer test_token_{TEST_USER_ID}'
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check required fields for frontend
            required_fields = ['recommendations', 'total_recommendations', 'engine_used']
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                print("✅ All required fields present")
                print(f"📊 Total Recommendations: {data['total_recommendations']}")
                print(f"🔧 Engine Used: {data['engine_used']}")
                
                # Check recommendation structure
                if data['recommendations']:
                    rec = data['recommendations'][0]
                    rec_fields = ['id', 'title', 'url', 'score', 'reason']
                    missing_rec_fields = [field for field in rec_fields if field not in rec]
                    
                    if not missing_rec_fields:
                        print("✅ Recommendation structure compatible")
                    else:
                        print(f"⚠️  Missing recommendation fields: {missing_rec_fields}")
                else:
                    print("ℹ️  No recommendations to check structure")
            else:
                print(f"❌ Missing required fields: {missing_fields}")
        else:
            print(f"❌ Request failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Frontend compatibility test error: {e}")

def main():
    """Run all frontend integration tests"""
    print("🚀 Frontend Integration Test Suite")
    print("=" * 50)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Base URL: {BASE_URL}")
    
    # Run tests
    test_status_endpoint()
    test_performance_metrics_endpoint()
    test_unified_orchestrator_endpoint()
    test_frontend_compatibility()
    
    print("\n\n🎉 Frontend Integration Test Suite Complete!")
    print("=" * 50)
    print("✅ If all tests passed, your frontend should work with the new unified orchestrator")
    print("📝 Check the console output above for any issues that need to be addressed")

if __name__ == "__main__":
    main() 