#!/usr/bin/env python3
"""
Debug script to see what Gemini is actually returning
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_gemini_response():
    """Debug what Gemini is actually returning"""
    print("🔍 Debugging Gemini Response")
    print("=" * 50)
    
    try:
        from gemini_utils import GeminiAnalyzer
        analyzer = GeminiAnalyzer()
        
        # Test with Java DSA project
        print("\n📋 Testing: Java DSA Project")
        print("-" * 30)
        
        response = analyzer.analyze_user_context(
            title="DSA visualiser",
            description="a visualizer for data structure and algorithms that make it easier to understand the complexity easier just copy paste yr code and get a dynamic visualization of that with a detailed dry run for now available in java language only java instrumentation byte buddy ast jvm",
            technologies="java, jvm, byte buddy, ast",
            user_interests="data structures, algorithms, visualization"
        )
        
        print("✅ Raw Gemini Response:")
        print(f"Type: {type(response)}")
        print(f"Keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        
        if isinstance(response, dict):
            print("\n📊 Response Details:")
            for key, value in response.items():
                print(f"  {key}: {value}")
                if key == 'technologies' and isinstance(value, list):
                    print(f"    Technologies type: {type(value)}")
                    print(f"    Technologies length: {len(value)}")
                    for i, tech in enumerate(value):
                        print(f"    [{i}] {tech} (type: {type(tech)})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_gemini_response() 