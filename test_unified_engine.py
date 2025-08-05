#!/usr/bin/env python3
"""
Test script for Improved Unified Recommendation Engine
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unified_recommendation_engine import UnifiedRecommendationEngine
from models import db, SavedContent, ContentAnalysis
from flask import Flask

def create_test_app():
    """Create a minimal Flask app for testing"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://localhost/fuze')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def test_unified_engine():
    """Test the improved unified recommendation engine"""
    print("🧪 Testing Improved Unified Recommendation Engine")
    print("=" * 60)
    
    # Create test app and context
    app = create_test_app()
    
    with app.app_context():
        # Initialize the engine
        engine = UnifiedRecommendationEngine()
        
        # Test cases
        test_cases = [
            {
                'name': 'Java DSA Visualizer Project',
                'title': 'DSA visualiser',
                'description': 'A visualizer for data structure and algorithms that make it easier to understand the complexity easier just copy paste yr code and get a dynamic visualization of that with a detailed dry run for now available in java language only',
                'technologies': 'java, jvm, byte buddy, ast',
                'user_interests': 'data structures, algorithms, visualization'
            },
            {
                'name': 'React Native Project',
                'title': 'React Native Mobile App',
                'description': 'Building a cross-platform mobile application with React Native and TypeScript',
                'technologies': 'react native, typescript, firebase',
                'user_interests': 'mobile development, react, typescript'
            },
            {
                'name': 'Python Backend API',
                'title': 'Python Django REST API',
                'description': 'Building a RESTful API with Django and PostgreSQL',
                'technologies': 'python, django, postgresql, redis',
                'user_interests': 'backend development, api design, python'
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 Test Case {i}: {test_case['name']}")
            print("-" * 40)
            
            start_time = time.time()
            
            try:
                # Extract context
                context = engine.extract_context_from_input(
                    title=test_case['title'],
                    description=test_case['description'],
                    technologies=test_case['technologies'],
                    user_interests=test_case['user_interests']
                )
                
                print(f"✅ Context extraction time: {(time.time() - start_time) * 1000:.2f}ms")
                print(f"📊 Extracted technologies: {context.get('primary_technologies', [])}")
                print(f"📊 Difficulty: {context.get('difficulty', 'unknown')}")
                print(f"📊 Content type: {context.get('content_type', 'unknown')}")
                
                # Get sample bookmarks (simulate content from database)
                sample_bookmarks = get_sample_bookmarks()
                
                if sample_bookmarks:
                    # Get recommendations
                    recommendations = engine.get_recommendations(
                        bookmarks=sample_bookmarks,
                        context=context,
                        max_recommendations=5
                    )
                    
                    total_time = (time.time() - start_time) * 1000
                    print(f"✅ Total response time: {total_time:.2f}ms")
                    print(f"📊 Found {len(recommendations)} recommendations")
                    
                    # Display top recommendations
                    for j, rec in enumerate(recommendations[:3], 1):
                        print(f"\n  {j}. {rec['title']}")
                        print(f"     Score: {rec['score']:.2f}")
                        print(f"     Match Score: {rec['match_score']:.2f}")
                        print(f"     Technologies: {', '.join(rec.get('technologies', [])[:3])}")
                        print(f"     Reason: {rec['reason'][:100]}...")
                        print(f"     Confidence: {rec['confidence']:.2f}")
                else:
                    print("⚠️  No sample bookmarks available for testing")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()

def get_sample_bookmarks():
    """Get sample bookmarks from database for testing"""
    try:
        # Get some sample content from the database
        sample_content = SavedContent.query.filter(
            SavedContent.quality_score >= 7,
            SavedContent.extracted_text.isnot(None),
            SavedContent.extracted_text != ''
        ).limit(20).all()
        
        if not sample_content:
            print("⚠️  No content found in database, creating mock data")
            return create_mock_bookmarks()
        
        # Convert to the format expected by the engine
        bookmarks = []
        for content in sample_content:
            bookmarks.append({
                'id': content.id,
                'title': content.title,
                'url': content.url,
                'extracted_text': content.extracted_text or '',
                'tags': content.tags or '',
                'notes': content.notes or '',
                'quality_score': content.quality_score or 7.0,
                'created_at': content.saved_at
            })
        
        return bookmarks
        
    except Exception as e:
        print(f"Error getting sample bookmarks: {e}")
        return create_mock_bookmarks()

def create_mock_bookmarks():
    """Create mock bookmarks for testing"""
    return [
        {
            'id': 1,
            'title': 'Java Data Structures and Algorithms Tutorial',
            'url': 'https://example.com/java-dsa',
            'extracted_text': 'Comprehensive guide to data structures and algorithms in Java. Learn about arrays, linked lists, trees, graphs, and sorting algorithms. Includes practical examples and performance analysis.',
            'tags': 'java, data structures, algorithms, tutorial',
            'notes': 'Excellent resource for Java DSA',
            'quality_score': 9.0,
            'created_at': '2024-01-15'
        },
        {
            'id': 2,
            'title': 'React Native Development Guide',
            'url': 'https://example.com/react-native',
            'extracted_text': 'Complete guide to building mobile apps with React Native. Covers components, navigation, state management, and deployment.',
            'tags': 'react native, mobile, javascript, tutorial',
            'notes': 'Great for mobile development',
            'quality_score': 8.5,
            'created_at': '2024-01-10'
        },
        {
            'id': 3,
            'title': 'Python Django REST API Tutorial',
            'url': 'https://example.com/django-api',
            'extracted_text': 'Build RESTful APIs with Django and Django REST Framework. Learn about serializers, viewsets, authentication, and database integration.',
            'tags': 'python, django, api, rest, tutorial',
            'notes': 'Comprehensive Django API guide',
            'quality_score': 8.0,
            'created_at': '2024-01-05'
        },
        {
            'id': 4,
            'title': 'Advanced Java Programming Techniques',
            'url': 'https://example.com/advanced-java',
            'extracted_text': 'Advanced Java programming concepts including reflection, bytecode manipulation, JVM internals, and performance optimization.',
            'tags': 'java, advanced, jvm, bytecode, performance',
            'notes': 'Advanced Java concepts',
            'quality_score': 9.5,
            'created_at': '2024-01-20'
        },
        {
            'id': 5,
            'title': 'Data Structure Visualization Tools',
            'url': 'https://example.com/dsa-viz',
            'extracted_text': 'Tools and techniques for visualizing data structures and algorithms. Includes interactive demos and step-by-step visualizations.',
            'tags': 'visualization, data structures, algorithms, tools',
            'notes': 'Great for understanding DSA concepts',
            'quality_score': 8.8,
            'created_at': '2024-01-12'
        }
    ]

if __name__ == "__main__":
    test_unified_engine() 