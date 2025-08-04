#!/usr/bin/env python3
"""
Performance Comparison Test for Fuze Recommendation Systems
Compares original vs optimized recommendation engines
"""

import time
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5000"
LOGIN_DATA = {
    "username": "ujjwaljain16",  # Replace with your actual username
    "password": "Jainsahab@16"   # Replace with your actual password
}

def login():
    """Login and get access token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=LOGIN_DATA)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"Login failed: {response.text}")
        return None

def test_endpoint_performance(endpoint, headers, name, iterations=3):
    """Test endpoint performance over multiple iterations"""
    print(f"\n🔍 Testing {name}...")
    print("-" * 40)
    
    times = []
    success_count = 0
    
    for i in range(iterations):
        print(f"  Iteration {i+1}/{iterations}...")
        
        start_time = time.time()
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        request_time = time.time() - start_time
        
        if response.status_code == 200:
            success_count += 1
            times.append(request_time)
            
            data = response.json()
            recommendations_count = len(data.get('recommendations', []))
            cached = data.get('cached', False)
            computation_time = data.get('computation_time_ms', 0)
            
            print(f"    ✅ Success: {request_time:.2f}s, {recommendations_count} recommendations")
            print(f"       Cached: {cached}, Computation: {computation_time:.1f}ms")
        else:
            print(f"    ❌ Failed: {response.status_code} - {response.text}")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n  📊 Results for {name}:")
        print(f"     Average: {avg_time:.2f}s")
        print(f"     Min: {min_time:.2f}s")
        print(f"     Max: {max_time:.2f}s")
        print(f"     Success Rate: {success_count}/{iterations}")
        
        return {
            'name': name,
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'success_rate': success_count / iterations,
            'times': times
        }
    else:
        print(f"  ❌ No successful requests for {name}")
        return None

def test_caching_performance(headers):
    """Test caching performance by making repeated requests"""
    print(f"\n🔄 Testing Caching Performance...")
    print("-" * 40)
    
    endpoints = [
        ('/api/recommendations/general', 'Original General'),
        ('/api/recommendations/optimized', 'Fast General'),
    ]
    
    caching_results = {}
    
    for endpoint, name in endpoints:
        print(f"\n  Testing {name} caching...")
        
        # First request (should be slow - computing fresh)
        print("    1️⃣ First request (computing fresh)...")
        start_time = time.time()
        response1 = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        first_time = time.time() - start_time
        
        if response1.status_code == 200:
            data1 = response1.json()
            cached1 = data1.get('cached', False)
            print(f"       ✅ Success: {first_time:.2f}s, Cached: {cached1}")
            
            # Second request (should be fast - using cache)
            print("    2️⃣ Second request (using cache)...")
            start_time = time.time()
            response2 = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            second_time = time.time() - start_time
            
            if response2.status_code == 200:
                data2 = response2.json()
                cached2 = data2.get('cached', False)
                print(f"       ✅ Success: {second_time:.2f}s, Cached: {cached2}")
                
                # Calculate speedup
                if first_time > 0 and second_time > 0:
                    speedup = first_time / second_time
                    print(f"       ⚡ Speedup: {speedup:.1f}x faster with caching!")
                    
                    caching_results[name] = {
                        'first_request_time': first_time,
                        'second_request_time': second_time,
                        'speedup': speedup,
                        'first_cached': cached1,
                        'second_cached': cached2
                    }
                else:
                    print(f"       ⚠️ Could not calculate speedup")
            else:
                print(f"       ❌ Second request failed: {response2.status_code}")
        else:
            print(f"       ❌ First request failed: {response1.status_code}")
    
    return caching_results

def test_project_recommendations(headers):
    """Test project-specific recommendations"""
    print(f"\n🎯 Testing Project Recommendations...")
    print("-" * 40)
    
    # Get user's projects first
    projects_response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
    if projects_response.status_code != 200:
        print("❌ Failed to get projects")
        return {}
    
    projects = projects_response.json().get('projects', [])
    if not projects:
        print("⚠️ No projects found for testing")
        return {}
    
    project_id = projects[0]['id']
    project_title = projects[0]['title']
    print(f"  Testing with project: {project_title} (ID: {project_id})")
    
    endpoints = [
        (f'/api/recommendations/project/{project_id}', 'Original Project'),
        (f'/api/recommendations/optimized-project/{project_id}', 'Fast Project'),
    ]
    
    project_results = {}
    
    for endpoint, name in endpoints:
        print(f"\n    Testing {name}...")
        
        start_time = time.time()
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        request_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            recommendations_count = len(data.get('recommendations', []))
            cached = data.get('cached', False)
            computation_time = data.get('computation_time_ms', 0)
            
            print(f"      ✅ Success: {request_time:.2f}s, {recommendations_count} recommendations")
            print(f"         Cached: {cached}, Computation: {computation_time:.1f}ms")
            
            project_results[name] = {
                'request_time': request_time,
                'recommendations_count': recommendations_count,
                'cached': cached,
                'computation_time_ms': computation_time
            }
        else:
            print(f"      ❌ Failed: {response.status_code} - {response.text}")
    
    return project_results

def generate_performance_report(results, caching_results, project_results):
    """Generate a comprehensive performance report"""
    print("\n" + "=" * 80)
    print("📊 PERFORMANCE COMPARISON REPORT")
    print("=" * 80)
    
    # General recommendations comparison
    if results:
        print("\n🏆 GENERAL RECOMMENDATIONS COMPARISON:")
        print("-" * 50)
        
        original_result = next((r for r in results if 'Original' in r['name']), None)
        optimized_result = next((r for r in results if 'Optimized' in r['name']), None)
        
        if original_result and optimized_result:
            improvement = (original_result['avg_time'] - optimized_result['avg_time']) / original_result['avg_time'] * 100
            print(f"Original Engine:  {original_result['avg_time']:.2f}s average")
            print(f"Optimized Engine: {optimized_result['avg_time']:.2f}s average")
            print(f"Improvement:      {improvement:.1f}% faster")
            
            if improvement > 0:
                print(f"🎉 The optimized engine is {improvement:.1f}% faster!")
            else:
                print(f"⚠️ The optimized engine is {abs(improvement):.1f}% slower")
    
    # Caching performance
    if caching_results:
        print("\n⚡ CACHING PERFORMANCE:")
        print("-" * 50)
        
        for name, data in caching_results.items():
            print(f"{name}:")
            print(f"  First request:  {data['first_request_time']:.2f}s")
            print(f"  Second request: {data['second_request_time']:.2f}s")
            print(f"  Speedup:        {data['speedup']:.1f}x faster")
            print(f"  First cached:   {data['first_cached']}")
            print(f"  Second cached:  {data['second_cached']}")
    
    # Project recommendations
    if project_results:
        print("\n🎯 PROJECT RECOMMENDATIONS:")
        print("-" * 50)
        
        for name, data in project_results.items():
            print(f"{name}:")
            print(f"  Request time:   {data['request_time']:.2f}s")
            print(f"  Recommendations: {data['recommendations_count']}")
            print(f"  Cached:         {data['cached']}")
            print(f"  Computation:    {data['computation_time_ms']:.1f}ms")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    print("-" * 50)
    
    if caching_results:
        best_speedup = max(caching_results.values(), key=lambda x: x['speedup'])
        if best_speedup['speedup'] > 5:
            print("✅ Caching is working well - significant speedup achieved")
        else:
            print("⚠️ Caching speedup could be improved")
    
    if results:
        original_result = next((r for r in results if 'Original' in r['name']), None)
        if original_result and original_result['avg_time'] > 2:
            print("⚠️ Original recommendations are slow - consider using optimized engine")
        else:
            print("✅ Original recommendations are performing well")
    
    print("\n🎯 NEXT STEPS:")
    print("-" * 50)
    print("1. Use the optimized endpoints for better performance")
    print("2. Monitor Redis cache hit rates")
    print("3. Consider database indexing for large datasets")
    print("4. Implement async processing for heavy computations")

def main():
    """Main performance comparison function"""
    print("🚀 Fuze Performance Comparison Test")
    print("=" * 50)
    
    # Login
    token = login()
    if not token:
        print("❌ Login failed. Please check your credentials.")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test general recommendations
    results = []
    
    # Test original general recommendations
    original_result = test_endpoint_performance(
        '/api/recommendations/general', 
        headers, 
        'Original General Recommendations'
    )
    if original_result:
        results.append(original_result)
    
    # Test fast general recommendations
    fast_result = test_endpoint_performance(
        '/api/recommendations/optimized', 
        headers, 
        'Fast General Recommendations'
    )
    if fast_result:
        results.append(fast_result)
    
    # Test caching performance
    caching_results = test_caching_performance(headers)
    
    # Test project recommendations
    project_results = test_project_recommendations(headers)
    
    # Generate report
    generate_performance_report(results, caching_results, project_results)
    
    # Save detailed results
    detailed_results = {
        'timestamp': datetime.now().isoformat(),
        'general_results': results,
        'caching_results': caching_results,
        'project_results': project_results
    }
    
    with open('performance_comparison_results.json', 'w') as f:
        json.dump(detailed_results, f, indent=2, default=str)
    
    print(f"\n📊 Detailed results saved to performance_comparison_results.json")

if __name__ == "__main__":
    main() 