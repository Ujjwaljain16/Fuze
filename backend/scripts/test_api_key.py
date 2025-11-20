#!/usr/bin/env python3
"""
Test Gemini API Key
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def test_api_key():
    """Test the API key"""
    try:
        from utils.gemini_utils import GeminiAnalyzer

        # Test with the provided API key
        api_key = 'AIzaSyAYElAOJ-cnuwL4CphagM5SSXWkNu4d88w'
        print('🔍 Testing API key:', api_key[:20] + '...')
        print('Length:', len(api_key))

        analyzer = GeminiAnalyzer(api_key=api_key)
        print('✅ API key format accepted')

        # Try a simple test
        test_result = analyzer._make_gemini_request('Say hello')
        if test_result:
            print('✅ API key works!')
            print('Response:', test_result[:100])
        else:
            print('❌ API key test failed - empty response')

    except Exception as e:
        print('❌ API key test failed:', str(e))
        if 'expired' in str(e).lower() or 'invalid' in str(e).lower():
            print('')
            print('💡 This API key is expired or invalid')
            print('🔑 Please get a new one from: https://aistudio.google.com/app/apikey')
            print('')
            print('Steps:')
            print('1. Go to https://aistudio.google.com/app/apikey')
            print('2. Sign in with your Google account')
            print('3. Click "Create API key"')
            print('4. Copy the new API key')
            print('5. Run: python scripts/update_api_key.py')
            print('6. Paste the new API key when prompted')

if __name__ == '__main__':
    test_api_key()

