#!/usr/bin/env python3
"""
Test Gemini Integration Directly
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_gemini_direct():
    """Test Gemini integration directly"""
    
    print("🔍 Testing Gemini Integration Directly")
    print("=" * 60)
    
    try:
        # Test if gemini_integration_layer can be imported
        print("📦 Testing import...")
        from gemini_integration_layer import get_gemini_enhanced_recommendations
        print("✅ Gemini integration layer imported successfully")
        
        # Test if Gemini API key is available
        print("\n🔑 Testing API key...")
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if gemini_api_key:
            print(f"✅ Gemini API key found: {gemini_api_key[:10]}...")
        else:
            print("❌ No Gemini API key found in environment")
            print("   Set GEMINI_API_KEY environment variable")
            return
        
        # Test basic Gemini functionality
        print("\n🤖 Testing basic Gemini functionality...")
        try:
            from gemini_integration_layer import GeminiIntegrationLayer
            
            layer = GeminiIntegrationLayer()
            print("✅ GeminiIntegrationLayer initialized")
            
            # Test if the model can be loaded
            if hasattr(layer, 'model') and layer.model:
                print("✅ Gemini model loaded successfully")
            else:
                print("❌ Gemini model not loaded")
                
        except Exception as e:
            print(f"❌ Error initializing Gemini: {e}")
            return
            
        print("\n✅ Gemini integration appears to be working!")
        print("   The issue might be in the status endpoint or authentication")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gemini_direct() 