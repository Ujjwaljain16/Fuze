#!/usr/bin/env python3
"""
Test script for unified recommendations with DSA visualizer project
"""

import requests
import json

def get_auth_token():
    """Get authentication token by logging in"""
    try:
        # Login to get token
        login_data = {
            "email": "jainujjwal1609@gmail.com",
            "password": "Jainsahab@16"
        }
        
        response = requests.post(
            'http://127.0.0.1:5000/api/auth/login',
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('access_token')
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Login exception: {e}")
        return None

def test_phase_status():
    """Test phase status to see which phases are available"""
    print("🔍 Testing Phase Status")
    print("=" * 40)
    
    # Get auth token
    token = get_auth_token()
    if not token:
        return
    
    try:
        response = requests.get(
            'http://127.0.0.1:5000/api/recommendations/phase-status',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Phase Status:")
            print(f"  Phase 1 (Smart Match): {data.get('phase1_available', False)}")
            print(f"  Phase 2 (Power Boost): {data.get('phase2_available', False)}")
            print(f"  Phase 3 (Genius Mode): {data.get('phase3_available', False)}")
            print(f"  Gemini Available: {data.get('gemini_available', False)}")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_unified_recommendations():
    """Test the unified recommendations endpoint"""
    
    # Test phase status first
    test_phase_status()
    print()
    
    # Get authentication token
    print("🔐 Getting authentication token...")
    token = get_auth_token()
    
    if not token:
        print("❌ Could not get authentication token. Please make sure:")
        print("   1. The server is running")
        print("   2. You have a test user with email: test@example.com, password: testpassword123")
        print("   3. Or update the credentials in this test script")
        return
    
    print("✅ Got authentication token")
    
    # Test data for mobile app React Native project
    test_data = {
        "project_title": "Learning Project",
        "project_description": "I want to learn and improve my skills",
        "technologies": "mobile app react native expo",
        "learning_goals": "Master relevant technologies and improve skills",
        "content_type": "all",
        "difficulty": "all",
        "max_recommendations": 10,
        "use_phase1": True,
        "use_phase2": True,
        "use_phase3": True,
        "performance_mode": True
    }
    
    print("\n🧪 Testing Unified Recommendations for Mobile App")
    print("=" * 60)
    print(f"Request data: {json.dumps(test_data, indent=2)}")
    print()
    
    # Test with timing
    import time
    start_time = time.time()
    
    try:
        # Make request to unified endpoint with authentication
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        response = requests.post(
            'http://127.0.0.1:5000/api/recommendations/unified',
            json=test_data,
            headers=headers,
            timeout=30
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"⏱️  Response Time: {response_time:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success! Got recommendations:")
            print(f"Total recommendations: {len(result.get('recommendations', []))}")
            print(f"Phases used: {result.get('phases_used', {})}")
            print(f"Performance mode: {result.get('performance_mode', False)}")
            
            # Debug: Check which phases actually ran
            phases_used = result.get('phases_used', {})
            print(f"🔍 Phase Debug:")
            print(f"  Phase 1 ran: {phases_used.get('phase1', False)}")
            print(f"  Phase 2 ran: {phases_used.get('phase2', False)}")
            print(f"  Phase 3 ran: {phases_used.get('phase3', False)}")
            print(f"  Gemini used: {phases_used.get('gemini', False)}")
            print()
            
            # Show top recommendations
            recommendations = result.get('recommendations', [])
            for i, rec in enumerate(recommendations[:5]):
                print(f"{i+1}. {rec.get('title', 'No title')}")
                print(f"   Score: {rec.get('score', 0):.1f}")
                print(f"   Algorithm: {rec.get('algorithm_used', 'Unknown')}")
                print(f"   Reasoning: {rec.get('reasoning', 'No reasoning')}")
                print(f"   Domain: {rec.get('metadata', {}).get('domain_match', 'Unknown')}")
                print(f"   Tech Alignment: {rec.get('metadata', {}).get('tech_alignment', 0)}")
                print(f"   URL: {rec.get('url', 'No URL')}")
                print()
            
            # Check if scores are reasonable
            scores = [rec.get('score', 0) for rec in recommendations]
            if scores:
                avg_score = sum(scores) / len(scores)
                print(f"📊 Score Analysis:")
                print(f"   Average score: {avg_score:.2f}")
                print(f"   Min score: {min(scores):.2f}")
                print(f"   Max score: {max(scores):.2f}")
                print(f"   Scores range: {min(scores):.2f} - {max(scores):.2f}")
                
                if avg_score > 3.0:
                    print("✅ Scores look good (above 3.0 average)")
                else:
                    print("⚠️  Scores might be too low")
            
            # Performance assessment
            if response_time < 5.0:
                print(f"🚀 Performance: EXCELLENT ({response_time:.2f}s)")
            elif response_time < 10.0:
                print(f"⚡ Performance: GOOD ({response_time:.2f}s)")
            elif response_time < 20.0:
                print(f"🐌 Performance: SLOW ({response_time:.2f}s)")
            else:
                print(f"❌ Performance: TOO SLOW ({response_time:.2f}s)")
                
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_unified_recommendations() 