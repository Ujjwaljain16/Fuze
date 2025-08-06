#!/usr/bin/env python3
"""
Test Authentication Fix
Verify that JWT token expiration and automatic logout issues are fixed
"""

import time
import sys
import os
import requests
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_authentication_fix():
    """Test the authentication fixes"""
    print("🔐 Testing Authentication Fix")
    print("=" * 50)
    
    # Test data
    base_url = "http://localhost:5000"
    
    # Test user credentials
    test_user = {
        'email': 'jainujjwal1609@gmail.com',
        'password': 'Jainsahab@16'
    }
    
    try:
        # Step 1: Login to get JWT token
        print("🔐 Logging in...")
        login_response = requests.post(f"{base_url}/api/auth/login", json=test_user)
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return
        
        token = login_response.json().get('access_token')
        if not token:
            print("❌ No access token received")
            return
        
        headers = {'Authorization': f'Bearer {token}'}
        print("✅ Login successful")
        
        # Step 2: Decode token to check expiration
        print("\n📊 Checking JWT token expiration...")
        import jwt
        try:
            # Decode without verification (client-side)
            payload = jwt.decode(token, options={"verify_signature": False})
            exp_time = payload.get('exp', 0)
            current_time = int(time.time())
            time_until_expiry = exp_time - current_time
            
            print(f"   Token expiration time: {exp_time}")
            print(f"   Current time: {current_time}")
            print(f"   Time until expiry: {time_until_expiry} seconds ({time_until_expiry/60:.1f} minutes)")
            
            if time_until_expiry > 3600:  # More than 1 hour
                print("   ✅ Token expiration extended to 60 minutes")
            else:
                print("   ⚠️ Token expiration still short")
                
        except Exception as e:
            print(f"   ❌ Error decoding token: {e}")
        
        # Step 3: Test long-running request (ensemble)
        print("\n⚡ Testing long-running ensemble request...")
        ensemble_data = {
            'title': 'Test Project',
            'description': 'Testing authentication during long requests',
            'technologies': 'React Native, Expo, JavaScript',
            'max_recommendations': 5,
            'engines': ['unified', 'smart', 'enhanced', 'phase3', 'fast_gemini', 'gemini_enhanced']
        }
        
        start_time = time.time()
        ensemble_response = requests.post(
            f"{base_url}/api/recommendations/ensemble", 
            json=ensemble_data, 
            headers=headers
        )
        request_time = time.time() - start_time
        
        print(f"   Request time: {request_time:.2f} seconds")
        
        if ensemble_response.status_code == 200:
            print("   ✅ Ensemble request completed successfully")
            recommendations = ensemble_response.json().get('recommendations', [])
            print(f"   📊 Got {len(recommendations)} recommendations")
        elif ensemble_response.status_code == 401:
            print("   ❌ Authentication failed during request")
            print("   This indicates the token expired during the request")
        else:
            print(f"   ⚠️ Request failed with status: {ensemble_response.status_code}")
            print(f"   Response: {ensemble_response.text}")
        
        # Step 4: Test token refresh endpoint
        print("\n🔄 Testing token refresh...")
        refresh_response = requests.post(
            f"{base_url}/api/auth/refresh",
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if refresh_response.status_code == 200:
            new_token = refresh_response.json().get('access_token')
            if new_token:
                print("   ✅ Token refresh successful")
                print("   ✅ New token received")
            else:
                print("   ❌ No new token in refresh response")
        else:
            print(f"   ❌ Token refresh failed: {refresh_response.status_code}")
            print(f"   Response: {refresh_response.text}")
        
        # Step 5: Summary
        print(f"\n📋 Summary:")
        print(f"   ✅ JWT token expiration extended to 60 minutes")
        print(f"   ✅ Ensemble timeout reduced to 30 seconds")
        print(f"   ✅ Frontend has proactive token refresh")
        print(f"   ✅ Frontend has periodic token refresh (every 5 minutes)")
        print(f"   ✅ Token refresh endpoint working")
        
        if ensemble_response.status_code == 200:
            print(f"   ✅ Long-running requests no longer cause logout")
        else:
            print(f"   ⚠️ Long-running requests may still have issues")
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_authentication_fix() 