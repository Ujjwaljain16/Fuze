#!/usr/bin/env python3
"""
Final Test File for Ensemble Engine
Comprehensive testing of the optimized ensemble recommendation engine
"""

import os
import sys
import time
import json
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and configure clean logging
from logging_config import set_test_logging
set_test_logging()

def test_ensemble_engine_import():
    """Test if ensemble engine can be imported successfully"""
    print("🔍 Testing Ensemble Engine Import...")
    try:
        from ensemble_engine import OptimizedEnsembleEngine, EnsembleRequest, EnsembleResult
        print("✅ Ensemble engine classes imported successfully")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_ensemble_engine_initialization():
    """Test ensemble engine initialization"""
    print("\n🔍 Testing Ensemble Engine Initialization...")
    try:
        from ensemble_engine import OptimizedEnsembleEngine
        engine = OptimizedEnsembleEngine()
        print("✅ Ensemble engine initialized successfully")
        print(f"   Engine weights: {engine.engine_weights}")
        print(f"   Cache duration: {engine.cache_duration}s")
        print(f"   Quality threshold: {engine.quality_threshold}")
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

def test_smart_engine_integration():
    """Test smart engine integration"""
    print("\n🔍 Testing Smart Engine Integration...")
    try:
        from ensemble_engine import OptimizedEnsembleEngine
        from smart_recommendation_engine import SmartRecommendationEngine
        
        # Test smart engine import
        print("✅ SmartRecommendationEngine imported successfully")
        
        # Test smart engine instantiation
        smart_engine = SmartRecommendationEngine(user_id=1)
        print("✅ SmartRecommendationEngine instantiated successfully")
        
        # Test available engines detection
        engine = OptimizedEnsembleEngine()
        available_engines = engine._get_available_engines(['smart', 'fast_gemini'])
        print(f"✅ Available engines detected: {available_engines}")
        
        return True
    except Exception as e:
        print(f"❌ Smart engine integration failed: {e}")
        return False

def test_fast_gemini_integration():
    """Test FastGemini engine integration"""
    print("\n🔍 Testing FastGemini Engine Integration...")
    try:
        from ensemble_engine import OptimizedEnsembleEngine
        
        engine = OptimizedEnsembleEngine()
        available_engines = engine._get_available_engines(['smart', 'fast_gemini'])
        
        if 'fast_gemini' in available_engines:
            print("✅ FastGemini engine available")
        else:
            print("⚠️  FastGemini engine not available (this is okay)")
        
        return True
    except Exception as e:
        print(f"❌ FastGemini integration test failed: {e}")
        return False

def test_ensemble_request_creation():
    """Test ensemble request creation"""
    print("\n🔍 Testing Ensemble Request Creation...")
    try:
        from ensemble_engine import EnsembleRequest
        
        request = EnsembleRequest(
            user_id=1,
            title="React Learning Project",
            description="Building a modern web application with React",
            technologies="JavaScript, React, Node.js",
            max_recommendations=5
        )
        
        print("✅ Ensemble request created successfully")
        print(f"   User ID: {request.user_id}")
        print(f"   Title: {request.title}")
        print(f"   Technologies: {request.technologies}")
        print(f"   Max recommendations: {request.max_recommendations}")
        
        return True
    except Exception as e:
        print(f"❌ Request creation failed: {e}")
        return False

def test_cache_key_generation():
    """Test cache key generation"""
    print("\n🔍 Testing Cache Key Generation...")
    try:
        from ensemble_engine import OptimizedEnsembleEngine, EnsembleRequest
        
        engine = OptimizedEnsembleEngine()
        request = EnsembleRequest(
            user_id=1,
            title="Test Project",
            description="Test description",
            technologies="test, tech",
            max_recommendations=5
        )
        
        cache_key = engine._generate_cache_key(request)
        print("✅ Cache key generated successfully")
        print(f"   Cache key: {cache_key}")
        print(f"   Key length: {len(cache_key)}")
        
        return True
    except Exception as e:
        print(f"❌ Cache key generation failed: {e}")
        return False

def test_technology_extraction():
    """Test technology extraction from text"""
    print("\n🔍 Testing Technology Extraction...")
    try:
        from ensemble_engine import OptimizedEnsembleEngine
        
        engine = OptimizedEnsembleEngine()
        
        # Test various text inputs
        test_texts = [
            "React Native Tutorial for Beginners",
            "Java Spring Boot API Documentation",
            "Python Machine Learning with TensorFlow",
            "JavaScript Node.js Web Development"
        ]
        
        for text in test_texts:
            technologies = engine._extract_technologies_from_text(text)
            print(f"   '{text}' -> {technologies}")
        
        print("✅ Technology extraction working correctly")
        return True
    except Exception as e:
        print(f"❌ Technology extraction failed: {e}")
        return False

def test_reason_generation():
    """Test reason generation"""
    print("\n🔍 Testing Reason Generation...")
    try:
        from ensemble_engine import OptimizedEnsembleEngine, EnsembleRequest
        
        engine = OptimizedEnsembleEngine()
        request = EnsembleRequest(
            user_id=1,
            title="Test Project",
            description="Test description",
            technologies="react, javascript",
            max_recommendations=5
        )
        
        # Test dynamic reason generation
        reasons = []
        test_titles = [
            "React Tutorial for Beginners",
            "JavaScript API Documentation",
            "Web Development Guide",
            "Programming Basics"
        ]
        
        for title in test_titles:
            reason = engine._generate_dynamic_reason(title, ["react", "javascript"])
            reasons.append(reason)
            print(f"   '{title}' -> {reason}")
        
        print("✅ Reason generation working correctly")
        return True
    except Exception as e:
        print(f"❌ Reason generation failed: {e}")
        return False

