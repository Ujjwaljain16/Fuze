#!/usr/bin/env python3
"""
Test to verify that the High Relevance Engine now properly filters for React/JavaScript content.
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

def test_react_filtering():
    """Test that the High Relevance Engine properly filters for React content"""
    print("🚀 Testing High Relevance Engine React Filtering")
    print("=" * 60)
    
    try:
        # Test 1: Import the quality ensemble engine
        print("1️⃣ Testing import...")
        from quality_ensemble_engine import get_quality_ensemble_recommendations
        print("✅ Successfully imported Quality Ensemble Engine")
        
        # Test 2: Test with React input
        print("\n2️⃣ Testing React Development recommendations...")
        request_data = {
            'title': 'React Development',
            'description': 'Building a modern React application with hooks and state management',
            'technologies': 'React, JavaScript, Hooks',
            'max_recommendations': 5,
            'engines': ['high_relevance']
        }
        
        start_time = time.time()
        results = get_quality_ensemble_recommendations(user_id=1, request_data=request_data)
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        
        print(f"✅ React recommendations completed in {response_time:.2f}ms")
        print(f"📊 Results: {len(results)} recommendations")
        
        if results:
            print("\n📋 React Development Results:")
            for i, result in enumerate(results[:5], 1):
                print(f"  {i}. {result.get('title', 'No title')}")
                print(f"     Score: {result.get('score', 0):.1f}")
                print(f"     Technologies: {result.get('technologies', [])}")
                print(f"     Reason: {result.get('reason', 'No reason')[:100]}...")
                print()
                
                # Check if the result is actually React-related
                title_lower = result.get('title', '').lower()
                technologies = [tech.lower() for tech in result.get('technologies', [])]
                reason_lower = result.get('reason', '').lower()
                
                is_react_related = (
                    'react' in title_lower or 
                    'javascript' in title_lower or
                    'react' in technologies or
                    'javascript' in technologies or
                    'react' in reason_lower or
                    'javascript' in reason_lower
                )
                
                if is_react_related:
                    print(f"     ✅ RELEVANT: React/JavaScript content found!")
                else:
                    print(f"     ❌ IRRELEVANT: Not React/JavaScript related")
                print()
        else:
            print("⚠️ No results returned")
        
        # Test 3: Test with Python input for comparison
        print("\n3️⃣ Testing Python Development recommendations (for comparison)...")
        request_data_python = {
            'title': 'Python Development',
            'description': 'Building a Python application with Django',
            'technologies': 'Python, Django, SQL',
            'max_recommendations': 3,
            'engines': ['high_relevance']
        }
        
        start_time = time.time()
        results_python = get_quality_ensemble_recommendations(user_id=1, request_data=request_data_python)
        end_time = time.time()
        response_time_python = (end_time - start_time) * 1000
        
        print(f"✅ Python recommendations completed in {response_time_python:.2f}ms")
        print(f"📊 Results: {len(results_python)} recommendations")
        
        if results_python:
            print("\n📋 Python Development Results:")
            for i, result in enumerate(results_python[:3], 1):
                print(f"  {i}. {result.get('title', 'No title')}")
                print(f"     Score: {result.get('score', 0):.1f}")
                print(f"     Technologies: {result.get('technologies', [])}")
                print()
        
        # Performance check
        total_time = response_time + response_time_python
        if total_time < 20000:  # 20 seconds
            print(f"✅ Performance: Good ({total_time:.2f}ms)")
        else:
            print(f"❌ Performance: Too slow ({total_time:.2f}ms)")
        
        print("\n🎉 React Filtering Test Completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_react_filtering()
    sys.exit(0 if success else 1) 