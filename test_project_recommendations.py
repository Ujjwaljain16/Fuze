#!/usr/bin/env python3
"""
Test script for project-based recommendations
"""

import requests
import json
import time

def test_project_recommendations():
    """Test project-based recommendations"""
    
    # Base URL
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Project-Based Recommendations")
    print("=" * 50)
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/api/recommendations/status", timeout=5)
        if response.status_code == 200:
            status_data = response.json()
            print(f"✅ Server is running")
            print(f"   Unified Orchestrator: {status_data.get('unified_orchestrator_available', False)}")
            print(f"   Recommended Engine: {status_data.get('recommended_engine', 'Unknown')}")
        else:
            print(f"❌ Server responded with status {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return
    
    # Test 2: Test unified orchestrator endpoint
    print("\n📋 Testing Unified Orchestrator Endpoint")
    print("-" * 40)
    
    test_payload = {
        "title": "React Web Application",
        "description": "Building a modern web application with React hooks and state management",
        "technologies": "React, JavaScript, Node.js, CSS",
        "user_interests": "Frontend development, modern web technologies",
        "project_id": 1,  # Assuming project ID 1 exists
        "max_recommendations": 5,
        "engine_preference": "auto",
        "diversity_weight": 0.3,
        "quality_threshold": 6,
        "include_global_content": True,
        "enhance_with_gemini": False  # Disable for faster testing
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/api/recommendations/unified-orchestrator",
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Unified orchestrator endpoint working")
            print(f"   Response time: {response_time:.2f}ms")
            print(f"   Total recommendations: {data.get('total_recommendations', 0)}")
            print(f"   Engine used: {data.get('engine_used', 'Unknown')}")
            
            # Show performance metrics
            if 'performance_metrics' in data:
                metrics = data['performance_metrics']
                print(f"   Cache hit rate: {metrics.get('cache_hit_rate', 0):.2%}")
                print(f"   Cache hits: {metrics.get('cache_hits', 0)}")
                print(f"   Cache misses: {metrics.get('cache_misses', 0)}")
            
            # Show first recommendation details
            recommendations = data.get('recommendations', [])
            if recommendations:
                first_rec = recommendations[0]
                print(f"\n📌 Sample Recommendation:")
                print(f"   Title: {first_rec.get('title', 'N/A')}")
                print(f"   Score: {first_rec.get('score', 0):.2f}")
                print(f"   Engine: {first_rec.get('engine_used', 'N/A')}")
                print(f"   Reason: {first_rec.get('reason', 'N/A')}")
                print(f"   Technologies: {', '.join(first_rec.get('technologies', [])[:3])}")
                
                # Check for project-specific metadata
                metadata = first_rec.get('metadata', {})
                if 'project_boost' in metadata:
                    print(f"   Project Boost: {metadata['project_boost']}")
                
        elif response.status_code == 401:
            print("❌ Authentication required - need valid JWT token")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing unified orchestrator: {e}")
    
    # Test 3: Test without project_id (general recommendations)
    print("\n📋 Testing General Recommendations (No Project)")
    print("-" * 40)
    
    general_payload = {
        "title": "JavaScript Learning",
        "description": "Learning modern JavaScript concepts",
        "technologies": "JavaScript, ES6, Async/Await",
        "user_interests": "Programming fundamentals",
        "max_recommendations": 3,
        "engine_preference": "auto",
        "enhance_with_gemini": False
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/api/recommendations/unified-orchestrator",
            json=general_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ General recommendations working")
            print(f"   Response time: {response_time:.2f}ms")
            print(f"   Total recommendations: {data.get('total_recommendations', 0)}")
            print(f"   Engine used: {data.get('engine_used', 'Unknown')}")
            
        elif response.status_code == 401:
            print("❌ Authentication required - need valid JWT token")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing general recommendations: {e}")
    
    # Test 4: Performance metrics endpoint
    print("\n📊 Testing Performance Metrics")
    print("-" * 40)
    
    try:
        response = requests.get(f"{base_url}/api/recommendations/performance-metrics", timeout=10)
        if response.status_code == 200:
            metrics = response.json()
            print(f"✅ Performance metrics available")
            print(f"   Cache hit rate: {metrics.get('cache_hit_rate', 0):.2%}")
            print(f"   Total cache hits: {metrics.get('cache_hits', 0)}")
            print(f"   Total cache misses: {metrics.get('cache_misses', 0)}")
            
            # Show engine performance
            engines = metrics.get('engines', {})
            for engine_name, engine_metrics in engines.items():
                print(f"   {engine_name}:")
                print(f"     Response time: {engine_metrics.get('response_time_ms', 0):.2f}ms")
                print(f"     Success rate: {engine_metrics.get('success_rate', 0):.2%}")
                print(f"     Total requests: {engine_metrics.get('total_requests', 0)}")
                
        elif response.status_code == 401:
            print("❌ Authentication required for performance metrics")
        else:
            print(f"❌ Error getting performance metrics: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing performance metrics: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Project-Based Recommendations Test Complete!")
    print("\n💡 Next Steps:")
    print("1. Start your frontend: npm run dev (in frontend directory)")
    print("2. Navigate to a project page to see project-specific recommendations")
    print("3. Check the browser console for any errors")
    print("4. Try refreshing recommendations to see the enhanced project context")

if __name__ == "__main__":
    test_project_recommendations() 