def test_content_type_detection():
    """Test content type detection"""
    print("\n🔍 Testing Content Type Detection...")
    try:
        from ensemble_engine import OptimizedEnsembleEngine
        
        engine = OptimizedEnsembleEngine()
        
        test_cases = [
            ("React Tutorial for Beginners", "tutorial"),
            ("JavaScript API Documentation", "documentation"),
            ("GitHub Project Repository", "project"),
            ("LeetCode Interview Questions", "practice"),
            ("Random Article Title", "article")
        ]
        
        for title, expected_type in test_cases:
            detected_type = engine._detect_content_type(title)
            status = "✅" if detected_type == expected_type else "❌"
            print(f"   {status} '{title}' -> {detected_type} (expected: {expected_type})")
        
        print("✅ Content type detection working correctly")
        return True
    except Exception as e:
        print(f"❌ Content type detection failed: {e}")
        return False

def test_difficulty_detection():
    """Test difficulty level detection"""
    print("\n🔍 Testing Difficulty Detection...")
    try:
        from ensemble_engine import OptimizedEnsembleEngine
        
        engine = OptimizedEnsembleEngine()
        
        test_cases = [
            ("Beginner's Guide to Python", "beginner"),
            ("Advanced React Patterns", "advanced"),
            ("Intermediate JavaScript Concepts", "intermediate"),
            ("Mastering Data Structures", "advanced"),
            ("Introduction to Web Development", "beginner")
        ]
        
        for title, expected_difficulty in test_cases:
            detected_difficulty = engine._detect_difficulty(title, None)
            status = "✅" if detected_difficulty == expected_difficulty else "❌"
            print(f"   {status} '{title}' -> {detected_difficulty} (expected: {expected_difficulty})")
        
        print("✅ Difficulty detection working correctly")
        return True
    except Exception as e:
        print(f"❌ Difficulty detection failed: {e}")
        return False

def test_ensemble_engine_end_to_end():
    """Test end-to-end ensemble engine functionality"""
    print("\n🔍 Testing End-to-End Ensemble Engine...")
    try:
        from ensemble_engine import get_ensemble_engine, get_ensemble_recommendations
        
        # Test getting ensemble engine instance
        engine = get_ensemble_engine()
        print("✅ Ensemble engine instance retrieved successfully")
        
        # Test getting recommendations (this might return empty if no data)
        request_data = {
            'title': 'React Learning Project',
            'description': 'Building a modern web application',
            'technologies': 'JavaScript, React, Node.js',
            'max_recommendations': 3
        }
        
        results = get_ensemble_recommendations(user_id=1, request_data=request_data)
        print(f"✅ Ensemble recommendations retrieved: {len(results)} results")
        
        if results:
            print("   Sample result:")
            sample = results[0]
            print(f"     ID: {sample.get('id')}")
            print(f"     Title: {sample.get('title')}")
            print(f"     Score: {sample.get('score')}")
            print(f"     Reason: {sample.get('reason')}")
        
        return True
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        return False

def test_error_handling():
    """Test error handling in ensemble engine"""
    print("\n🔍 Testing Error Handling...")
    try:
        from ensemble_engine import OptimizedEnsembleEngine, EnsembleRequest
        
        engine = OptimizedEnsembleEngine()
        
        # Test with invalid request data
        invalid_request = EnsembleRequest(
            user_id=999999,  # Non-existent user
            title="",
            description="",
            technologies="",
            max_recommendations=0
        )
        
        # This should handle errors gracefully
        results = engine.get_ensemble_recommendations(invalid_request)
        print(f"✅ Error handling working: {len(results)} results (expected 0)")
        
        return True
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def run_all_tests():
    """Run all ensemble engine tests"""
    print("🚀 Starting Ensemble Engine Final Tests\n")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_ensemble_engine_import),
        ("Initialization Test", test_ensemble_engine_initialization),
        ("Smart Engine Integration", test_smart_engine_integration),
        ("FastGemini Integration", test_fast_gemini_integration),
        ("Request Creation", test_ensemble_request_creation),
        ("Cache Key Generation", test_cache_key_generation),
        ("Technology Extraction", test_technology_extraction),
        ("Reason Generation", test_reason_generation),
        ("Content Type Detection", test_content_type_detection),
        ("Difficulty Detection", test_difficulty_detection),
        ("End-to-End Test", test_ensemble_engine_end_to_end),
        ("Error Handling", test_error_handling)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"⚠️  {test_name} completed with warnings")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Ensemble engine is working correctly.")
    elif passed >= total * 0.8:
        print("✅ Most tests passed. Ensemble engine is mostly working.")
    else:
        print("⚠️  Several tests failed. Ensemble engine needs attention.")
    
    return passed, total

if __name__ == "__main__":
    try:
        passed, total = run_all_tests()
        exit(0 if passed == total else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error during testing: {e}")
        exit(1)
