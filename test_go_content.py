#!/usr/bin/env python3
"""
Test script to check Go content availability
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, SavedContent, ContentAnalysis

def check_go_content():
    """Check what Go-related content is available"""
    print("Checking Go-related content in database...")
    
    with app.app_context():
        # Check for Go content in titles with different quality scores
        go_content_all = SavedContent.query.filter(
            db.or_(
                SavedContent.title.ilike('%go%'),
                SavedContent.title.ilike('%golang%'),
                SavedContent.url.ilike('%go%'),
                SavedContent.url.ilike('%golang%')
            )
        ).all()
        
        print(f"\nFound {len(go_content_all)} total Go-related content items:")
        
        # Group by quality score
        quality_groups = {}
        for content in go_content_all:
            quality = content.quality_score
            if quality not in quality_groups:
                quality_groups[quality] = []
            quality_groups[quality].append(content)
        
        for quality in sorted(quality_groups.keys()):
            print(f"\nQuality Score {quality} ({len(quality_groups[quality])} items):")
            for content in quality_groups[quality][:3]:  # Show first 3
                print(f"  - {content.title}")
                print(f"    URL: {content.url}")
                
                # Check if it has analysis
                analysis = ContentAnalysis.query.filter_by(content_id=content.id).first()
                if analysis:
                    print(f"    Has Analysis: Yes - {analysis.technology_tags}")
                else:
                    print(f"    Has Analysis: No")
        
        # Check what would pass the smart recommendation filters
        print(f"\n" + "="*50)
        print("Content that would pass smart recommendation filters:")
        
        filtered_content = SavedContent.query.filter(
            SavedContent.quality_score >= 7,  # Only high-quality content
            SavedContent.title.notlike('%Test Bookmark%'),  # Exclude test content
            SavedContent.title.notlike('%test bookmark%'),
            SavedContent.title.notlike('%pdf%'),  # Exclude PDF downloads
            SavedContent.title.notlike('%download%'),  # Exclude download sites
            SavedContent.url.notlike('%dbooks.org%'),  # Exclude free book sites
            SavedContent.url.notlike('%pdfdrive.com%'),
            SavedContent.url.notlike('%scribd.com%'),
            db.or_(
                SavedContent.title.ilike('%go%'),
                SavedContent.title.ilike('%golang%'),
                SavedContent.url.ilike('%go%'),
                SavedContent.url.ilike('%golang%')
            )
        ).all()
        
        print(f"Found {len(filtered_content)} Go content items that pass filters:")
        for i, content in enumerate(filtered_content, 1):
            print(f"\n{i}. {content.title}")
            print(f"   URL: {content.url}")
            print(f"   Quality Score: {content.quality_score}")
            
            # Check if it has analysis
            analysis = ContentAnalysis.query.filter_by(content_id=content.id).first()
            if analysis:
                print(f"   Has Analysis: Yes")
                print(f"   Technologies: {analysis.technology_tags}")
                print(f"   Content Type: {analysis.content_type}")
            else:
                print(f"   Has Analysis: No")
        
        # Check for analyzed Go content
        analyzed_go = db.session.query(SavedContent, ContentAnalysis).join(
            ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
        ).filter(
            db.or_(
                ContentAnalysis.technology_tags.ilike('%go%'),
                ContentAnalysis.technology_tags.ilike('%golang%'),
                SavedContent.title.ilike('%go%'),
                SavedContent.title.ilike('%golang%')
            )
        ).all()
        
        print(f"\n" + "="*50)
        print(f"Found {len(analyzed_go)} analyzed Go-related content items:")
        for i, (content, analysis) in enumerate(analyzed_go, 1):
            print(f"\n{i}. {content.title}")
            print(f"   URL: {content.url}")
            print(f"   Quality Score: {content.quality_score}")
            print(f"   Technologies: {analysis.technology_tags}")
            print(f"   Content Type: {analysis.content_type}")

if __name__ == "__main__":
    check_go_content() 