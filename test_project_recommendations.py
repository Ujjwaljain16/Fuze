#!/usr/bin/env python3
"""
Test script to verify improved project recommendations
"""

import requests
import json
import time

def get_auth_token():
    """Get authentication token"""
    try:
        login_data = {
            "email": "jainujjwal1609@gmail.com",
            "password": "Jainsahab@16"
        }
        
        response = requests.post("http://localhost:5000/api/auth/login", json=login_data)
        
        if response.status_code == 200:
            return response.json().get('access_token')
        
        return None
        
    except Exception as e:
        print(f"❌ Auth error: {e}")
        return None

def test_project_recommendations():
    """Test project-specific recommendations"""
    print("\n" + "="*60)
    print("TESTING IMPROVED PROJECT RECOMMENDATIONS")
    print("="*60)
    
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
    
    # Test configuration
    base_url = "http://localhost:5000"
    project_id = 2  # DSA visualiser project
    
    # Test cases
    test_cases = [
        {
            "name": "DSA Visualiser Project Recommendations",
            "endpoint": f"/api/recommendations/project/{project_id}",
            "method": "GET",
            "expected_keywords": ["java", "data structures", "algorithms", "visualization", "bytecode", "jvm"]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        print(f"📡 Endpoint: {test_case['endpoint']}")
        
        try:
            # Make request
            start_time = time.time()
            response = requests.get(f"{base_url}{test_case['endpoint']}", headers=headers)
            response_time = (time.time() - start_time) * 1000
            
            print(f"⏱️  Response Time: {response_time:.2f}ms")
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if we got recommendations
                recommendations = data.get('recommendations', [])
                print(f"📋 Found {len(recommendations)} recommendations")
                
                # Analyze relevance
                relevant_count = 0
                total_score = 0
                
                print("\n📝 Recommendations:")
                for i, rec in enumerate(recommendations[:5], 1):  # Show top 5
                    title = rec.get('title', 'No title')
                    score = rec.get('similarity_score', 0)
                    reason = rec.get('reason', 'No reason')
                    
                    # Check for relevant keywords
                    title_lower = title.lower()
                    is_relevant = any(keyword in title_lower for keyword in test_case['expected_keywords'])
                    
                    if is_relevant:
                        relevant_count += 1
                        print(f"  ✅ {i}. {title} (Score: {score:.3f})")
                        print(f"     Reason: {reason}")
                    else:
                        print(f"  ❌ {i}. {title} (Score: {score:.3f})")
                        print(f"     Reason: {reason}")
                    
                    total_score += score
                
                # Calculate metrics
                avg_score = total_score / len(recommendations) if recommendations else 0
                relevance_percentage = (relevant_count / len(recommendations)) * 100 if recommendations else 0
                
                print(f"\n📊 Analysis:")
                print(f"  Average Score: {avg_score:.3f}")
                print(f"  Relevant Recommendations: {relevant_count}/{len(recommendations)} ({relevance_percentage:.1f}%)")
                
                # Performance check
                if response_time < 2000:  # Less than 2 seconds
                    print(f"  ⚡ Performance: Good ({response_time:.0f}ms)")
                else:
                    print(f"  🐌 Performance: Slow ({response_time:.0f}ms)")
                
                # Quality assessment
                if relevance_percentage > 60:
                    print(f"  🎯 Quality: Excellent ({relevance_percentage:.1f}% relevant)")
                elif relevance_percentage > 40:
                    print(f"  🎯 Quality: Good ({relevance_percentage:.1f}% relevant)")
                elif relevance_percentage > 20:
                    print(f"  🎯 Quality: Fair ({relevance_percentage:.1f}% relevant)")
                else:
                    print(f"  🎯 Quality: Poor ({relevance_percentage:.1f}% relevant)")
                
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    print("\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60)

if __name__ == '__main__':
    test_project_recommendations() 