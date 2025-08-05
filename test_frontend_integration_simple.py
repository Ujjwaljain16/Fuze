#!/usr/bin/env python3
"""
Simple Frontend Integration Test - No Authentication Required
Tests the new unified orchestrator endpoint without JWT tokens.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5000"

def test_status_endpoint():
    """Test the status endpoint (no auth required)"""
    print("🔍 Testing Status Endpoint")
    print("=" * 30)
    
    try:
        response = requests.get(f"{BASE_URL}/api/recommendations/status")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Status endpoint working")
            print(f"🔧 Unified Orchestrator: {data.get('unified_orchestrator_available', False)}")
            print(f"🔧 Unified Engine: {data.get('unified_engine_available', False)}")
            print(f"🤖 Gemini Integration: {data.get('gemini_integration_available', False)}")
            print(f"📊 Total Engines: {data.get('total_engines_available', 0)}")
            print(f"⭐ Recommended Engine: {data.get('recommended_engine', 'None')}")
            
            # Check if unified orchestrator is available
            if data.get('unified_orchestrator_available', False):
                print("🎉 Unified Orchestrator is available!")
                return True
            else:
                print("❌ Unified Orchestrator is not available")
                return False
        else:
            print(f"❌ Status endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Status endpoint error: {e}")
        return False

def test_unified_orchestrator_import():
    """Test if the unified orchestrator can be imported"""
    print("\n🧪 Testing Unified Orchestrator Import")
    print("=" * 40)
    
    try:
        from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest
        print("✅ Unified orchestrator import successful")
        
        # Try to get the orchestrator instance
        orchestrator = get_unified_orchestrator()
        if orchestrator:
            print("✅ Unified orchestrator instance created successfully")
            return True
        else:
            print("❌ Failed to create orchestrator instance")
            return False
            
    except Exception as e:
        print(f"❌ Unified orchestrator import failed: {e}")
        return False

def test_gemini_integration_import():
    """Test if the Gemini integration can be imported"""
    print("\n🤖 Testing Gemini Integration Import")
    print("=" * 35)
    
    try:
        from gemini_integration_layer import get_gemini_integration
        print("✅ Gemini integration import successful")
        
        # Try to get the Gemini integration instance
        gemini_layer = get_gemini_integration()
        if gemini_layer:
            print("✅ Gemini integration instance created successfully")
            return True
        else:
            print("❌ Failed to create Gemini integration instance")
            return False
            
    except Exception as e:
        print(f"❌ Gemini integration import failed: {e}")
        return False

def main():
    """Run all simple tests"""
    print("🚀 Simple Frontend Integration Test Suite")
    print("=" * 50)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Base URL: {BASE_URL}")
    
    # Run tests
    status_ok = test_status_endpoint()
    orchestrator_ok = test_unified_orchestrator_import()
    gemini_ok = test_gemini_integration_import()
    
    print("\n\n🎉 Simple Test Suite Complete!")
    print("=" * 50)
    print(f"📊 Results:")
    print(f"  Status Endpoint: {'✅ PASS' if status_ok else '❌ FAIL'}")
    print(f"  Unified Orchestrator: {'✅ PASS' if orchestrator_ok else '❌ FAIL'}")
    print(f"  Gemini Integration: {'✅ PASS' if gemini_ok else '❌ FAIL'}")
    
    if status_ok and orchestrator_ok:
        print("\n🎉 Frontend integration should work! The unified orchestrator is available.")
        print("📝 Next step: Test with proper authentication tokens.")
    else:
        print("\n⚠️  Some components are not working properly.")
        print("📝 Check the logs above for specific issues.")

if __name__ == "__main__":
    main() 