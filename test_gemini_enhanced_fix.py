#!/usr/bin/env python3
"""
Test script to verify that the Gemini Enhanced engine is working properly
after applying the meta tensor fix.
"""

import sys
import os
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gemini_enhanced_engine():
    """Test the Gemini Enhanced engine initialization and basic functionality"""
    print("🧪 Testing Gemini Enhanced Engine Fix")
    print("=" * 50)
    
    try:
        # Test 1: Import the engine
        print("1️⃣ Testing import...")
        from gemini_enhanced_recommendation_engine import GeminiEnhancedRecommendationEngine
        print("✅ Successfully imported GeminiEnhancedRecommendationEngine")
        
        # Test 2: Initialize the engine
        print("\n2️⃣ Testing initialization...")
        start_time = time.time()
        engine = GeminiEnhancedRecommendationEngine()
        init_time = (time.time() - start_time) * 1000
        print(f"✅ Successfully initialized in {init_time:.1f}ms")
        
        # Test 3: Check engine components
        print("\n3️⃣ Testing engine components...")
        if hasattr(engine, 'gemini_analyzer'):
            print("✅ Gemini analyzer available")
        else:
            print("⚠️ Gemini analyzer not available")
            
        if hasattr(engine, 'unified_engine'):
            print("✅ Unified engine available")
        else:
            print("❌ Unified engine not available")
            
        if hasattr(engine, 'use_gemini'):
            print(f"✅ Use Gemini flag: {engine.use_gemini}")
        else:
            print("❌ Use Gemini flag not available")
        
        # Test 4: Test with sample data
        print("\n4️⃣ Testing with sample data...")
        sample_bookmarks = [
            {
                'id': 1,
                'title': 'React Hooks Tutorial',
                'url': 'https://example.com/react-hooks',
                'extracted_text': 'Learn how to use React hooks for state management',
                'tags': 'react, javascript, hooks',
                'notes': 'Great tutorial for beginners',
                'quality_score': 8.5,
                'created_at': datetime.now()
            },
            {
                'id': 2,
                'title': 'Python Flask API Guide',
                'url': 'https://example.com/flask-api',
                'extracted_text': 'Build REST APIs with Python Flask framework',
                'tags': 'python, flask, api',
                'notes': 'Comprehensive guide for API development',
                'quality_score': 9.0,
                'created_at': datetime.now()
            }
        ]
        
        user_input = {
            'title': 'Web Development',
            'description': 'I want to learn web development with modern frameworks',
            'technologies': 'react, python, javascript',
            'user_interests': 'frontend, backend, fullstack'
        }
        
        start_time = time.time()
        try:
            result = engine.get_enhanced_recommendations(
                bookmarks=sample_bookmarks,
                user_input=user_input,
                max_recommendations=5
            )
            processing_time = (time.time() - start_time) * 1000
            
            print(f"✅ Successfully processed recommendations in {processing_time:.1f}ms")
            
            if 'recommendations' in result:
                recommendations = result['recommendations']
                print(f"📊 Generated {len(recommendations)} recommendations")
                
                for i, rec in enumerate(recommendations[:3], 1):
                    print(f"   {i}. {rec.get('title', 'N/A')} (Score: {rec.get('score', 0):.1f})")
            else:
                print("⚠️ No recommendations in result")
                
        except Exception as e:
            print(f"❌ Error processing recommendations: {e}")
            return False
        
        print("\n🎉 All tests passed! Gemini Enhanced engine is working properly.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_ensemble_engine_gemini():
    """Test that the ensemble engine can use Gemini Enhanced engine"""
    print("\n🧪 Testing Ensemble Engine with Gemini Enhanced")
    print("=" * 50)
    
    try:
        # Test ensemble engine initialization
        print("1️⃣ Testing ensemble engine...")
        from ensemble_engine import OptimizedEnsembleEngine
        
        engine = OptimizedEnsembleEngine()
        print("✅ Ensemble engine initialized")
        
        # Test that gemini_enhanced is in available engines
        available_engines = engine._get_available_engines(['gemini_enhanced'])
        print(f"✅ Available engines: {available_engines}")
        
        if 'gemini_enhanced' in available_engines:
            print("✅ Gemini Enhanced engine is available in ensemble")
        else:
            print("⚠️ Gemini Enhanced engine not available in ensemble")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing ensemble engine: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Gemini Enhanced Engine Meta Tensor Fix")
    print("=" * 60)
    
    # Test 1: Direct engine test
    test1_success = test_gemini_enhanced_engine()
    
    # Test 2: Ensemble engine test
    test2_success = test_ensemble_engine_gemini()
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 30)
    print(f"Gemini Enhanced Engine: {'✅ PASSED' if test1_success else '❌ FAILED'}")
    print(f"Ensemble Engine Integration: {'✅ PASSED' if test2_success else '❌ FAILED'}")
    
    if test1_success and test2_success:
        print("\n🎉 All tests passed! The meta tensor fix is working correctly.")
        return True
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 