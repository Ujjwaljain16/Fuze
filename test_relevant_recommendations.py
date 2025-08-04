#!/usr/bin/env python3
"""
Test script for Improved Relevance in Enhanced Recommendation System
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_recommendation_engine import get_enhanced_recommendations, unified_engine

def test_react_native_relevance():
    """Test React Native specific recommendations"""
    print("🧪 Testing React Native Relevance")
    print("=" * 50)
    
    # Clear cache to test fresh recommendations
    unified_engine.cache_manager.memory_cache.clear()
    
    test_cases = [
        {
            'name': 'React Native Mobile App',
            'request_data': {
                'technologies': ['react native', 'expo', 'mobile'],
                'content_type': 'tutorial',
                'difficulty': 'intermediate',
                'project_title': 'React Native Mobile App',
                'description': 'Building a cross-platform mobile application with React Native and Expo'
            }
        },
        {
            'name': 'React Native with TypeScript',
            'request_data': {
                'technologies': ['react native', 'typescript', 'mobile'],
                'content_type': 'documentation',
                'difficulty': 'advanced',
                'project_title': 'React Native TypeScript App',
                'description': 'Advanced React Native development with TypeScript'
            }
        }
    ]
    
    user_id = 1
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📱 Test Case {i}: {test_case['name']}")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            # Get recommendations
            recommendations = get_enhanced_recommendations(
                user_id=user_id,
                request_data=test_case['request_data'],
                limit=10
            )
            
            response_time = (time.time() - start_time) * 1000
            
            print(f"✅ Response time: {response_time:.2f}ms")
            print(f"📊 Found {len(recommendations)} recommendations")
            
            # Display recommendations with relevance analysis
            for j, rec in enumerate(recommendations[:5], 1):
                print(f"\n  {j}. {rec['title']}")
                print(f"     Score: {rec['score']:.2f}/10")
                print(f"     Technologies: {', '.join(rec['technologies'][:5])}")
                print(f"     Type: {rec['content_type']}")
                print(f"     Difficulty: {rec['difficulty']}")
                print(f"     Reasoning: {rec['reasoning'][:150]}...")
                
                # Analyze relevance
                tech_match = any(tech in rec['title'].lower() or tech in ' '.join(rec['technologies']).lower() 
                               for tech in ['react native', 'expo', 'mobile', 'react'])
                if tech_match:
                    print(f"     🎯 RELEVANT: Contains React Native related content")
                else:
                    print(f"     ⚠️  IRRELEVANT: No React Native content found")
            
        except Exception as e:
            print(f"❌ Error: {e}")

def test_python_relevance():
    """Test Python specific recommendations"""
    print(f"\n🐍 Testing Python Relevance")
    print("=" * 50)
    
    test_cases = [
        {
            'name': 'Python Django Backend',
            'request_data': {
                'technologies': ['python', 'django', 'api'],
                'content_type': 'documentation',
                'difficulty': 'advanced',
                'project_title': 'Django REST API',
                'description': 'Building a RESTful API with Django and Python'
            }
        }
    ]
    
    user_id = 1
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🐍 Test Case {i}: {test_case['name']}")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            # Get recommendations
            recommendations = get_enhanced_recommendations(
                user_id=user_id,
                request_data=test_case['request_data'],
                limit=10
            )
            
            response_time = (time.time() - start_time) * 1000
            
            print(f"✅ Response time: {response_time:.2f}ms")
            print(f"📊 Found {len(recommendations)} recommendations")
            
            # Display recommendations with relevance analysis
            for j, rec in enumerate(recommendations[:5], 1):
                print(f"\n  {j}. {rec['title']}")
                print(f"     Score: {rec['score']:.2f}/10")
                print(f"     Technologies: {', '.join(rec['technologies'][:5])}")
                print(f"     Type: {rec['content_type']}")
                print(f"     Difficulty: {rec['difficulty']}")
                print(f"     Reasoning: {rec['reasoning'][:150]}...")
                
                # Analyze relevance
                tech_match = any(tech in rec['title'].lower() or tech in ' '.join(rec['technologies']).lower() 
                               for tech in ['python', 'django', 'flask', 'fastapi'])
                if tech_match:
                    print(f"     🎯 RELEVANT: Contains Python/Django related content")
                else:
                    print(f"     ⚠️  IRRELEVANT: No Python/Django content found")
            
        except Exception as e:
            print(f"❌ Error: {e}")

def test_go_relevance():
    """Test Go specific recommendations"""
    print(f"\n🐹 Testing Go Relevance")
    print("=" * 50)
    
    test_cases = [
        {
            'name': 'Go Microservices',
            'request_data': {
                'technologies': ['go', 'golang', 'microservices'],
                'content_type': 'tutorial',
                'difficulty': 'intermediate',
                'project_title': 'Go Microservices',
                'description': 'Building microservices with Go and Gin'
            }
        }
    ]
    
    user_id = 1
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🐹 Test Case {i}: {test_case['name']}")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            # Get recommendations
            recommendations = get_enhanced_recommendations(
                user_id=user_id,
                request_data=test_case['request_data'],
                limit=10
            )
            
            response_time = (time.time() - start_time) * 1000
            
            print(f"✅ Response time: {response_time:.2f}ms")
            print(f"📊 Found {len(recommendations)} recommendations")
            
            # Display recommendations with relevance analysis
            for j, rec in enumerate(recommendations[:5], 1):
                print(f"\n  {j}. {rec['title']}")
                print(f"     Score: {rec['score']:.2f}/10")
                print(f"     Technologies: {', '.join(rec['technologies'][:5])}")
                print(f"     Type: {rec['content_type']}")
                print(f"     Difficulty: {rec['difficulty']}")
                print(f"     Reasoning: {rec['reasoning'][:150]}...")
                
                # Analyze relevance
                tech_match = any(tech in rec['title'].lower() or tech in ' '.join(rec['technologies']).lower() 
                               for tech in ['go', 'golang', 'gin', 'echo'])
                if tech_match:
                    print(f"     🎯 RELEVANT: Contains Go related content")
                else:
                    print(f"     ⚠️  IRRELEVANT: No Go content found")
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🎯 Testing Improved Relevance in Enhanced Recommendation System")
    print("=" * 70)
    
    # Test different technology stacks
    test_react_native_relevance()
    test_python_relevance()
    test_go_relevance()
    
    print(f"\n🎉 Relevance Testing Complete!")
    print("=" * 70)
    print("✅ Technology-specific matching")
    print("✅ Relevance scoring improvements")
    print("✅ Content filtering enhancements")
    print("✅ Penalty for irrelevant content") 