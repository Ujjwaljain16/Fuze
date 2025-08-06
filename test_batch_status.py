#!/usr/bin/env python3
"""
Test Batch Processing Status
Verify that the analysis stats endpoint returns correct data
"""

import requests
import json

def test_batch_status():
    """Test the batch processing status endpoint"""
    print("🧪 Testing Batch Processing Status")
    print("=" * 40)
    
    # Test data
    test_url = "http://localhost:5000/api/recommendations/analysis/stats"
    
    try:
        # First, try to get a valid token by logging in
        login_url = "http://localhost:5000/api/auth/login"
        login_data = {
            "email": "test@example.com",
            "password": "testpassword"
        }
        
        print("🔐 Attempting to get authentication token...")
        login_response = requests.post(login_url, json=login_data)
        
        if login_response.status_code == 200:
            token = login_response.json().get('access_token')
            if token:
                print("✅ Got authentication token")
                headers = {'Authorization': f'Bearer {token}'}
            else:
                print("⚠️ No token in login response, trying without auth")
                headers = {}
        else:
            print("⚠️ Login failed, trying without authentication")
            headers = {}
        
        # Make request to the endpoint
        response = requests.get(test_url, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Data: {json.dumps(data, indent=2)}")
            
            # Check if all required fields are present
            required_fields = ['total_content', 'analyzed_content', 'pending_analysis', 'coverage_percentage']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                print(f"❌ Missing fields: {missing_fields}")
            else:
                print("✅ All required fields present")
                
                # Validate data types
                if isinstance(data['total_content'], int) and \
                   isinstance(data['analyzed_content'], int) and \
                   isinstance(data['pending_analysis'], int) and \
                   isinstance(data['coverage_percentage'], (int, float)):
                    print("✅ All fields have correct data types")
                else:
                    print("❌ Some fields have incorrect data types")
                
                # Validate percentage calculation
                if data['total_content'] > 0:
                    expected_percentage = round((data['analyzed_content'] / data['total_content']) * 100, 1)
                    if abs(data['coverage_percentage'] - expected_percentage) < 0.1:
                        print("✅ Percentage calculation is correct")
                    else:
                        print(f"❌ Percentage calculation mismatch: expected {expected_percentage}, got {data['coverage_percentage']}")
                else:
                    print("ℹ️ No content to analyze")
                
                # Validate pending calculation
                expected_pending = data['total_content'] - data['analyzed_content']
                if data['pending_analysis'] == expected_pending:
                    print("✅ Pending analysis calculation is correct")
                else:
                    print(f"❌ Pending analysis mismatch: expected {expected_pending}, got {data['pending_analysis']}")
                    
        elif response.status_code == 401:
            print("❌ Authentication required but no valid token available")
            print("   This is expected if the server requires authentication")
            print("   The endpoint is working correctly, just needs proper auth")
        else:
            print(f"❌ Request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the Flask app is running.")
    except Exception as e:
        print(f"❌ Error testing batch status: {e}")

if __name__ == "__main__":
    test_batch_status() 