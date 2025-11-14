#!/usr/bin/env python3
"""
Test Fast Gemini Engine Status
Diagnose why FastGeminiEngine is showing as not available
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

print("🔍 Testing Fast Gemini Engine Status")
print("=" * 50)

# Check environment variables
print(f"GEMINI_API_KEY set: {'Yes' if os.getenv('GEMINI_API_KEY') else 'No'}")
if os.getenv('GEMINI_API_KEY'):
    print(f"GEMINI_API_KEY length: {len(os.getenv('GEMINI_API_KEY'))}")
    print(f"GEMINI_API_KEY starts with: {os.getenv('GEMINI_API_KEY')[:10]}...")

# Test importing FastGeminiEngine
print("\n📦 Testing FastGeminiEngine import...")
try:
    from fast_gemini_engine import FastGeminiEngine
    print("✅ FastGeminiEngine import successful")
    
    # Test instantiation
    print("\n🔧 Testing FastGeminiEngine instantiation...")
    try:
        engine = FastGeminiEngine()
        print("✅ FastGeminiEngine instantiation successful")
        
        # Check if Gemini components are available
        print(f"Gemini available: {engine.gemini_available}")
        print(f"Gemini analyzer: {'Available' if engine.gemini_analyzer else 'Not available'}")
        print(f"Rate limiter: {'Available' if engine.rate_limiter else 'Not available'}")
        
    except Exception as e:
        print(f"❌ FastGeminiEngine instantiation failed: {e}")
        
except ImportError as e:
    print(f"❌ FastGeminiEngine import failed: {e}")

# Test importing individual components
print("\n🔧 Testing individual component imports...")

try:
    from gemini_utils import GeminiAnalyzer
    print("✅ GeminiAnalyzer import successful")
    
    try:
        analyzer = GeminiAnalyzer()
        print("✅ GeminiAnalyzer instantiation successful")
    except Exception as e:
        print(f"❌ GeminiAnalyzer instantiation failed: {e}")
        
except ImportError as e:
    print(f"❌ GeminiAnalyzer import failed: {e}")

try:
    from rate_limit_handler import GeminiRateLimiter
    print("✅ GeminiRateLimiter import successful")
    
    try:
        rate_limiter = GeminiRateLimiter()
        print("✅ GeminiRateLimiter instantiation successful")
    except Exception as e:
        print(f"❌ GeminiRateLimiter instantiation failed: {e}")
        
except ImportError as e:
    print(f"❌ GeminiRateLimiter import failed: {e}")

print("\n" + "=" * 50)
print("�� Test completed") 