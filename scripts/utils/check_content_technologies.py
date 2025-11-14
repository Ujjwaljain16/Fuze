#!/usr/bin/env python3
"""
Quick script to check what technologies are actually in your saved content
"""

import os
import sys
from collections import Counter

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_content_technologies():
    """Check what technologies are actually in your saved content"""
    try:
        from app import app
        
        with app.app_context():
            from models import SavedContent, ContentAnalysis
            
            print("🔍 Checking your saved content technologies...")
            
            # Get ALL content with analysis (no limit!)
            content_items = SavedContent.query.join(ContentAnalysis).filter(
                SavedContent.quality_score >= 5
            ).all()  # Removed limit(100) to get ALL content
            
            print(f"📊 Found {len(content_items)} content items (ALL content in database)")
            
            # Group by user to see distribution
            user_content_count = {}
            for content in content_items:
                user_id = content.user_id
                user_content_count[user_id] = user_content_count.get(user_id, 0) + 1
            
            print(f"👥 Content distribution by user:")
            for user_id, count in user_content_count.items():
                print(f"   User {user_id}: {count} items")
            
            # Collect all technologies
            all_technologies = []
            content_samples = []
            
            for content in content_items:
                # Get technologies from analyses (note: it's 'analyses' not 'analysis')
                analyses = content.analyses
                if analyses and len(analyses) > 0:
                    analysis = analyses[0]  # Get the first analysis
                    if analysis.technology_tags:
                        techs = [tech.strip().lower() for tech in analysis.technology_tags.split(',') if tech.strip()]
                        all_technologies.extend(techs)
                        
                        # Sample some content
                        if len(content_samples) < 5:
                            content_samples.append({
                                'title': content.title,
                                'technologies': techs,
                                'quality': content.quality_score,
                                'user_id': content.user_id
                            })
            
            # Count technology frequency
            tech_counter = Counter(all_technologies)
            
            print(f"\n🏆 Top 20 Technologies in Your Content:")
            for tech, count in tech_counter.most_common(20):
                print(f"   {tech}: {count} times")
            
            print(f"\n📝 Sample Content Items:")
            for i, sample in enumerate(content_samples, 1):
                print(f"\n{i}. {sample['title']}")
                print(f"   Technologies: {', '.join(sample['technologies'][:5])}")
                print(f"   Quality Score: {sample['quality']}")
                print(f"   User ID: {sample['user_id']}")
            
            # Check for your specific techs
            your_techs = ['java', 'jvm', 'bytecode', 'ast', 'instrumentation', 'byte buddy']
            print(f"\n🎯 Your Requested Technologies:")
            for tech in your_techs:
                count = tech_counter.get(tech, 0)
                if count > 0:
                    print(f"   ✅ {tech}: {count} times")
                else:
                    print(f"   ❌ {tech}: Not found")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_content_technologies()
    if success:
        print("\n✅ Content analysis complete!")
    else:
        print("\n💥 Analysis failed!")
