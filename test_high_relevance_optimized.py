#!/usr/bin/env python3
"""
Optimized test to verify that the High Relevance Engine is working properly
in the quality ensemble endpoint with faster timeouts.
"""

import sys
import os
import logging
import time
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_optimized_quality_ensemble():
    """Test the Quality Ensemble with optimized High Relevance Engine"""
    print("🚀 Testing Optimized Quality Ensemble with High Relevance Engine")
    print("=" * 70)
    
    try:
        # Test 1: Import the quality ensemble engine
        print("1️⃣ Testing import...")
        from quality_ensemble_engine import get_quality_ensemble_recommendations
        print("✅ Successfully imported Quality Ensemble Engine")
        
        # Test 2: Test with high relevance engine only (optimized)
        print("\n2️⃣ Testing Quality Ensemble with High Relevance Engine only...")
        
        request_data = {
            'title': 'React Development',
            'description': 'Building a modern web application with React',
            'technologies': 'React, JavaScript, HTML, CSS',
            'max_recommendations': 3,  # Reduced for faster testing
            'engines': ['high_relevance']  # Only use high relevance engine
        }
        
        start_time = time.time()
        results = get_quality_ensemble_recommendations(user_id=1, request_data=request_data)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        
        print(f"✅ Quality Ensemble completed in {response_time:.2f}ms")
        print(f"📊 Results: {len(results)} recommendations")
        
        if results:
            print("\n📋 Sample Results:")
            for i, result in enumerate(results[:3], 1):
                print(f"  {i}. {result.get('title', 'No title')}")
                print(f"     Score: {result.get('score', 0):.1f}")
                print(f"     Ensemble Score: {result.get('ensemble_score', 0):.1f}")
                print(f"     Reason: {result.get('reason', 'No reason')[:80]}...")
                print()
        else:
            print("⚠️ No results returned")
        
        # Test 3: Test with multiple engines including high relevance
        print("\n3️⃣ Testing Quality Ensemble with multiple engines...")
        
        request_data_multi = {
            'title': 'Python Machine Learning',
            'description': 'Building a machine learning model with Python',
            'technologies': 'Python, scikit-learn, pandas, numpy',
            'max_recommendations': 3,  # Reduced for faster testing
            'engines': ['unified', 'high_relevance']  # Use unified and high relevance
        }
        
        start_time = time.time()
        results_multi = get_quality_ensemble_recommendations(user_id=1, request_data=request_data_multi)
        end_time = time.time()
        
        response_time_multi = (end_time - start_time) * 1000
        
        print(f"✅ Multi-engine Quality Ensemble completed in {response_time_multi:.2f}ms")
        print(f"📊 Results: {len(results_multi)} recommendations")
        
        if results_multi:
            print("\n📋 Sample Multi-Engine Results:")
            for i, result in enumerate(results_multi[:3], 1):
                print(f"  {i}. {result.get('title', 'No title')}")
                print(f"     Score: {result.get('score', 0):.1f}")
                print(f"     Ensemble Score: {result.get('ensemble_score', 0):.1f}")
                print(f"     Engine Votes: {result.get('engine_votes', {})}")
                print()
        
        print("🎉 All optimized tests completed successfully!")
        print(f"⏱️  Total response time: {response_time + response_time_multi:.2f}ms")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_optimized_quality_ensemble()
    sys.exit(0 if success else 1) 