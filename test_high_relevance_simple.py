#!/usr/bin/env python3
"""
Simple test to verify that the High Relevance Engine is working independently
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

def test_high_relevance_simple():
    """Simple test for High Relevance Engine independent operation"""
    print("🚀 Testing High Relevance Engine Simple Operation")
    print("=" * 50)
    
    try:
        # Test 1: Import the quality ensemble engine
        print("1️⃣ Testing import...")
        from quality_ensemble_engine import get_quality_ensemble_recommendations
        print("✅ Successfully imported Quality Ensemble Engine")
        
        # Test 2: Simple test with minimal data
        print("\n2️⃣ Testing High Relevance Engine...")
        
        request_data = {
            'title': 'React App',
            'description': 'Building a React application',
            'technologies': 'React, JavaScript',
            'max_recommendations': 3,  # Small number for speed
            'engines': ['high_relevance']
        }
        
        start_time = time.time()
        results = get_quality_ensemble_recommendations(user_id=1, request_data=request_data)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        
        print(f"✅ High Relevance Engine completed in {response_time:.2f}ms")
        print(f"📊 Results: {len(results)} recommendations")
        
        if results:
            print("\n📋 Results:")
            for i, result in enumerate(results[:3], 1):
                print(f"  {i}. {result.get('title', 'No title')}")
                print(f"     Score: {result.get('score', 0):.1f}")
                print(f"     Reason: {result.get('reason', 'No reason')[:80]}...")
                print()
        else:
            print("⚠️ No results returned")
        
        print("🎉 High Relevance Engine Test Completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_high_relevance_simple()
    sys.exit(0 if success else 1) 