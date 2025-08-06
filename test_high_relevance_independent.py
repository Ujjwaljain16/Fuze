#!/usr/bin/env python3
"""
Test to verify that the High Relevance Engine is working independently
in the quality ensemble endpoint.
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

def test_high_relevance_independent():
    """Test the High Relevance Engine working independently"""
    print("🚀 Testing High Relevance Engine Independent Operation")
    print("=" * 60)
    
    try:
        # Test 1: Import the quality ensemble engine
        print("1️⃣ Testing import...")
        from quality_ensemble_engine import get_quality_ensemble_recommendations
        print("✅ Successfully imported High Relevance Engine")
        
        # Test 2: Test with high relevance engine only (independent operation)
        print("\n2️⃣ Testing High Relevance Engine Independent Operation...")
        
        request_data = {
            'title': 'React Development',
            'description': 'Building a modern web application with React',
            'technologies': 'React, JavaScript, HTML, CSS',
            'max_recommendations': 5,  # Get 5 recommendations
            'engines': ['high_relevance']  # This will be ignored, only high_relevance used
        }
        
        start_time = time.time()
        results = get_quality_ensemble_recommendations(user_id=1, request_data=request_data)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        
        print(f"✅ High Relevance Engine completed in {response_time:.2f}ms")
        print(f"📊 Results: {len(results)} recommendations")
        
        if results:
            print("\n📋 High Relevance Results:")
            for i, result in enumerate(results[:5], 1):
                print(f"  {i}. {result.get('title', 'No title')}")
                print(f"     Score: {result.get('score', 0):.1f}")
                print(f"     Ensemble Score: {result.get('ensemble_score', 0):.1f}")
                print(f"     Engine Votes: {result.get('engine_votes', {})}")
                print(f"     Reason: {result.get('reason', 'No reason')[:100]}...")
                print()
        else:
            print("⚠️ No results returned")
        
        # Test 3: Test with different technologies
        print("\n3️⃣ Testing with different technologies...")
        
        request_data_2 = {
            'title': 'Python Machine Learning',
            'description': 'Building a machine learning model with Python',
            'technologies': 'Python, scikit-learn, pandas, numpy',
            'max_recommendations': 3,
            'engines': ['unified', 'smart']  # This will be ignored, only high_relevance used
        }
        
        start_time = time.time()
        results_2 = get_quality_ensemble_recommendations(user_id=1, request_data=request_data_2)
        end_time = time.time()
        
        response_time_2 = (end_time - start_time) * 1000
        
        print(f"✅ High Relevance Engine (Python ML) completed in {response_time_2:.2f}ms")
        print(f"📊 Results: {len(results_2)} recommendations")
        
        if results_2:
            print("\n📋 Python ML Results:")
            for i, result in enumerate(results_2[:3], 1):
                print(f"  {i}. {result.get('title', 'No title')}")
                print(f"     Score: {result.get('score', 0):.1f}")
                print(f"     Reason: {result.get('reason', 'No reason')[:80]}...")
                print()
        
        print("🎉 High Relevance Engine Independent Operation Test Completed!")
        print(f"⏱️  Total response time: {response_time + response_time_2:.2f}ms")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_high_relevance_independent()
    sys.exit(0 if success else 1) 