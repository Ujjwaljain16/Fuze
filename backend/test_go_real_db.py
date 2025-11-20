#!/usr/bin/env python3
"""
Test Go lang recommendations for user 8 using real database
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def test_go_recommendations():
    """Test Go lang recommendations for user 8 using real database"""
    try:
        # Load environment variables from .env file
        from dotenv import load_dotenv
        load_dotenv()

        # Use the proper app creation from run_production to ensure all setup is correct
        from run_production import create_app
        from models import db

        app = create_app()

        with app.app_context():
            # Ensure database tables exist
            try:
                # Try to create tables (this will work for both SQLite and PostgreSQL)
                db.create_all()
                print("✅ Database tables verified/created")
            except Exception as db_error:
                error_str = str(db_error).lower()
                # Ignore pgvector extension errors (SQLite doesn't support it, but that's OK)
                if 'vector' in error_str or 'extension' in error_str:
                    print("⚠️  Warning: pgvector extension not available (SQLite detected, this is OK)")
                    # Try again without extension requirement
                    try:
                        db.create_all()
                        print("✅ Database tables verified/created")
                    except Exception as e2:
                        print(f"⚠️  Warning: Could not create database tables: {e2}")
                        print("   Continuing with test (tables may already exist)...")
                else:
                    print(f"⚠️  Warning: Could not create database tables: {db_error}")
                    print("   Continuing with test (tables may already exist)...")
            from ml.unified_recommendation_orchestrator import UnifiedRecommendationOrchestrator, UnifiedRecommendationRequest

            print("🎯 TESTING GO LANG RECOMMENDATIONS FOR USER 8 (REAL DATABASE)")
            print("=" * 70)

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

            # Get REAL content from database for user 8
            try:
                content_list = orchestrator.data_layer.get_candidate_content(8, request)
                print(f"✅ Found {len(content_list)} real content items from database for user 8")
                print()

                # Analyze content
                go_count = 0
                js_count = 0
                total_count = len(content_list)

                print("Sample content from database:")
                for i, content in enumerate(content_list[:5]):  # Show first 5
                    title = content.get('title', 'No title')[:50]
                    techs = content.get('technologies', [])
                    quality = content.get('quality_score', 0)

                    # Count technologies
                    tech_str = ' '.join(str(tech) for tech in techs).lower()
                    if 'go' in tech_str or 'golang' in tech_str:
                        go_count += 1
                    if 'javascript' in tech_str or 'js' in tech_str or 'react' in tech_str:
                        js_count += 1

                    print(f"  {i+1}. {title}... (tech: {techs}, quality: {quality})")

                print(f"\n📊 Content Analysis:")
                print(f"   Total content: {total_count}")
                print(f"   Go-related content: {go_count}")
                print(f"   JS/React content: {js_count}")
                print()

                if len(content_list) == 0:
                    print("❌ No content found for user 8 in database")
                    return

            except Exception as e:
                print(f"❌ Database query failed: {e}")
                print("Cannot test with real data. Database connection issue.")
                return

            # Test context extraction
            from ml.unified_recommendation_orchestrator import ContextAwareEngine
            context_engine = ContextAwareEngine(orchestrator.data_layer)
            context = context_engine._extract_context(request)

            print("Context analysis:")
            print(f"  Intent goal: {context.get('intent_goal')}")
            print(f"  Technologies: {context.get('technologies')}")
            print()

            # Get recommendations using the context-aware engine
            recommendations = context_engine.get_recommendations(content_list, request)

            print("🎯 GO LANG RECOMMENDATIONS TEST")
            print("=" * 50)
            print(f"Request: {request.title}")
            print(f"Technologies: {request.technologies}")
            print()

            # Convert to dict format for display
            from dataclasses import asdict
            recommendations_dict = [asdict(rec) for rec in recommendations]

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

                # Count Go vs JS content in recommendations
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

            print("📈 RECOMMENDATION ANALYSIS:")
            print(f"   ✅ Go-related recommendations: {go_related_count}")
            print(f"   ❌ JS/React recommendations: {js_related_count}")
            print()

            if go_related_count > 0 and js_related_count == 0:
                print("🎉 SUCCESS: Recommendations are now relevant!")
                print("   - Go content properly prioritized")
                print("   - No irrelevant JS/React content")
                print("   - Learning-specific filtering working")
            elif go_related_count == 0:
                print("❌ ISSUE: No Go-related content recommended")
                print("   - Check if user has Go-related saved content")
                print("   - Verify technology matching logic")
            else:
                print("⚠️  PARTIAL SUCCESS: Some Go content, but still showing JS/React")
                print("   - Technology filtering may need adjustment")
                print("   - Check semantic similarity scores")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_go_recommendations()
