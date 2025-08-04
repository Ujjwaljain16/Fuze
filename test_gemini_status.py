#!/usr/bin/env python3
"""
Test script to check Gemini status and enhanced recommendations
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:5000"

def test_gemini_status():
    """Test Gemini status endpoint"""
    print("Testing Gemini Status...")
    
    try:
        # First, we need to get a token (simulate login)
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            return
        
        token = login_response.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}'}
        
        # Test Gemini status
        status_response = requests.get(f"{BASE_URL}/api/recommendations/gemini-status", headers=headers)
        print(f"Gemini Status Response: {status_response.status_code}")
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"Gemini Available: {status_data.get('gemini_available')}")
            print(f"Status: {status_data.get('status')}")
            print(f"Details: {status_data.get('details')}")
            
            if status_data.get('gemini_available'):
                print("✅ Gemini is available - testing enhanced recommendations...")
                test_gemini_enhanced(headers)
            else:
                print("❌ Gemini is not available")
                print(f"Error: {status_data.get('details', {}).get('error_message')}")
        else:
            print(f"❌ Failed to get Gemini status: {status_response.text}")
            
    except Exception as e:
        print(f"❌ Error testing Gemini status: {e}")

def test_gemini_enhanced(headers):
    """Test Gemini enhanced recommendations"""
    print("\nTesting Gemini Enhanced Recommendations...")
    
    try:
        data = {
            "title": "Test Project",
            "description": "Testing Gemini enhanced recommendations",
            "technologies": "python, flask",
            "user_interests": "web development, python",
            "max_recommendations": 5
        }
        
        response = requests.post(f"{BASE_URL}/api/recommendations/gemini-enhanced", headers=headers, json=data)
        print(f"Enhanced Recommendations Response: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            recommendations = result.get('recommendations', [])
            print(f"✅ Found {len(recommendations)} Gemini enhanced recommendations")
            
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"\n{i}. {rec.get('title', 'No title')}")
                print(f"   URL: {rec.get('url', 'No URL')}")
                print(f"   Score: {rec.get('similarity_score', 'No score')}")
        else:
            print(f"❌ Failed to get enhanced recommendations: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing enhanced recommendations: {e}")

if __name__ == "__main__":
    test_gemini_status() 