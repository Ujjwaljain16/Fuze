#!/usr/bin/env python3
"""
Debug script to check analysis status for user bookmarks
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def debug_analysis_status():
    """Debug analysis status"""
    try:
        import flask
        from models import db, SavedContent, ContentAnalysis

        # Setup Flask context (use same config as main app)
        from config import DevelopmentConfig
        app = flask.Flask(__name__)
        app.config.from_object(DevelopmentConfig)

        db.init_app(app)

        with app.app_context():
            user_id = 8

            print("🔍 DEBUG: Analysis Status for User", user_id)
            print("=" * 50)

            # Get all user's saved content
            all_content = SavedContent.query.filter_by(user_id=user_id).all()
            total_content = len(all_content)
            print(f"Total saved content: {total_content}")

            # Get analyzed content
            analyzed_ids = db.session.query(ContentAnalysis.content_id).all()
            analyzed_ids = {row[0] for row in analyzed_ids}
            analyzed_content = [c for c in all_content if c.id in analyzed_ids]
            analyzed_count = len(analyzed_content)
            print(f"Analyzed content: {analyzed_count}")

            # Get unanalyzed content
            unanalyzed_content = [c for c in all_content if c.id not in analyzed_ids]
            unanalyzed_count = len(unanalyzed_content)
            print(f"Unanalyzed content: {unanalyzed_count}")

            print("\n" + "=" * 30)
            print("UNANALYZED CONTENT BREAKDOWN:")
            print("=" * 30)

            low_quality = 0
            empty_content = 0
            other = 0

            for content in unanalyzed_content:
                if content.quality_score < 5:
                    low_quality += 1
                    print(f"Low quality (score {content.quality_score}): {content.title[:50]}...")
                elif not content.extracted_text or not content.extracted_text.strip():
                    empty_content += 1
                    print(f"Empty content: {content.title[:50]}...")
                else:
                    other += 1
                    print(f"Other reason: {content.title[:50]}...")

            print("\nBREAKDOWN SUMMARY:")
            print(f"Low quality (score < 5): {low_quality}")
            print(f"Empty content: {empty_content}")
            print(f"Other: {other}")
            print(f"Total unanalyzed: {low_quality + empty_content + other}")

            print("\nSAMPLE UNANALYZED CONTENT:")
            for i, content in enumerate(unanalyzed_content[:5]):
                print(f"{i+1}. {content.title}")
                print(f"   URL: {content.url}")
                print(f"   Quality Score: {content.quality_score}")
                content_length = len((content.extracted_text or "").strip())
                print(f"   Content Length: {content_length}")
                print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_analysis_status()
