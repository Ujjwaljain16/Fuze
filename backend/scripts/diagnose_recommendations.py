#!/usr/bin/env python3
"""
Diagnose recommendation system issues
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def diagnose_recommendations():
    """Diagnose recommendation system issues"""
    try:
        import flask
        from models import db, SavedContent, ContentAnalysis

        # Setup Flask context
        app = flask.Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/fuze')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(app)

        with app.app_context():
            user_id = 8

            print("🔍 DIAGNOSING RECOMMENDATION SYSTEM")
            print("=" * 50)

            # Check total content vs analyzed content
            total_content = SavedContent.query.filter_by(user_id=user_id).count()
            analyzed_content = db.session.query(ContentAnalysis.content_id).join(
                SavedContent, ContentAnalysis.content_id == SavedContent.id
            ).filter(SavedContent.user_id == user_id).count()

            print(f"Total user content: {total_content}")
            print(f"Analyzed content: {analyzed_content}")
            print(".1f")

            # Check content analysis quality
            analyses = ContentAnalysis.query.join(
                SavedContent, ContentAnalysis.content_id == SavedContent.id
            ).filter(SavedContent.user_id == user_id).limit(5).all()

            print("\n📊 SAMPLE CONTENT ANALYSES:")
            for analysis in analyses:
                content = SavedContent.query.get(analysis.content_id)
                print(f"  Title: {content.title[:50]}...")
                print(f"  Technologies: {analysis.technology_tags}")
                print(f"  Content Type: {analysis.content_type}")
                print(f"  Quality Score: {content.quality_score}")
                print(f"  Relevance Score: {analysis.relevance_score}")
                print()

            # Check for Go-related content
            go_content = SavedContent.query.filter(
                SavedContent.user_id == user_id,
                db.or_(
                    SavedContent.title.ilike('%go%'),
                    SavedContent.title.ilike('%golang%'),
                    SavedContent.extracted_text.ilike('%go lang%'),
                    SavedContent.extracted_text.ilike('%golang%')
                )
            ).all()

            print(f"🔍 GO-RELATED CONTENT FOUND: {len(go_content)}")
            for content in go_content[:3]:
                print(f"  - {content.title[:60]}...")
                analysis = ContentAnalysis.query.filter_by(content_id=content.id).first()
                if analysis:
                    print(f"    Technologies: {analysis.technology_tags}")
                    print(f"    Content Type: {analysis.content_type}")
                print()

            # Check technology distribution
            from sqlalchemy import func
            tech_stats = db.session.query(
                func.unnest(ContentAnalysis.technology_tags).label('tech'),
                func.count().label('count')
            ).join(
                SavedContent, ContentAnalysis.content_id == SavedContent.id
            ).filter(SavedContent.user_id == user_id).group_by('tech').order_by(func.count().desc()).limit(10).all()

            print("🛠️ TOP TECHNOLOGIES IN USER CONTENT:")
            for tech, count in tech_stats:
                print(f"  {tech}: {count} items")

            print("\n" + "=" * 50)
            print("🔧 DIAGNOSIS:")

            issues = []

            if analyzed_content == 0:
                issues.append("❌ No content has been analyzed")
            elif analyzed_content < total_content * 0.5:
                issues.append(f"⚠️ Only {analyzed_content}/{total_content} content analyzed")

            if len(go_content) == 0:
                issues.append("❌ No Go-related content found in database")

            # Check if recommendations are using content analysis
            try:
                from ml.unified_recommendation_orchestrator import UnifiedRecommendationOrchestrator
                print("✅ Recommendation orchestrator imports successfully")
            except Exception as e:
                issues.append(f"❌ Recommendation system import error: {e}")

            if not issues:
                print("✅ Basic diagnosis passed - system appears functional")
                print("💡 Recommendation quality issues may be due to:")
                print("   - Low semantic similarity scores")
                print("   - Content analysis quality")
                print("   - Technology matching algorithms")
                print("   - Insufficient Go-related training data")
            else:
                print("❌ DIAGNOSIS ISSUES FOUND:")
                for issue in issues:
                    print(f"   {issue}")

    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    diagnose_recommendations()

