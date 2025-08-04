#!/usr/bin/env python3
"""
Clear cache and test project recommendations
"""

import requests
import json
import time

def get_auth_token():
    """Get authentication token"""
    try:
        login_data = {
            "username": "jainujjwal1609@gmail.com",
            "password": "Jainsahab@16"
        }
        
        response = requests.post("http://localhost:5000/api/auth/login", json=login_data)
        
        if response.status_code == 200:
            return response.json().get('access_token')
        
        return None
        
    except Exception as e:
        print(f"❌ Auth error: {e}")
        return None

def clear_cache_and_test():
    """Clear cache and test project recommendations"""
    print("🧹 CLEARING CACHE AND TESTING")
    print("=" * 50)
    
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
    
    # Clear recommendation cache
    print("\n🧹 Clearing recommendation cache...")
    try:
        response = requests.post("http://localhost:5000/api/recommendations/cache/clear", headers=headers)
        if response.status_code == 200:
            print("✅ Cache cleared successfully")
        else:
            print(f"⚠️ Cache clear response: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Cache clear error: {e}")
    
    # Wait a moment
    time.sleep(1)
    
    # Test project recommendations
    print("\n🧪 Testing project recommendations...")
    try:
        start_time = time.time()
        response = requests.get("http://localhost:5000/api/recommendations/project/2", headers=headers)
        response_time = (time.time() - start_time) * 1000
        
        print(f"⏱️ Response Time: {response_time:.2f}ms")
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print(f"📋 Found {len(recommendations)} recommendations")
            
            # Check if cached
            cached = data.get('cached', False)
            print(f"💾 Cached: {cached}")
            
            # Analyze scores
            print("\n📝 Score Analysis:")
            scores = []
            for i, rec in enumerate(recommendations[:5], 1):
                title = rec.get('title', 'No title')
                score = rec.get('similarity_score', 0)
                reason = rec.get('reason', 'No reason')
                scores.append(score)
                
                print(f"  {i}. {title}")
                print(f"     Score: {score:.3f}")
                print(f"     Reason: {reason}")
            
            if scores:
                avg_score = sum(scores) / len(scores)
                print(f"\n📊 Average Score: {avg_score:.3f}")
                
                # Check for suspicious scores
                if all(score == 1.0 for score in scores):
                    print("🚨 WARNING: All scores are 1.000 - this is suspicious!")
                elif avg_score > 0.8:
                    print("⚠️ High average score - may indicate scoring issues")
                else:
                    print("✅ Scores look reasonable")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n" + "=" * 50)
    print("TEST COMPLETED")

if __name__ == '__main__':
    clear_cache_and_test() 