#!/usr/bin/env python3
"""
Check complete database content without any limits
"""

import os
import sys
from collections import Counter

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_complete_database():
    """Check ALL content in the database without limits"""
    try:
        from app import app
        
        with app.app_context():
            from models import SavedContent, ContentAnalysis
            
            print("🔍 Checking COMPLETE database content...")
            print("=" * 60)
            
            # Get ALL content (no limits!)
            all_content = SavedContent.query.all()
            print(f"📊 TOTAL CONTENT IN DATABASE: {len(all_content)} items")
            
            # Get content with analysis
            content_with_analysis = SavedContent.query.join(ContentAnalysis).all()
            print(f"📊 CONTENT WITH ANALYSIS: {len(content_with_analysis)} items")
            
            # Get content without analysis
            content_without_analysis = len(all_content) - len(content_with_analysis)
            print(f"📊 CONTENT WITHOUT ANALYSIS: {content_without_analysis} items")
            
            # Calculate analysis coverage
            if len(all_content) > 0:
                coverage = (len(content_with_analysis) / len(all_content)) * 100
                print(f"📊 ANALYSIS COVERAGE: {coverage:.1f}%")
            else:
                print("📊 No content in database yet")
            
            print("\n" + "=" * 60)
            print("👥 CONTENT DISTRIBUTION BY USER:")
            
            # Group by user
            user_content = {}
            for content in all_content:
                user_id = content.user_id
                if user_id not in user_content:
                    user_content[user_id] = {
                        'total': 0,
                        'with_analysis': 0,
                        'without_analysis': 0,
                        'quality_scores': [],
                        'titles': []
                    }
                
                user_content[user_id]['total'] += 1
                user_content[user_id]['quality_scores'].append(content.quality_score or 0)
                user_content[user_id]['titles'].append(content.title[:50] + "..." if len(content.title) > 50 else content.title)
                
                # Check if has analysis
                if content.analyses and len(content.analyses) > 0:
                    user_content[user_id]['with_analysis'] += 1
                else:
                    user_content[user_id]['without_analysis'] += 1
            
            # Display user distribution
            for user_id, data in user_content.items():
                print(f"\n👤 User {user_id}:")
                print(f"   📚 Total content: {data['total']}")
                print(f"   ✅ With analysis: {data['with_analysis']}")
                print(f"   ⏳ Without analysis: {data['without_analysis']}")
                print(f"   📊 Average quality: {sum(data['quality_scores']) / len(data['quality_scores']):.1f}")
                
                # Show sample titles
                print(f"   📝 Sample titles:")
                for i, title in enumerate(data['titles'][:3], 1):
                    print(f"      {i}. {title}")
                if len(data['titles']) > 3:
                    print(f"      ... and {len(data['titles']) - 3} more")
            
            print("\n" + "=" * 60)
            print("🔍 CONTENT QUALITY DISTRIBUTION:")
            
            # Quality score distribution
            quality_scores = [content.quality_score or 0 for content in all_content]
            quality_counter = Counter(quality_scores)
            
            for score in sorted(quality_counter.keys()):
                count = quality_counter[score]
                percentage = (count / len(all_content)) * 100
                print(f"   Quality {score}: {count} items ({percentage:.1f}%)")
            
            print("\n" + "=" * 60)
            print("📊 RECOMMENDATION SYSTEM READINESS:")
            
            # Check if we have enough analyzed content for recommendations
            if len(content_with_analysis) >= 10:
                print(f"   ✅ Ready for recommendations: {len(content_with_analysis)} analyzed items")
            elif len(content_with_analysis) >= 5:
                print(f"   ⚠️  Limited recommendations: {len(content_with_analysis)} analyzed items")
            else:
                print(f"   ❌ Not ready for recommendations: {len(content_with_analysis)} analyzed items")
            
            # Check analysis coverage
            if coverage >= 80:
                print(f"   ✅ Excellent analysis coverage: {coverage:.1f}%")
            elif coverage >= 50:
                print(f"   ⚠️  Good analysis coverage: {coverage:.1f}%")
            else:
                print(f"   ❌ Low analysis coverage: {coverage:.1f}%")
            
            print("\n" + "=" * 60)
            print("🚀 NEXT STEPS:")
            
            if content_without_analysis > 0:
                print(f"   📝 {content_without_analysis} items need analysis")
                print("   🔄 Background Analysis Service will process them automatically")
                print("   ⏱️  Processing happens every 30 seconds")
            else:
                print("   🎉 All content is already analyzed!")
            
            print("   💡 Run 'python run_production.py' to start automatic processing")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_complete_database()
    if success:
        print("\n✅ Complete database check completed!")
    else:
        print("\n💥 Database check failed!")
