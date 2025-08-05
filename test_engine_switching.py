#!/usr/bin/env python3
"""
Test script to demonstrate engine switching and performance comparison
"""

import requests
import json
import time

def test_engine_switching():
    """Test different engines and their performance"""
    
    base_url = "http://localhost:5000"
    
    print("🚀 Testing Engine Switching and Performance")
    print("=" * 60)
    
    # Test payload
    test_payload = {
        "title": "React Web Application with State Management",
        "description": "Building a modern web application using React hooks, Redux for state management, and TypeScript for type safety. The app will include user authentication, real-time updates, and responsive design.",
        "technologies": "React, TypeScript, Redux, Node.js, MongoDB",
        "user_interests": "Frontend development, state management, modern JavaScript frameworks",
        "project_id": 1,
        "max_recommendations": 5,
        "enhance_with_gemini": False  # Disable for speed comparison
    }
    
    # Test different engine preferences
    engine_tests = [
        {
            "name": "Fast Engine (Speed Optimized)",
            "payload": {**test_payload, "engine_preference": "fast"}
        },
        {
            "name": "Context Engine (Accuracy Optimized)", 
            "payload": {**test_payload, "engine_preference": "context"}
        },
        {
            "name": "Auto Selection (Default)",
            "payload": {**test_payload, "engine_preference": "auto"}
        }
    ]
    
    print("📊 Engine Performance Comparison")
    print("-" * 40)
    
    results = []
    
    for test in engine_tests:
        print(f"\n🧪 Testing: {test['name']}")
        print(f"   Engine Preference: {test['payload']['engine_preference']}")
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{base_url}/api/recommendations/unified-orchestrator",
                json=test['payload'],
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                recommendations = data.get('recommendations', [])
                engine_used = data.get('engine_used', 'Unknown')
                
                print(f"   ✅ Success")
                print(f"   ⏱️  Response Time: {response_time:.2f}ms")
                print(f"   🔧 Engine Used: {engine_used}")
                print(f"   📋 Recommendations: {len(recommendations)}")
                
                # Show first recommendation
                if recommendations:
                    first_rec = recommendations[0]
                    print(f"   🎯 Top Result: {first_rec.get('title', 'N/A')[:50]}...")
                    print(f"   📊 Score: {first_rec.get('score', 0):.2f}")
                
                results.append({
                    "name": test['name'],
                    "response_time": response_time,
                    "engine_used": engine_used,
                    "recommendations_count": len(recommendations),
                    "success": True
                })
                
            elif response.status_code == 401:
                print(f"   ❌ Authentication required")
                results.append({
                    "name": test['name'],
                    "response_time": response_time,
                    "success": False,
                    "error": "Authentication required"
                })
            else:
                print(f"   ❌ Error: {response.status_code}")
                results.append({
                    "name": test['name'],
                    "response_time": response_time,
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                })
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results.append({
                "name": test['name'],
                "response_time": 0,
                "success": False,
                "error": str(e)
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("📈 Performance Summary")
    print("=" * 60)
    
    successful_results = [r for r in results if r['success']]
    
    if successful_results:
        # Find fastest and slowest
        fastest = min(successful_results, key=lambda x: x['response_time'])
        slowest = max(successful_results, key=lambda x: x['response_time'])
        
        print(f"🏆 Fastest: {fastest['name']} ({fastest['response_time']:.2f}ms)")
        print(f"🐌 Slowest: {slowest['name']} ({slowest['response_time']:.2f}ms)")
        
        # Performance comparison
        if len(successful_results) > 1:
            avg_time = sum(r['response_time'] for r in successful_results) / len(successful_results)
            print(f"📊 Average Response Time: {avg_time:.2f}ms")
            
            for result in successful_results:
                speed_diff = result['response_time'] - avg_time
                if speed_diff > 0:
                    print(f"   {result['name']}: +{speed_diff:.2f}ms (slower)")
                else:
                    print(f"   {result['name']}: {speed_diff:.2f}ms (faster)")
    
    print("\n🎯 Engine Recommendations:")
    print("- Use 'fast' for quick, simple queries")
    print("- Use 'context' for complex, detailed projects") 
    print("- Use 'auto' for general use (recommended)")
    print("- Add 'enhance_with_gemini: true' for AI-enhanced results")

def test_different_endpoints():
    """Test different API endpoints"""
    
    base_url = "http://localhost:5000"
    
    print("\n🔗 Testing Different Endpoints")
    print("=" * 40)
    
    endpoints = [
        {
            "name": "Unified Orchestrator (Default)",
            "url": "/api/recommendations/unified-orchestrator",
            "method": "POST"
        },
        {
            "name": "Unified Engine",
            "url": "/api/recommendations/unified", 
            "method": "POST"
        },
        {
            "name": "Smart Engine",
            "url": "/api/recommendations/smart-recommendations",
            "method": "POST"
        },
        {
            "name": "Enhanced Engine",
            "url": "/api/recommendations/enhanced",
            "method": "POST"
        }
    ]
    
    test_payload = {
        "title": "JavaScript Learning",
        "description": "Learning modern JavaScript concepts",
        "technologies": "JavaScript, ES6, Async/Await",
        "max_recommendations": 3
    }
    
    for endpoint in endpoints:
        print(f"\n🧪 Testing: {endpoint['name']}")
        print(f"   Endpoint: {endpoint['url']}")
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{base_url}{endpoint['url']}",
                json=test_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                recommendations = data.get('recommendations', [])
                print(f"   ✅ Success ({response_time:.2f}ms)")
                print(f"   📋 Recommendations: {len(recommendations)}")
            elif response.status_code == 401:
                print(f"   🔐 Authentication required")
            else:
                print(f"   ❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    test_engine_switching()
    test_different_endpoints()
    
    print("\n" + "=" * 60)
    print("🎉 Engine Testing Complete!")
    print("\n💡 How to switch engines in your frontend:")
    print("1. Add 'engine_preference' parameter to your API calls")
    print("2. Use different endpoints for different engines")
    print("3. Monitor performance metrics to choose the best engine")
    print("\n🚀 Your current setup is optimal for most use cases!") 