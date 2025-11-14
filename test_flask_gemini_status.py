#!/usr/bin/env python3
"""
Test Fast Gemini Engine Status in Flask Context
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

print("🔍 Testing Fast Gemini Engine Status in Flask Context")
print("=" * 60)

# Check environment variables
print(f"GEMINI_API_KEY set: {'Yes' if os.getenv('GEMINI_API_KEY') else 'No'}")

# Test importing the recommendations blueprint
print("\n📦 Testing recommendations blueprint import...")
try:
    from blueprints.recommendations import FAST_GEMINI_AVAILABLE, init_engines
    print(f"FAST_GEMINI_AVAILABLE from blueprint: {FAST_GEMINI_AVAILABLE}")
    
    # Call init_engines to see what happens
    print("\n🔧 Calling init_engines()...")
    init_engines()
    
    # Check the status again
    from blueprints.recommendations import FAST_GEMINI_AVAILABLE
    print(f"FAST_GEMINI_AVAILABLE after init_engines: {FAST_GEMINI_AVAILABLE}")
    
except Exception as e:
    print(f"❌ Error importing recommendations blueprint: {e}")

# Test the status endpoint logic
print("\n🌐 Testing status endpoint logic...")
try:
    from blueprints.recommendations import get_engine_status
    from flask import Flask
    
    # Create a minimal Flask app
    app = Flask(__name__)
    
    with app.app_context():
        # Import the status variables
        from blueprints.recommendations import (
            UNIFIED_ORCHESTRATOR_AVAILABLE, UNIFIED_ENGINE_AVAILABLE, 
            SMART_ENGINE_AVAILABLE, ENHANCED_ENGINE_AVAILABLE, 
            PHASE3_ENGINE_AVAILABLE, FAST_GEMINI_AVAILABLE, 
            ENHANCED_MODULES_AVAILABLE
        )
        
        print(f"UNIFIED_ORCHESTRATOR_AVAILABLE: {UNIFIED_ORCHESTRATOR_AVAILABLE}")
        print(f"UNIFIED_ENGINE_AVAILABLE: {UNIFIED_ENGINE_AVAILABLE}")
        print(f"SMART_ENGINE_AVAILABLE: {SMART_ENGINE_AVAILABLE}")
        print(f"ENHANCED_ENGINE_AVAILABLE: {ENHANCED_ENGINE_AVAILABLE}")
        print(f"PHASE3_ENGINE_AVAILABLE: {PHASE3_ENGINE_AVAILABLE}")
        print(f"FAST_GEMINI_AVAILABLE: {FAST_GEMINI_AVAILABLE}")
        print(f"ENHANCED_MODULES_AVAILABLE: {ENHANCED_MODULES_AVAILABLE}")
        
        # Calculate total engines
        total_engines = sum([
            UNIFIED_ORCHESTRATOR_AVAILABLE,
            UNIFIED_ENGINE_AVAILABLE,
            SMART_ENGINE_AVAILABLE,
            ENHANCED_ENGINE_AVAILABLE,
            PHASE3_ENGINE_AVAILABLE,
            FAST_GEMINI_AVAILABLE
        ])
        print(f"Total engines available: {total_engines}")
        
except Exception as e:
    print(f"❌ Error testing status endpoint: {e}")

print("\n" + "=" * 60)
print("�� Test completed") 