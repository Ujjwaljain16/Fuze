#!/usr/bin/env python3
"""
Test Ultra-Fast Recommendation Engine Performance
Verifies the performance improvements from 7.52s to under 1s
"""

import time
import json
import requests
from typing import Dict, Any

def test_ultra_fast_recommendations():
    """Test the ultra-fast recommendation endpoint"""
    
    print("🚀 Testing Ultra-Fast Recommendation Engine Performance")
    print("=" * 60)
    
    # Test configuration
    base_url = "http://localhost:5000"
    test_user_id = 1  # Assuming user 1 exists
    
    # Test data
    test_input = {
        "title": "Python web development",
        "description": "Building modern web applications with Python",
        "technologies": "Python, Flask, React, PostgreSQL",
        "max_recommendations": 10
    }
    
    print(f"📍 Testing endpoint: {base_url}/api/recommendations/ultra-fast")
    print(f"👤 User ID: {test_user_id}")
    print(f"📝 Test input: {test_input}")
    print()
    
    try:
        # First, get a JWT token (you'll need to implement this based on your auth system)
        print("🔐 Getting authentication token...")
        
        # For testing purposes, you might need to manually set a valid token
        # or implement proper authentication flow
        auth_token = "your_jwt_token_here"  # Replace with actual token
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        print("⚡ Testing ultra-fast recommendations...")
        start_time = time.time()
        
        response = requests.post(
            f"{base_url}/api/recommendations/ultra-fast",
            json=test_input,
            headers=headers,
            timeout=30
        )
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        print(f"⏱️  Response time: {response_time:.1f}ms")
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"✅ Success! Status: {response.status_code}")
            print(f"📊 Total recommendations: {result.get('total_recommendations', 0)}")
            print(f"🔧 Engine used: {result.get('engine_used', 'Unknown')}")
            print(f"💾 Cached: {result.get('cached', False)}")
            
            # Performance metrics
            perf_metrics = result.get('performance_metrics', {})
            if perf_metrics:
                print(f"🚀 Vector search: {perf_metrics.get('vector_search_used', False)}")
                print(f"📦 Candidates processed: {perf_metrics.get('candidates_processed', 0)}")
                print(f"🎯 Optimization level: {perf_metrics.get('optimization_level', 'Unknown')}")
            
            # Check if performance target is met
            if response_time < 1000:  # Less than 1 second
                print("🎉 PERFORMANCE TARGET ACHIEVED! (< 1 second)")
            elif response_time < 3000:  # Less than 3 seconds
                print("✅ GOOD PERFORMANCE (< 3 seconds)")
            else:
                print("⚠️  PERFORMANCE NEEDS IMPROVEMENT (> 3 seconds)")
            
            # Show first few recommendations
            recommendations = result.get('recommendations', [])
            if recommendations:
                print(f"\n📋 Top {min(3, len(recommendations))} recommendations:")
                for i, rec in enumerate(recommendations[:3]):
                    print(f"  {i+1}. {rec.get('title', 'No title')}")
                    print(f"     Score: {rec.get('similarity_score', 0):.2f}")
                    print(f"     Quality: {rec.get('quality_score', 0)}")
                    print()
            
        else:
            print(f"❌ Error! Status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out (> 30 seconds)")
    except requests.exceptions.ConnectionError:
        print("🔌 Connection error - make sure the server is running")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    return response_time

def test_regular_recommendations_comparison():
    """Compare with regular recommendations for performance comparison"""
    
    print("\n🔄 Performance Comparison Test")
    print("=" * 40)
    
    base_url = "http://localhost:5000"
    test_input = {
        "title": "Machine learning basics",
        "description": "Introduction to machine learning concepts",
        "technologies": "Python, scikit-learn, TensorFlow",
        "max_recommendations": 10
    }
    
    endpoints = [
        ("/api/recommendations/ultra-fast", "Ultra-Fast Engine"),
        ("/api/recommendations/unified", "Unified Engine"),
        ("/api/recommendations/ensemble", "Ensemble Engine")
    ]
    
    results = {}
    
    for endpoint, engine_name in endpoints:
        try:
            print(f"\n🧪 Testing {engine_name}...")
            
            # You'll need to implement proper authentication here
            headers = {
                "Authorization": "Bearer your_jwt_token_here",
                "Content-Type": "application/json"
            }
            
            start_time = time.time()
            response = requests.post(
                f"{base_url}{endpoint}",
                json=test_input,
                headers=headers,
                timeout=60
            )
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                result = response.json()
                recommendations_count = result.get('total_recommendations', 0)
                
                results[engine_name] = {
                    'response_time_ms': response_time,
                    'recommendations': recommendations_count,
                    'status': 'success'
                }
                
                print(f"  ✅ {response_time:.1f}ms - {recommendations_count} recommendations")
            else:
                results[engine_name] = {
                    'response_time_ms': 0,
                    'recommendations': 0,
                    'status': f'error_{response.status_code}'
                }
                print(f"  ❌ Error {response.status_code}")
                
        except Exception as e:
            results[engine_name] = {
                'response_time_ms': 0,
                'recommendations': 0,
                'status': f'error_{str(e)}'
            }
            print(f"  ❌ Exception: {e}")
    
    # Performance summary
    print(f"\n📊 Performance Summary:")
    print("=" * 40)
    
    for engine_name, result in results.items():
        if result['status'] == 'success':
            print(f"{engine_name}: {result['response_time_ms']:.1f}ms")
        else:
            print(f"{engine_name}: {result['status']}")
    
    # Find fastest engine
    successful_results = {k: v for k, v in results.items() if v['status'] == 'success'}
    if successful_results:
        fastest_engine = min(successful_results.items(), key=lambda x: x[1]['response_time_ms'])
        print(f"\n🏆 Fastest Engine: {fastest_engine[0]} ({fastest_engine[1]['response_time_ms']:.1f}ms)")
    
    return results

def test_database_performance():
    """Test database performance after optimizations"""
    
    print("\n🗄️  Database Performance Test")
    print("=" * 40)
    
    try:
        from add_database_indexes import analyze_table_performance
        analyze_table_performance()
    except ImportError:
        print("⚠️  Database optimization script not available")
    except Exception as e:
        print(f"❌ Database test error: {e}")

if __name__ == "__main__":
    print("🚀 Ultra-Fast Recommendation Engine Performance Test")
    print("=" * 60)
    
    # Test ultra-fast engine
    ultra_fast_time = test_ultra_fast_recommendations()
    
    # Test database performance
    test_database_performance()
    
    # Performance comparison
    comparison_results = test_regular_recommendations_comparison()
    
    # Final summary
    print(f"\n🎯 Final Performance Summary:")
    print("=" * 40)
    print(f"Ultra-Fast Engine: {ultra_fast_time:.1f}ms")
    
    if ultra_fast_time < 1000:
        print("🎉 RECOMMENDATIONS ARE NOW FAST! (< 1 second)")
    elif ultra_fast_time < 3000:
        print("✅ RECOMMENDATIONS ARE ACCEPTABLE (< 3 seconds)")
    else:
        print("⚠️  RECOMMENDATIONS STILL NEED OPTIMIZATION (> 3 seconds)")
    
    print(f"\n💡 Expected improvements:")
    print(f"  - Before: 7.52 seconds")
    print(f"  - After: {ultra_fast_time/1000:.2f} seconds")
    print(f"  - Speedup: {7.52/(ultra_fast_time/1000):.1f}x faster")
