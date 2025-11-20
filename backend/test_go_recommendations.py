#!/usr/bin/env python3
"""
Test Go lang recommendations for user 8
"""

import sys
import os
import json

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def test_go_recommendations():
    """Test Go lang recommendations for user 8"""
    try:
        # Set up Flask application context for database access
        from flask import Flask
        import os

        # Load environment variables
        os.environ.setdefault('FLASK_APP', 'run_production.py')
        os.environ.setdefault('FLASK_ENV', 'development')

        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/fuze')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = 'test-key'

        # Initialize database
        from models import db
        db.init_app(app)

        with app.app_context():
            from ml.unified_recommendation_orchestrator import UnifiedRecommendationOrchestrator, UnifiedRecommendationRequest

            print("🎯 TESTING GO LANG RECOMMENDATIONS FOR USER 8")
            print("=" * 60)

            # Create test request
            request = UnifiedRecommendationRequest(
                user_id=8,
                title='Learn and develop backend in Go lang',
                description='Learn go lang backend concepts for building REST APIs',
                technologies=['Go lang', 'Backend', 'RESTful'],
                user_interests='Backend development, API design',
                max_recommendations=5
            )

            print(f"Request: {request.title}")
            print(f"Technologies: {request.technologies}")
            print()

            # Get orchestrator
            orchestrator = UnifiedRecommendationOrchestrator()

            print("Note: Using mock data since database connection not available in test")
            print("This demonstrates the filtering logic with sample content.")
            print()

            # Since we can't access the database, let's create a simple demonstration
            # of how the filtering would work by manually calling the engine methods

            from ml.unified_recommendation_orchestrator import ContextAwareEngine

            # Create mock content for testing
            content_list = [
                {
                    'id': 1,
                    'title': 'Go Backend Tutorial: Building REST APIs',
                    'extracted_text': 'Learn Go programming for backend development with REST APIs',
                    'technologies': ['Go', 'Backend', 'REST'],
                    'quality_score': 9,
                    'content_type': 'tutorial',
                    'embedding': [0.1] * 384,
                    'has_analysis': True,
                    'analysis_boost': 0.1
                },
                {
                    'id': 2,
                    'title': 'JavaScript React Tutorial for Beginners',
                    'extracted_text': 'Learn React JavaScript framework for frontend development',
                    'technologies': ['JavaScript', 'React', 'Frontend'],
                    'quality_score': 8,
                    'content_type': 'tutorial',
                    'embedding': [0.2] * 384,
                    'has_analysis': True,
                    'analysis_boost': 0.0
                },
                {
                    'id': 3,
                    'title': 'Reddit - The heart of the internet',
                    'extracted_text': 'Reddit is a social media platform',
                    'technologies': ['social media'],
                    'quality_score': 3,
                    'content_type': 'social',
                    'embedding': [0.3] * 384,
                    'has_analysis': False,
                    'analysis_boost': 0.0
                },
                {
                    'id': 4,
                    'title': 'Go Programming Language Official Documentation',
                    'extracted_text': 'Official Go language documentation and tutorials',
                    'technologies': ['Go', 'Programming'],
                    'quality_score': 10,
                    'content_type': 'documentation',
                    'embedding': [0.4] * 384,
                    'has_analysis': True,
                    'analysis_boost': 0.2
                },
                {
                    'id': 5,
                    'title': 'Google Forms - Create surveys',
                    'extracted_text': 'Create online forms and surveys',
                    'technologies': ['forms', 'surveys'],
                    'quality_score': 2,
                    'content_type': 'tool',
                    'embedding': [0.5] * 384,
                    'has_analysis': False,
                    'analysis_boost': 0.0
                }
            ]

            print(f"Testing with {len(content_list)} mock content items:")
            for item in content_list:
                print(f"  - {item['title'][:50]}... (tech: {item['technologies']}, quality: {item['quality_score']})")
            print()

            # Test context extraction
            context_engine = ContextAwareEngine(orchestrator.data_layer)
            context = context_engine._extract_context(request)

            print("Context analysis:")
            print(f"  Intent goal: {context.get('intent_goal')}")
            print(f"  Technologies: {context.get('technologies')}")
            print()

            # Get recommendations using the context-aware engine
            recommendations = context_engine.get_recommendations(content_list, request)

            # Generate context summaries
            recommendations = orchestrator.generate_context_summaries(recommendations, request, 8)

            result = recommendations

            print("🎯 GO LANG RECOMMENDATIONS TEST")
            print("=" * 50)
            print(f"Request: {request.title}")
            print(f"Technologies: {request.technologies}")
            print()

            # Convert to dict format for display
            from dataclasses import asdict
            recommendations_dict = [asdict(rec) for rec in result]

            print(f"📊 GOT {len(recommendations_dict)} RECOMMENDATIONS:")
            print()

            go_related_count = 0
            js_related_count = 0

            for i, rec in enumerate(recommendations_dict, 1):
                title = rec.get('title', 'Unknown')
                technologies = rec.get('technologies', [])
                score = rec.get('score', 0)
                ml_enhanced = rec.get('metadata', {}).get('ml_enhanced', False)
                context_summary = rec.get('context_summary', '')

                # Count Go vs JS content
                tech_str = ' '.join(technologies).lower() if technologies else ''
                if 'go' in tech_str or 'golang' in tech_str:
                    go_related_count += 1
                if 'javascript' in tech_str or 'js' in tech_str or 'react' in tech_str:
                    js_related_count += 1

                print(f"{i}. {title[:60]}...")
                print(f"   Technologies: {technologies}")
                print(f"   Score: {score}")
                print(f"   ML Enhanced: {ml_enhanced}")
                if context_summary:
                    print(f"   Context Summary: {context_summary[:100]}...")
                print()

            print("📈 ANALYSIS:")
            print(f"   ✅ Go-related recommendations: {go_related_count}")
            print(f"   ❌ JS/React recommendations: {js_related_count}")
            print()

            if go_related_count > 0 and js_related_count == 0:
                print("🎉 SUCCESS: Recommendations are now relevant!")
                print("   - Go content prioritized")
                print("   - No irrelevant JS/React content")
            elif go_related_count == 0:
                print("❌ ISSUE: No Go-related content found")
            else:
                print("⚠️  PARTIAL: Some Go content, but still showing JS/React")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_go_recommendations()
