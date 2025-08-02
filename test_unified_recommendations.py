#!/usr/bin/env python3
"""
Test script for the unified intelligent recommendation system
"""

import requests
import json
import os
from datetime import datetime

# Configuration
API_BASE = 'http://localhost:5000/api'
JWT_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc1Mjg0MDg3NiwianRpIjoiZDEyYzQ2MmUtZWQyNy00ZGU2LTkzYTctN2M0NjY4NzVhZjgwIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjEiLCJuYmYiOjE3NTI4NDA4NzYsImV4cCI6MTc1Mjg0MTc3Nn0.3B4z6seAnRhxWxquKUb8WwKuMZOJ8-OoWSOAoBNoX_c'

HEADERS = {
    'Authorization': f'Bearer {JWT_TOKEN}',
    'Content-Type': 'application/json',
}

def test_health_check():
    """Test if the API is running"""
    print("\n" + "="*60)
    print("TESTING API HEALTH CHECK")
    print("="*60)
    
    try:
        resp = requests.get(f'{API_BASE}/health')
        print(f'Status Code: {resp.status_code}')
        if resp.status_code == 200:
            data = resp.json()
            print(f'API Status: {data.get("status")}')
            print(f'Database: {data.get("database")}')
            print(f'Version: {data.get("version")}')
            return True
        else:
            print(f'Error: {resp.text}')
            return False
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API. Make sure the Flask app is running on localhost:5000")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_unified_recommendations():
    """Test the unified recommendations endpoint with various inputs"""
    print("\n" + "="*60)
    print("TESTING UNIFIED RECOMMENDATIONS")
    print("="*60)
    
    test_cases = [
        {
            "name": "DSA Visualizer Project",
            "data": {
                "title": "DSA visualiser",
                "description": "A visualizer for data structure and algorithms that make it easier to understand the complexity easier just copy paste yr code and get a dynamic visualization of that with a detailed dry run for now available in java language only",
                "technologies": "java, instrumentation, byte buddy AST, JVM",
                "user_interests": "data structures, algorithms, java programming",
                "max_recommendations": 5,
                "diverse": True
            }
        },
        {
            "name": "React Native Mobile App",
            "data": {
                "title": "Mobile Expense Tracker",
                "description": "Build a mobile app for tracking expenses with payment integration and SMS notifications",
                "technologies": "react native, javascript, payment, mobile",
                "user_interests": "mobile development, react native, payment systems",
                "max_recommendations": 5,
                "diverse": True
            }
        },
        {
            "name": "Python AI Project",
            "data": {
                "title": "Machine Learning Model",
                "description": "Create a machine learning model for image classification using Python and TensorFlow",
                "technologies": "python, tensorflow, ai, machine learning",
                "user_interests": "artificial intelligence, python programming",
                "max_recommendations": 5,
                "diverse": True
            }
        },
        {
            "name": "Simple Web Development",
            "data": {
                "title": "Personal Portfolio Website",
                "description": "Create a simple personal portfolio website with HTML, CSS, and JavaScript",
                "technologies": "html, css, javascript, web",
                "user_interests": "web development, frontend",
                "max_recommendations": 5,
                "diverse": True
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['name']} ---")
        
        try:
            resp = requests.post(f'{API_BASE}/recommendations/unified', 
                               json=test_case['data'], 
                               headers=HEADERS)
            
            print(f'Status Code: {resp.status_code}')
            
            if resp.status_code == 200:
                data = resp.json()
                
                # Print context analysis
                context = data.get('context_analysis', {})
                if context:
                    input_analysis = context.get('input_analysis', {})
                    print(f"Input Analysis:")
                    print(f"  - Technologies: {', '.join(input_analysis.get('technologies', []))}")
                    print(f"  - Content Type: {input_analysis.get('content_type', 'Unknown')}")
                    print(f"  - Difficulty: {input_analysis.get('difficulty', 'Unknown')}")
                    print(f"  - Intent: {input_analysis.get('intent', 'Unknown')}")
                    print(f"  - Complexity Score: {input_analysis.get('complexity_score', 0)}%")
                    print(f"  - Key Concepts: {', '.join(input_analysis.get('key_concepts', [])[:5])}")
                
                # Print processing stats
                stats = context.get('processing_stats', {})
                print(f"Processing Stats:")
                print(f"  - Total Bookmarks Analyzed: {stats.get('total_bookmarks_analyzed', 0)}")
                print(f"  - Relevant Bookmarks Found: {stats.get('relevant_bookmarks_found', 0)}")
                
                # Print recommendations
                recommendations = data.get('recommendations', [])
                print(f"\nFound {len(recommendations)} recommendations:")
                
                for j, rec in enumerate(recommendations[:3], 1):  # Show top 3
                    print(f"\n{j}. {rec['title']}")
                    print(f"   Score: {rec['score']}%")
                    print(f"   Confidence: {rec['confidence']}%")
                    print(f"   Reason: {rec['reason']}")
                    print(f"   URL: {rec['url']}")
                    
                    analysis = rec.get('analysis', {})
                    if analysis:
                        print(f"   Analysis:")
                        print(f"     - Tech Match: {analysis.get('technology_match', 0)}")
                        print(f"     - Content Relevance: {analysis.get('content_relevance', 0)}")
                        print(f"     - Semantic Similarity: {analysis.get('semantic_similarity', 0)}")
                        print(f"     - Technologies: {', '.join(analysis.get('bookmark_technologies', [])[:3])}")
            else:
                print(f'Error: {resp.text}')
                
        except requests.exceptions.ConnectionError:
            print("ERROR: Could not connect to the API")
        except Exception as e:
            print(f"ERROR: {e}")

def test_unified_project_recommendations(project_id=1):
    """Test unified recommendations for a specific project"""
    print("\n" + "="*60)
    print(f"TESTING UNIFIED PROJECT RECOMMENDATIONS (Project ID: {project_id})")
    print("="*60)
    
    try:
        resp = requests.get(f'{API_BASE}/recommendations/unified-project/{project_id}', 
                           headers=HEADERS)
        
        print(f'Status Code: {resp.status_code}')
        
        if resp.status_code == 200:
            data = resp.json()
            
            # Print context analysis
            context = data.get('context_analysis', {})
            if context:
                project_analysis = context.get('project_analysis', {})
                print(f"Project Analysis:")
                print(f"  - Title: {project_analysis.get('title', 'Unknown')}")
                print(f"  - Technologies: {', '.join(project_analysis.get('technologies', []))}")
                print(f"  - Content Type: {project_analysis.get('content_type', 'Unknown')}")
                print(f"  - Difficulty: {project_analysis.get('difficulty', 'Unknown')}")
                print(f"  - Intent: {project_analysis.get('intent', 'Unknown')}")
                print(f"  - Complexity Score: {project_analysis.get('complexity_score', 0)}%")
                print(f"  - Key Concepts: {', '.join(project_analysis.get('key_concepts', [])[:5])}")
            
            # Print recommendations
            recommendations = data.get('recommendations', [])
            print(f"\nFound {len(recommendations)} recommendations:")
            
            for i, rec in enumerate(recommendations[:5], 1):
                print(f"\n{i}. {rec['title']}")
                print(f"   Score: {rec['score']}%")
                print(f"   Confidence: {rec['confidence']}%")
                print(f"   Reason: {rec['reason']}")
                print(f"   URL: {rec['url']}")
                
                analysis = rec.get('analysis', {})
                if analysis:
                    print(f"   Analysis:")
                    print(f"     - Tech Match: {analysis.get('technology_match', 0)}")
                    print(f"     - Content Relevance: {analysis.get('content_relevance', 0)}")
                    print(f"     - Semantic Similarity: {analysis.get('semantic_similarity', 0)}")
                    print(f"     - Technologies: {', '.join(analysis.get('bookmark_technologies', [])[:3])}")
        else:
            print(f'Error: {resp.text}')
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API")
    except Exception as e:
        print(f"ERROR: {e}")

def test_engine_directly():
    """Test the unified engine directly without API"""
    print("\n" + "="*60)
    print("TESTING UNIFIED ENGINE DIRECTLY")
    print("="*60)
    
    try:
        from unified_recommendation_engine import UnifiedRecommendationEngine
        
        engine = UnifiedRecommendationEngine()
        
        # Test context extraction
        test_input = {
            "title": "DSA visualiser",
            "description": "A visualizer for data structure and algorithms using java bytecode instrumentation",
            "technologies": "java, byte buddy, JVM",
            "user_interests": "data structures, algorithms"
        }
        
        context = engine.extract_context_from_input(**test_input)
        
        print("Context Extraction Test:")
        print(f"  - Technologies: {[tech['category'] for tech in context['technologies']]}")
        print(f"  - Content Type: {context['content_type']}")
        print(f"  - Difficulty: {context['difficulty']}")
        print(f"  - Intent: {context['intent']}")
        print(f"  - Complexity Score: {context['complexity_score']:.2f}")
        print(f"  - Key Concepts: {context['key_concepts'][:5]}")
        print(f"  - Requirements: {context['requirements']}")
        
        print("\n✅ Engine test completed successfully!")
        
    except ImportError:
        print("❌ Could not import UnifiedRecommendationEngine")
    except Exception as e:
        print(f"❌ Engine test failed: {e}")

if __name__ == '__main__':
    print("Unified Intelligent Recommendation System Test")
    print("="*60)
    print(f"Testing at: {datetime.now()}")
    
    # Test health first
    if test_health_check():
        # Test unified recommendations
        test_unified_recommendations()
        
        # Test project-specific recommendations
        test_unified_project_recommendations(project_id=1)
        
        # Test engine directly
        test_engine_directly()
    else:
        print("Skipping tests due to API connection issues")
    
    print("\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60) 