#!/usr/bin/env python3
"""
Debug script to see why DSA visualizer request isn't getting the right recommendations
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_recommendation_matching():
    """Debug why DSA visualizer request isn't getting the right recommendations"""
    try:
        from app import app
        
        with app.app_context():
            from models import SavedContent, ContentAnalysis, db
            
            print("🔍 Debugging DSA Visualizer Recommendation Matching...")
            print("=" * 60)
            
            # Your request
            request_title = "DSA visualiser"
            request_technologies = "java instrumentation byte buddy AST JVM"
            
            print(f"🎯 Your Request:")
            print(f"   Title: {request_title}")
            print(f"   Technologies: {request_technologies}")
            print()
            
            # Find all bookmarks that should match
            print("🔍 Searching for relevant bookmarks...")
            
            # Search for DSA/visualizer related content
            dsa_content = SavedContent.query.filter(
                SavedContent.title.ilike('%DSA%') |
                SavedContent.title.ilike('%visualizer%') |
                SavedContent.title.ilike('%visualiser%') |
                SavedContent.title.ilike('%data structure%') |
                SavedContent.title.ilike('%algorithm%')
            ).all()
            
            print(f"📊 Found {len(dsa_content)} DSA/visualizer related bookmarks:")
            for content in dsa_content:
                print(f"   - ID {content.id}: {content.title}")
                print(f"     Quality: {content.quality_score}, User: {content.user_id}")
                if content.analyses:
                    analysis = content.analyses[0]
                    if analysis.technology_tags:
                        print(f"     Tech: {analysis.technology_tags}")
                print()
            
            # Search for Java/bytecode related content
            java_content = SavedContent.query.filter(
                SavedContent.title.ilike('%java%') |
                SavedContent.title.ilike('%bytecode%') |
                SavedContent.title.ilike('%byte buddy%') |
                SavedContent.title.ilike('%instrumentation%') |
                SavedContent.title.ilike('%AST%') |
                SavedContent.title.ilike('%JVM%')
            ).all()
            
            print(f"📊 Found {len(java_content)} Java/bytecode related bookmarks:")
            for content in java_content:
                print(f"   - ID {content.id}: {content.title}")
                print(f"     Quality: {content.quality_score}, User: {content.user_id}")
                if content.analyses:
                    analysis = content.analyses[0]
                    if analysis.technology_tags:
                        print(f"     Tech: {analysis.technology_tags}")
                print()
            
            # Check what the recommendation engine is actually seeing
            print("🔍 Checking what recommendation engine sees...")
            
            # Get all content for user 1 (your content)
            user_content = SavedContent.query.filter_by(user_id=1).all()
            print(f"📊 Total user content: {len(user_content)}")
            
            # Check for specific keywords in your content
            keywords = ['DSA', 'visualizer', 'visualiser', 'java', 'bytecode', 'byte buddy', 'AST', 'JVM', 'instrumentation']
            matching_content = []
            
            for content in user_content:
                title_lower = content.title.lower()
                text_lower = (content.extracted_text or '').lower()
                
                matches = []
                for keyword in keywords:
                    if keyword.lower() in title_lower or keyword.lower() in text_lower:
                        matches.append(keyword)
                
                if matches:
                    matching_content.append((content, matches))
            
            print(f"📊 Found {len(matching_content)} content items with relevant keywords:")
            for content, matches in matching_content:
                print(f"   - ID {content.id}: {content.title}")
                print(f"     Matches: {', '.join(matches)}")
                print(f"     Quality: {content.quality_score}")
                if content.analyses:
                    analysis = content.analyses[0]
                    if analysis.technology_tags:
                        print(f"     Tech: {analysis.technology_tags}")
                print()
            
            # Check if these are being filtered out
            print("🔍 Checking if relevant content is being filtered out...")
            
            # Test the exact query the orchestrator uses
            from sqlalchemy import select
            query = db.session.query(SavedContent, ContentAnalysis).outerjoin(
                ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
            )
            
            # Apply the same filters that were in the orchestrator (but with our fixes)
            query = query.filter(
                SavedContent.user_id == 1,
                SavedContent.quality_score >= 1,  # Fixed: was get_threshold('quality_user_content')
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != '',
                SavedContent.title.isnot(None),
                SavedContent.title != ''
            )
            
            # No more restrictive filters! (removed test bookmark, dictionary, etc. filters)
            
            # Increased limit to 1000
            user_content = query.order_by(
                SavedContent.quality_score.desc(),
                SavedContent.saved_at.desc()
            ).limit(1000).all()
            
            print(f"📊 Content retrieved with fixed query: {len(user_content)}")
            
            # Check if our matching content is in the results
            matching_ids = [content.id for content, _ in matching_content]
            retrieved_ids = [content.id for content, _ in user_content]
            
            missing_matches = [cid for cid in matching_ids if cid not in retrieved_ids]
            if missing_matches:
                print(f"⚠️  Missing matching content IDs: {missing_matches}")
            else:
                print("✅ All matching content is being retrieved")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_recommendation_matching()
    if success:
        print("\n✅ Debug completed!")
    else:
        print("\n💥 Debug failed!")
