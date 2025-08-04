#!/usr/bin/env python3
"""
Debug script to check candidate content retrieval
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, SavedContent, ContentAnalysis

def debug_candidate_content():
    """Debug the candidate content retrieval"""
    print("🔍 Debugging Candidate Content Retrieval")
    print("=" * 50)
    
    try:
        with app.app_context():
            # Check total content
            total_content = db.session.query(SavedContent).count()
            print(f"📊 Total SavedContent: {total_content}")
            
            # Check content with analysis
            content_with_analysis = db.session.query(SavedContent, ContentAnalysis).join(
                ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
            ).count()
            print(f"📊 Content with Analysis: {content_with_analysis}")
            
            # Check quality scores
            high_quality = db.session.query(SavedContent).filter(
                SavedContent.quality_score >= 5
            ).count()
            print(f"📊 High Quality Content (>=5): {high_quality}")
            
            # Check some sample content
            sample_content = db.session.query(SavedContent).limit(5).all()
            print(f"\n📝 Sample Content:")
            for i, content in enumerate(sample_content, 1):
                print(f"  {i}. {content.title}")
                print(f"     Quality Score: {content.quality_score}")
                print(f"     URL: {content.url}")
                print(f"     Has Analysis: {bool(db.session.query(ContentAnalysis).filter_by(content_id=content.id).first())}")
            
            # Test the base query
            base_query = db.session.query(SavedContent, ContentAnalysis).join(
                ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
            ).filter(
                SavedContent.quality_score >= 5,
                SavedContent.title.notlike('%Test%'),
                SavedContent.title.notlike('%test%')
            )
            
            base_count = base_query.count()
            print(f"\n🔍 Base Query Count: {base_count}")
            
            if base_count > 0:
                # Get some candidates
                candidates = base_query.limit(3).all()
                print(f"📋 Sample Candidates:")
                for i, (content, analysis) in enumerate(candidates, 1):
                    print(f"  {i}. {content.title}")
                    print(f"     Quality: {content.quality_score}")
                    print(f"     Tech Tags: {analysis.technology_tags}")
            else:
                print("❌ No candidates found in base query!")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_candidate_content() 