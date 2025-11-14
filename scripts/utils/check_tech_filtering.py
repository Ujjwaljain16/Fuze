#!/usr/bin/env python3
"""
Check why technology filtering is so aggressive
"""

from app import app
from models import SavedContent, ContentAnalysis

def check_tech_filtering():
    with app.app_context():
        print("🔍 Checking technology filtering issue...")
        
        # Get sample content
        content = SavedContent.query.join(ContentAnalysis).filter(
            SavedContent.user_id == 1
        ).limit(10).all()
        
        print(f"📊 Found {len(content)} content items")
        
        # Check technologies
        for i, c in enumerate(content):
            tech_tags = c.analyses[0].technology_tags if c.analyses else "None"
            print(f"{i+1}. Title: {c.title[:60]}...")
            print(f"   Tech: {tech_tags}")
            print(f"   Quality: {c.quality_score}")
            print()
        
        # Check what technologies are being requested
        print("🎯 What technologies are being requested?")
        print("From your test: 'react,python,ai,machine learning,cloud,devops'")
        
        # Test the filtering logic
        request_techs = ['react', 'python', 'ai', 'machine learning', 'cloud', 'devops']
        print(f"\n🔧 Testing filtering with: {request_techs}")
        
        relevant_count = 0
        for c in content:
            if c.analyses:
                content_techs = c.analyses[0].technology_tags
                if content_techs:
                    tech_list = [tech.strip().lower() for tech in content_techs.split(',') if tech.strip()]
                    
                    # Calculate relevance score (same logic as orchestrator)
                    relevance_score = 0.0
                    
                    # Exact matches
                    exact_matches = set(request_techs).intersection(set(tech_list))
                    relevance_score += len(exact_matches) * 0.4
                    
                    # Partial matches
                    for req_tech in request_techs:
                        for content_tech in tech_list:
                            if req_tech in content_tech or content_tech in req_tech:
                                relevance_score += 0.2
                    
                    # Text mentions
                    content_text = f"{c.title} {c.extracted_text or ''}".lower()
                    for tech in request_techs:
                        if tech in content_text:
                            relevance_score += 0.3
                    
                    if relevance_score >= 0.3:
                        relevant_count += 1
                        print(f"✅ Relevant: {c.title[:50]}... (score: {relevance_score:.2f})")
                    else:
                        print(f"❌ Filtered: {c.title[:50]}... (score: {relevance_score:.2f})")
        
        print(f"\n📊 Filtering result: {len(content)} → {relevant_count} relevant items")
        print(f"🔍 Threshold: 0.3 (this might be too high!)")

if __name__ == "__main__":
    check_tech_filtering()
