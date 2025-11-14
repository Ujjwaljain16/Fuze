#!/usr/bin/env python3
"""
Test script to verify that the High Relevance Engine is working properly
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

def test_high_relevance_engine():
    """Test the High Relevance Engine directly"""
    print("🧪 Testing High Relevance Engine Directly")
    print("=" * 50)
    
    try:
        # Test 1: Import the engine
        print("1️⃣ Testing import...")
        from high_relevance_engine import high_relevance_engine
        print("✅ Successfully imported High Relevance Engine")
        
        # Test 2: Test with sample data
        print("\n2️⃣ Testing with sample data...")
        sample_bookmarks = [
            {
                'id': 1,
                'title': 'React Hooks Tutorial - Complete Guide',
                'url': 'https://example.com/react-hooks',
                'extracted_text': 'Learn how to use React hooks for state management, useEffect, useState, and custom hooks',
                'tags': 'react, javascript, hooks, frontend',
                'notes': 'Great tutorial for beginners',
                'quality_score': 8.5,
                'created_at': datetime.now(),
                'technologies': ['react', 'javascript', 'hooks']
            },
            {
                'id': 2,
                'title': 'Python Flask API Development',
                'url': 'https://example.com/flask-api',
                'extracted_text': 'Build REST APIs with Python Flask framework, database integration, authentication',
                'tags': 'python, flask, api, backend',
                'notes': 'Comprehensive guide for API development',
                'quality_score': 9.0,
                'created_at': datetime.now(),
                'technologies': ['python', 'flask', 'api']
            },
            {
                'id': 3,
                'title': 'Docker Containerization Best Practices',
                'url': 'https://example.com/docker-best-practices',
                'extracted_text': 'Learn Docker containerization, multi-stage builds, security, and deployment',
                'tags': 'docker, devops, containers, deployment',
                'notes': 'Production-ready Docker practices',
                'quality_score': 8.8,
                'created_at': datetime.now(),
                'technologies': ['docker', 'devops', 'containers']
            }
        ]
        
        user_input = {
            'title': 'Web Development Project',
            'description': 'I need to build a web application with React frontend and Python Flask backend. I want to learn how to implement user authentication and API development.',
            'technologies': 'react, python, flask, javascript, api',
            'project_id': 1
        }
        
        start_time = time.time()
        results = high_relevance_engine.get_high_relevance_recommendations(
            bookmarks=sample_bookmarks,
            user_input=user_input,
            max_recommendations=5
        )
        processing_time = (time.time() - start_time) * 1000
        
        print(f"✅ Successfully processed in {processing_time:.1f}ms")
        print(f"📊 Generated {len(results)} recommendations")
        
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result.get('title', 'N/A')} (Score: {result.get('total_score', 0):.1f})")
            print(f"      Reason: {result.get('reason', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing High Relevance Engine: {e}")
        return False

def test_quality_ensemble_with_high_relevance():
    """Test the quality ensemble with High Relevance Engine"""
    print("\n🧪 Testing Quality Ensemble with High Relevance Engine")
    print("=" * 60)
    
    try:
        # Test 1: Import the quality ensemble engine
        print("1️⃣ Testing quality ensemble import...")
        from quality_ensemble_engine import get_quality_ensemble_engine
        
        engine = get_quality_ensemble_engine()
        print("✅ Successfully imported Quality Ensemble Engine")
        
        # Test 2: Check if high_relevance is in available engines
        print("\n2️⃣ Checking available engines...")
        available_engines = engine._get_available_engines(['high_relevance'])
        print(f"✅ Available engines: {available_engines}")
        
        if 'high_relevance' in available_engines:
            print("✅ High Relevance Engine is available in quality ensemble")
        else:
            print("❌ High Relevance Engine not available in quality ensemble")
            return False
        
        # Test 3: Test with sample request
        print("\n3️⃣ Testing quality ensemble with sample request...")
        from quality_ensemble_engine import QualityEnsembleRequest
        
        request = QualityEnsembleRequest(
            user_id=1,
            title='Web Development Project',
            description='Building a web app with React and Python Flask',
            technologies='react, python, flask, javascript, api',
            project_id=1,
            max_recommendations=5,
            engines=['high_relevance']  # Test only high relevance engine
        )
        
        start_time = time.time()
        results = engine.get_quality_ensemble_recommendations(request)
        processing_time = (time.time() - start_time) * 1000
        
        print(f"✅ Quality ensemble completed in {processing_time:.1f}ms")
        print(f"📊 Generated {len(results)} recommendations")
        
        for i, result in enumerate(results[:3], 1):
            print(f"   {i}. {result.title} (Score: {result.ensemble_score:.1f})")
            print(f"      Engine votes: {result.engine_votes}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing quality ensemble: {e}")
        return False

def test_endpoint_integration():
    """Test the endpoint integration"""
    print("\n🧪 Testing Endpoint Integration")
    print("=" * 40)
    
    try:
        # Test the endpoint function
        print("1️⃣ Testing endpoint function...")
        from quality_ensemble_engine import get_quality_ensemble_recommendations
        
        request_data = {
            'title': 'Web Development Project',
            'description': 'Building a web app with React and Python Flask',
            'technologies': 'react, python, flask, javascript, api',
            'project_id': 1,
            'max_recommendations': 5,
            'engines': ['high_relevance', 'unified']  # Include both engines
        }
        
        start_time = time.time()
        results = get_quality_ensemble_recommendations(user_id=1, request_data=request_data)
        processing_time = (time.time() - start_time) * 1000
        
        print(f"✅ Endpoint function completed in {processing_time:.1f}ms")
        print(f"📊 Generated {len(results)} recommendations")
        
        # Check if results have high relevance engine votes
        high_relevance_votes = 0
        for result in results:
            if 'high_relevance' in result.get('engine_votes', {}):
                high_relevance_votes += 1
        
        print(f"✅ {high_relevance_votes}/{len(results)} results have High Relevance Engine votes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing endpoint integration: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing High Relevance Engine in Quality Ensemble")
    print("=" * 70)
    
    # Test 1: Direct engine test
    test1_success = test_high_relevance_engine()
    
    # Test 2: Quality ensemble integration
    test2_success = test_quality_ensemble_with_high_relevance()
    
    # Test 3: Endpoint integration
    test3_success = test_endpoint_integration()
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 30)
    print(f"High Relevance Engine Direct: {'✅ PASSED' if test1_success else '❌ FAILED'}")
    print(f"Quality Ensemble Integration: {'✅ PASSED' if test2_success else '❌ FAILED'}")
    print(f"Endpoint Integration: {'✅ PASSED' if test3_success else '❌ FAILED'}")
    
    if test1_success and test2_success and test3_success:
        print("\n🎉 All tests passed! High Relevance Engine is working in quality ensemble.")
        print("🌐 You can now use: http://127.0.0.1:5000/api/recommendations/ensemble/quality")
        return True
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 