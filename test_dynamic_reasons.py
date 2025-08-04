#!/usr/bin/env python3
"""
Test Dynamic Recommendation Reasons
Test that recommendation reasons are now dynamic and content-specific
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

def test_dynamic_reasons():
    """Test that recommendation reasons are dynamic"""
    print("🧪 Testing Dynamic Recommendation Reasons")
    print("=" * 45)
    
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
    
    # Test with different user inputs to see different reasons
    test_cases = [
        {
            "title": "Java Development",
            "technologies": "java, spring, maven",
            "description": "Learning Java development",
            "max_recommendations": 3
        },
        {
            "title": "JavaScript React",
            "technologies": "javascript, react, node",
            "description": "Frontend development with React",
            "max_recommendations": 3
        },
        {
            "title": "Python Data Science",
            "technologies": "python, pandas, numpy",
            "description": "Data science with Python",
            "max_recommendations": 3
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test Case {i}: {test_case['title']}")
        print("-" * 40)
        
        try:
            start_time = time.time()
            response = requests.post(f"{BASE_URL}/api/recommendations/fast-gemini", json=test_case, headers=headers)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                recommendations = data.get('recommendations', [])
                
                print(f"✅ Got {len(recommendations)} recommendations in {response_time:.3f}s")
                
                # Check for unique reasons
                reasons = []
                for j, rec in enumerate(recommendations):
                    reason = rec.get('reason', 'No reason')
                    reasons.append(reason)
                    print(f"   {j+1}. Reason: {reason}")
                
                # Check if reasons are unique
                unique_reasons = list(set(reasons))
                if len(unique_reasons) == len(reasons):
                    print(f"✅ All reasons are unique ({len(unique_reasons)} unique reasons)")
                else:
                    print(f"⚠️ Some reasons are duplicated ({len(unique_reasons)} unique out of {len(reasons)} total)")
                
                # Check if reasons are dynamic (not generic)
                generic_reasons = ['Relevant content for learning', 'Recommended based on content quality']
                dynamic_count = sum(1 for reason in reasons if reason not in generic_reasons)
                print(f"✅ {dynamic_count}/{len(reasons)} reasons are dynamic (not generic)")
                
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Test case {i} error: {e}")
    
    print("\n" + "=" * 45)
    print("🎯 Dynamic Reasons Test Complete!")
    print("=" * 45)

if __name__ == "__main__":
    test_dynamic_reasons() 