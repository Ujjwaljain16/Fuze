#!/usr/bin/env python3
"""
Test Context Analysis
Verify that context analysis is working in both engines
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def test_context_analysis():
    """Test that context analysis is working"""
    print("🎯 Testing Context Analysis")
    print("=" * 40)
    
    # Login to get token
    login_data = {
        "email": "jainujjwal1609@gmail.com",
        "password": "Jainsahab@16"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json().get('access_token')
            headers = {'Authorization': f'Bearer {token}'}
            print("✅ Got auth token")
        else:
            print(f"❌ Login failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Login error: {e}")
        return
    
    # Test ultra-fast recommendations (should show context analysis)
    print("\n🔍 Testing Ultra-Fast Context Analysis:")
    print("-" * 40)
    
    try:
        response = requests.get(f"{BASE_URL}/api/recommendations/optimized", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            context_analysis = data.get('context_analysis')
            
            if context_analysis:
                print("✅ Context analysis found!")
                processing_stats = context_analysis.get('processing_stats', {})
                print(f"   Bookmarks Analyzed: {processing_stats.get('total_bookmarks_analyzed', 0)}")
                print(f"   Relevant Found: {processing_stats.get('relevant_bookmarks_found', 0)}")
                print(f"   Gemini Enhanced: {processing_stats.get('gemini_enhanced', False)}")
                print(f"   Engine: {processing_stats.get('engine', 'unknown')}")
            else:
                print("❌ No context analysis found")
        else:
            print(f"❌ Request failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Request error: {e}")
    
    # Test Gemini recommendations (should show context analysis)
    print("\n🔍 Testing Gemini Context Analysis:")
    print("-" * 40)
    
    try:
        response = requests.post(f"{BASE_URL}/api/recommendations/fast-gemini", headers=headers, json={})
        
        if response.status_code == 200:
            data = response.json()
            context_analysis = data.get('context_analysis')
            
            if context_analysis:
                print("✅ Context analysis found!")
                processing_stats = context_analysis.get('processing_stats', {})
                print(f"   Bookmarks Analyzed: {processing_stats.get('total_bookmarks_analyzed', 0)}")
                print(f"   Relevant Found: {processing_stats.get('relevant_bookmarks_found', 0)}")
                print(f"   Gemini Enhanced: {processing_stats.get('gemini_enhanced', False)}")
                print(f"   Engine: {processing_stats.get('engine', 'unknown')}")
            else:
                print("❌ No context analysis found")
        else:
            print(f"❌ Request failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Request error: {e}")
    
    print("\n" + "=" * 40)
    print("🎯 Context Analysis Test Complete!")
    print("=" * 40)

if __name__ == "__main__":
    test_context_analysis() 