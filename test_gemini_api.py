#!/usr/bin/env python3
"""
Simple script to test Gemini API directly
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini_api():
    """Test Gemini API with different models"""
    
    # Get API key from environment
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment variables")
        return False
    
    print(f"🔑 API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    # Models to test
    models = [
        'gemini-2.0-flash',
        'gemini-1.5-pro',
        'gemini-pro'
    ]
    
    # Test payload
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Hello! Please respond with 'API test successful' if you can see this message."
                    }
                ]
            }
        ]
    }
    
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': api_key
    }
    
    for model in models:
        print(f"\n🧪 Testing model: {model}")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and data['candidates']:
                    text = data['candidates'][0]['content']['parts'][0]['text']
                    print(f"   ✅ Success! Response: {text[:100]}...")
                    print(f"   🎉 Model {model} is working!")
                    return True
                else:
                    print(f"   ❌ Unexpected response format: {data}")
            else:
                print(f"   ❌ Error: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON decode error: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
    
    print("\n❌ All models failed")
    return False

def test_python_library():
    """Test the Python google-generativeai library"""
    
    print("\n🐍 Testing Python google-generativeai library...")
    
    try:
        import google.generativeai as genai
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ GEMINI_API_KEY not found")
            return False
        
        genai.configure(api_key=api_key)
        
        # Test with different models
        models_to_try = ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-pro']
        
        for model_name in models_to_try:
            try:
                print(f"   Testing model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Hello! Say 'Python library test successful' if you can see this.")
                
                if response.text:
                    print(f"   ✅ {model_name} working! Response: {response.text[:100]}...")
                    return True
                    
            except Exception as e:
                print(f"   ❌ {model_name} failed: {e}")
        
        print("   ❌ All Python library models failed")
        return False
        
    except ImportError:
        print("❌ google-generativeai library not installed")
        return False

if __name__ == "__main__":
    print("="*60)
    print(" GEMINI API TEST")
    print("="*60)
    
    # Test direct API
    print("\n1. Testing direct API calls...")
    api_success = test_gemini_api()
    
    # Test Python library
    print("\n2. Testing Python library...")
    library_success = test_python_library()
    
    print("\n" + "="*60)
    print(" TEST RESULTS")
    print("="*60)
    
    if api_success or library_success:
        print("✅ Gemini API is working!")
        if api_success:
            print("   - Direct API calls: ✅ Working")
        if library_success:
            print("   - Python library: ✅ Working")
        print("\n🎉 Your Fuze application should now work with Gemini AI!")
    else:
        print("❌ Gemini API tests failed")
        print("   Please check your API key and internet connection")
        print("   Get a new API key from: https://makersuite.google.com/app/apikey") 