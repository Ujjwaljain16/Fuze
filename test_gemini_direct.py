#!/usr/bin/env python3
"""
Test Gemini API directly
"""

import os
import sys
from pathlib import Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path(".env")
    if env_file.exists():
        print("📁 Loading environment variables from .env file...")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Environment variables loaded successfully!")
    else:
        print("⚠️  .env file not found")

def test_gemini_direct():
    """Test Gemini API directly"""
    print("🧠 Testing Gemini API Directly")
    print("=" * 40)
    
    # Load environment variables first
    load_env_file()
    
    try:
        # Check if API key is set
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print("❌ GEMINI_API_KEY environment variable not set")
            return
        
        print(f"✅ GEMINI_API_KEY found: {api_key[:10]}...")
        
        # Import and test Gemini
        from gemini_utils import GeminiAnalyzer
        
        print("🔧 Initializing Gemini Analyzer...")
        gemini_analyzer = GeminiAnalyzer()
        print("✅ Gemini Analyzer initialized successfully!")
        
        # Test simple analysis
        test_prompt = """
        Analyze this content for learning value:
        Title: "JavaScript Tutorial for Beginners"
        Content: "Learn JavaScript fundamentals, DOM manipulation, and basic programming concepts."
        
        Provide a JSON response with:
        - relevance_score (0-10)
        - learning_value (0-10) 
        - key_insights (brief explanation)
        """
        
        print("🔍 Testing Gemini analysis...")
        response = gemini_analyzer.analyze_batch_content(test_prompt)
        
        if response and 'analysis' in response:
            print("✅ Gemini analysis successful!")
            print(f"Response: {response}")
        else:
            print("❌ Gemini analysis failed or returned unexpected format")
            print(f"Response: {response}")
            
    except Exception as e:
        print(f"❌ Gemini test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gemini_direct() 