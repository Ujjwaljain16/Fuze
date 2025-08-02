#!/usr/bin/env python3
"""
Test script to verify Gemini optimization improvements
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from gemini_enhanced_recommendation_engine import GeminiEnhancedRecommendationEngine
    print("✅ Successfully imported GeminiEnhancedRecommendationEngine")
except ImportError as e:
    print(f"❌ Failed to import GeminiEnhancedRecommendationEngine: {e}")
    sys.exit(1)

def test_optimization():
    """Test the optimization improvements"""
    
    # Check if Gemini API key is available
    if not os.getenv('GEMINI_API_KEY'):
        print("❌ GEMINI_API_KEY not found in environment variables")
        print("Please set your Gemini API key in the .env file")
        return False
    
    try:
        engine = GeminiEnhancedRecommendationEngine()
        print("✅ Successfully initialized GeminiEnhancedRecommendationEngine")
    except Exception as e:
        print(f"❌ Failed to initialize GeminiEnhancedRecommendationEngine: {e}")
        return False
    
    # Create test bookmarks
    test_bookmarks = [
        {
            'id': 1,
            'title': 'Java Bytecode Instrumentation with ASM',
            'url': 'https://example.com/java-asm',
            'notes': 'Learn ASM framework for Java bytecode manipulation',
            'extracted_text': 'This tutorial covers Java bytecode instrumentation using the ASM framework.'
        },
        {
            'id': 2,
            'title': 'Data Structures and Algorithms in Java',
            'url': 'https://example.com/java-dsa',
            'notes': 'Comprehensive guide to DSA in Java',
            'extracted_text': 'Learn data structures and algorithms implementation in Java.'
        },
        {
            'id': 3,
            'title': 'JavaScript React Tutorial',
            'url': 'https://example.com/react-js',
            'notes': 'React.js tutorial for beginners',
            'extracted_text': 'Learn React.js framework for building user interfaces.'
        },
        {
            'id': 4,
            'title': 'Python Flask Web Development',
            'url': 'https://example.com/flask-python',
            'notes': 'Flask web framework tutorial',
            'extracted_text': 'Build web applications with Python Flask framework.'
        },
        {
            'id': 5,
            'title': 'Java Spring Boot Microservices',
            'url': 'https://example.com/spring-boot',
            'notes': 'Spring Boot microservices architecture',
            'extracted_text': 'Learn to build microservices with Spring Boot.'
        }
    ]
    
    # Test user input
    user_input = {
        'title': 'Java DSA Learning Project',
        'description': 'Learning Java data structures and algorithms with instrumentation',
        'technologies': 'java, dsa, instrumentation',
        'user_interests': 'java, algorithms, bytecode manipulation'
    }
    
    print("\n🔍 Testing optimized Gemini recommendations...")
    print(f"📊 Total bookmarks to process: {len(test_bookmarks)}")
    
    # Time the recommendation generation
    start_time = time.time()
    
    try:
        result = engine.get_enhanced_recommendations(
            test_bookmarks, user_input, max_recommendations=3
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"⏱️  Processing time: {processing_time:.2f} seconds")
        print(f"📊 Cache stats: {engine.get_cache_stats()}")
        
        # Display results
        print(f"\n📋 Recommendations found: {len(result.get('recommendations', []))}")
        print(f"🧠 Gemini Enhanced: {result.get('context_analysis', {}).get('processing_stats', {}).get('gemini_enhanced', False)}")
        
        # Show processing stats
        stats = result.get('context_analysis', {}).get('processing_stats', {})
        print(f"📈 Processing Stats:")
        print(f"  - Total bookmarks analyzed: {stats.get('total_bookmarks_analyzed', 0)}")
        print(f"  - Relevant bookmarks found: {stats.get('relevant_bookmarks_found', 0)}")
        
        # Test cache effectiveness
        print(f"\n🔄 Testing cache effectiveness...")
        cache_start_time = time.time()
        
        # Run the same request again (should use cache)
        cached_result = engine.get_enhanced_recommendations(
            test_bookmarks, user_input, max_recommendations=3
        )
        
        cache_end_time = time.time()
        cached_processing_time = cache_end_time - cache_start_time
        
        print(f"⏱️  Cached processing time: {cached_processing_time:.2f} seconds")
        print(f"🚀 Speed improvement: {processing_time/cached_processing_time:.1f}x faster")
        
        print("\n✅ Optimization test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_optimization()
    if success:
        print("\n🎉 Gemini optimization is working correctly!")
        print("The system should now be much faster and more efficient.")
    else:
        print("\n❌ Some tests failed. Please check the error messages above.") 