#!/usr/bin/env python3
"""
Test script for Gemini AI-enhanced recommendation system
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

def test_gemini_status():
    """Test Gemini AI availability"""
    print("\n" + "="*60)
    print("TESTING GEMINI AI STATUS")
    print("="*60)
    
    try:
        resp = requests.get(f'{API_BASE}/recommendations/gemini-status', headers=HEADERS)
        print(f'Status Code: {resp.status_code}')
        
        if resp.status_code == 200:
            data = resp.json()
            print(f'Gemini Available: {data.get("gemini_available")}')
            print(f'Status: {data.get("status")}')
            print(f'Message: {data.get("message")}')
            return data.get("gemini_available", False)
        else:
            print(f'Error: {resp.text}')
            return False
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_gemini_enhanced_recommendations():
    """Test Gemini-enhanced recommendations"""
    print("\n" + "="*60)
    print("TESTING GEMINI-ENHANCED RECOMMENDATIONS")
    print("="*60)
    
    test_cases = [
        {
            "name": "DSA Visualizer Project (Gemini Enhanced)",
            "data": {
                "title": "DSA visualiser",
                "description": "A visualizer for data structure and algorithms that make it easier to understand the complexity easier just copy paste yr code and get a dynamic visualization of that with a detailed dry run for now available in java language only",
                "technologies": "java, instrumentation, byte buddy AST, JVM",
                "user_interests": "data structures, algorithms, java programming, bytecode manipulation",
                "max_recommendations": 5
            }
        },
        {
            "name": "React Native Mobile App (Gemini Enhanced)",
            "data": {
                "title": "Mobile Expense Tracker",
                "description": "Build a mobile app for tracking expenses with payment integration and SMS notifications using React Native",
                "technologies": "react native, javascript, payment, mobile, expo",
                "user_interests": "mobile development, react native, payment systems, user experience",
                "max_recommendations": 5
            }
        },
        {
            "name": "Python AI Project (Gemini Enhanced)",
            "data": {
                "title": "Machine Learning Model",
                "description": "Create a machine learning model for image classification using Python and TensorFlow with data preprocessing and model evaluation",
                "technologies": "python, tensorflow, ai, machine learning, numpy, pandas",
                "user_interests": "artificial intelligence, python programming, deep learning, computer vision",
                "max_recommendations": 5
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['name']} ---")
        
        try:
            resp = requests.post(f'{API_BASE}/recommendations/gemini-enhanced', 
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
                
                # Print Gemini insights
                gemini_insights = context.get('gemini_insights', {})
                if gemini_insights:
                    print(f"Gemini Insights:")
                    print(f"  - Project Type: {gemini_insights.get('project_type', 'Unknown')}")
                    print(f"  - Complexity Level: {gemini_insights.get('complexity_level', 'Unknown')}")
                    print(f"  - Development Stage: {gemini_insights.get('development_stage', 'Unknown')}")
                    print(f"  - Learning Needs: {', '.join(gemini_insights.get('learning_needs', [])[:3])}")
                    print(f"  - Focus Areas: {', '.join(gemini_insights.get('focus_areas', [])[:3])}")
                    print(f"  - Project Summary: {gemini_insights.get('project_summary', 'N/A')}")
                
                # Print processing stats
                stats = context.get('processing_stats', {})
                print(f"Processing Stats:")
                print(f"  - Total Bookmarks Analyzed: {stats.get('total_bookmarks_analyzed', 0)}")
                print(f"  - Relevant Bookmarks Found: {stats.get('relevant_bookmarks_found', 0)}")
                print(f"  - Gemini Enhanced: {stats.get('gemini_enhanced', False)}")
                
                # Print recommendations
                recommendations = data.get('recommendations', [])
                print(f"\nFound {len(recommendations)} Gemini-enhanced recommendations:")
                
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
                        
                        # Show Gemini-specific analysis
                        if analysis.get('gemini_technologies'):
                            print(f"     - Gemini Technologies: {', '.join(analysis.get('gemini_technologies', [])[:3])}")
                        if analysis.get('gemini_summary'):
                            print(f"     - Gemini Summary: {analysis.get('gemini_summary', '')[:100]}...")
                        if analysis.get('quality_indicators'):
                            quality = analysis.get('quality_indicators', {})
                            print(f"     - Quality: Completeness={quality.get('completeness', 0)}%, Clarity={quality.get('clarity', 0)}%")
                        if analysis.get('learning_objectives'):
                            print(f"     - Learning Objectives: {', '.join(analysis.get('learning_objectives', [])[:2])}")
            else:
                print(f'Error: {resp.text}')
                
        except requests.exceptions.ConnectionError:
            print("ERROR: Could not connect to the API")
        except Exception as e:
            print(f"ERROR: {e}")

def test_gemini_enhanced_project_recommendations(project_id=1):
    """Test Gemini-enhanced project recommendations"""
    print("\n" + "="*60)
    print(f"TESTING GEMINI-ENHANCED PROJECT RECOMMENDATIONS (Project ID: {project_id})")
    print("="*60)
    
    try:
        resp = requests.get(f'{API_BASE}/recommendations/gemini-enhanced-project/{project_id}', 
                           headers=HEADERS)
        
        print(f'Status Code: {resp.status_code}')
        
        if resp.status_code == 200:
            data = resp.json()
            
            # Print context analysis
            context = data.get('context_analysis', {})
            if context:
                input_analysis = context.get('input_analysis', {})
                print(f"Project Analysis:")
                print(f"  - Title: {input_analysis.get('title', 'Unknown')}")
                print(f"  - Technologies: {', '.join(input_analysis.get('technologies', []))}")
                print(f"  - Content Type: {input_analysis.get('content_type', 'Unknown')}")
                print(f"  - Difficulty: {input_analysis.get('difficulty', 'Unknown')}")
                print(f"  - Intent: {input_analysis.get('intent', 'Unknown')}")
                print(f"  - Complexity Score: {input_analysis.get('complexity_score', 0)}%")
                print(f"  - Key Concepts: {', '.join(input_analysis.get('key_concepts', [])[:5])}")
            
            # Print Gemini insights
            gemini_insights = context.get('gemini_insights', {})
            if gemini_insights:
                print(f"Gemini Project Insights:")
                print(f"  - Project Type: {gemini_insights.get('project_type', 'Unknown')}")
                print(f"  - Complexity Level: {gemini_insights.get('complexity_level', 'Unknown')}")
                print(f"  - Development Stage: {gemini_insights.get('development_stage', 'Unknown')}")
                print(f"  - Learning Needs: {', '.join(gemini_insights.get('learning_needs', [])[:3])}")
                print(f"  - Technical Requirements: {', '.join(gemini_insights.get('technical_requirements', [])[:3])}")
                print(f"  - Project Summary: {gemini_insights.get('project_summary', 'N/A')}")
            
            # Print recommendations
            recommendations = data.get('recommendations', [])
            print(f"\nFound {len(recommendations)} Gemini-enhanced project recommendations:")
            
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
                    
                    # Show Gemini-specific analysis
                    if analysis.get('gemini_technologies'):
                        print(f"     - Gemini Technologies: {', '.join(analysis.get('gemini_technologies', [])[:3])}")
                    if analysis.get('gemini_summary'):
                        print(f"     - Gemini Summary: {analysis.get('gemini_summary', '')[:100]}...")
                    if analysis.get('quality_indicators'):
                        quality = analysis.get('quality_indicators', {})
                        print(f"     - Quality: Completeness={quality.get('completeness', 0)}%, Clarity={quality.get('clarity', 0)}%")
        else:
            print(f'Error: {resp.text}')
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API")
    except Exception as e:
        print(f"ERROR: {e}")

def test_bookmark_analysis(bookmark_id=1):
    """Test individual bookmark analysis with Gemini"""
    print("\n" + "="*60)
    print(f"TESTING BOOKMARK ANALYSIS WITH GEMINI (Bookmark ID: {bookmark_id})")
    print("="*60)
    
    try:
        resp = requests.get(f'{API_BASE}/recommendations/analyze-bookmark/{bookmark_id}', 
                           headers=HEADERS)
        
        print(f'Status Code: {resp.status_code}')
        
        if resp.status_code == 200:
            data = resp.json()
            
            print(f"Bookmark: {data.get('title', 'Unknown')}")
            print(f"URL: {data.get('url', 'Unknown')}")
            
            analysis = data.get('gemini_analysis', {})
            if analysis:
                print(f"\nGemini Analysis:")
                print(f"  - Technologies: {', '.join(analysis.get('technologies', []))}")
                print(f"  - Content Type: {analysis.get('content_type', 'Unknown')}")
                print(f"  - Difficulty: {analysis.get('difficulty', 'Unknown')}")
                print(f"  - Intent: {analysis.get('intent', 'Unknown')}")
                print(f"  - Relevance Score: {analysis.get('relevance_score', 0)}%")
                print(f"  - Target Audience: {analysis.get('target_audience', 'Unknown')}")
                print(f"  - Key Concepts: {', '.join(analysis.get('key_concepts', [])[:5])}")
                print(f"  - Learning Objectives: {', '.join(analysis.get('learning_objectives', [])[:3])}")
                print(f"  - Prerequisites: {', '.join(analysis.get('prerequisites', [])[:3])}")
                
                quality = analysis.get('quality_indicators', {})
                if quality:
                    print(f"  - Quality Indicators:")
                    print(f"    * Completeness: {quality.get('completeness', 0)}%")
                    print(f"    * Clarity: {quality.get('clarity', 0)}%")
                    print(f"    * Practical Value: {quality.get('practical_value', 0)}%")
                
                if analysis.get('summary'):
                    print(f"  - Summary: {analysis.get('summary', '')}")
        else:
            print(f'Error: {resp.text}')
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API")
    except Exception as e:
        print(f"ERROR: {e}")

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

if __name__ == '__main__':
    print("Gemini AI-Enhanced Recommendation System Test")
    print("="*60)
    print(f"Testing at: {datetime.now()}")
    
    # Test health first
    if test_health_check():
        # Test Gemini status
        gemini_available = test_gemini_status()
        
        if gemini_available:
            # Test Gemini-enhanced recommendations
            test_gemini_enhanced_recommendations()
            test_gemini_enhanced_project_recommendations(project_id=1)
            test_bookmark_analysis(bookmark_id=1)
        else:
            print("\n⚠️  Gemini AI is not available. Please check your GEMINI_API_KEY environment variable.")
            print("The system will fall back to the unified recommendation engine.")
    else:
        print("Skipping tests due to API connection issues")
    
    print("\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60) 