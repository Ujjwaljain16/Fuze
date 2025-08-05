#!/usr/bin/env python3
"""
Test Ensemble Engine Syntax
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ensemble_syntax():
    """Test if ensemble engine can be imported and initialized"""
    print("🔍 Testing Ensemble Engine Syntax")
    print("=" * 50)
    
    try:
        # Test import
        print("📦 Testing import...")
        from ensemble_engine import get_ensemble_engine, EnsembleRequest, get_ensemble_recommendations
        print("✅ Ensemble engine imported successfully")
        
        # Test initialization
        print("🔧 Testing initialization...")
        engine = get_ensemble_engine()
        print("✅ Ensemble engine initialized successfully")
        
        # Test request creation
        print("📝 Testing request creation...")
        request = EnsembleRequest(
            user_id=1,
            title="Test Request",
            description="Test Description",
            technologies="Python, Flask",
            max_recommendations=5
        )
        print("✅ Request created successfully")
        
        # Test function call
        print("🚀 Testing function call...")
        test_data = {
            'title': 'React Development',
            'description': 'Building web apps',
            'technologies': 'React, JavaScript',
            'max_recommendations': 3,
            'engines': ['unified']  # Start with just unified to avoid complex dependencies
        }
        
        results = get_ensemble_recommendations(1, test_data)
        print(f"✅ Function call successful! Got {len(results)} results")
        
        print("\n✅ All syntax tests passed!")
        print("   The ensemble engine should now work properly")
        
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        print(f"   Line: {e.lineno}, Column: {e.offset}")
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ensemble_syntax() 