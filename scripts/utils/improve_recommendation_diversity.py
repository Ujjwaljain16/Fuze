#!/usr/bin/env python3
"""
Improve Recommendation Diversity
Implement better algorithms to ensure diverse recommendations
"""
from app import app, db
from models import SavedContent
from sqlalchemy import text
import random

def improve_recommendation_diversity():
    """Improve recommendation diversity"""
    print("🎯 Improving Recommendation Diversity")
    print("=" * 40)
    
    with app.app_context():
        # Get all high-quality content
        all_content = SavedContent.query.filter(
            SavedContent.quality_score >= 7,
            SavedContent.title.notlike('%Test Bookmark%'),
            SavedContent.title.notlike('%test bookmark%')
        ).all()
        
        print(f"Total eligible content: {len(all_content)}")
        
        # Analyze content types for diversity
        content_types = {}
        for content in all_content:
            title_lower = content.title.lower()
            
            # Categorize content
            if any(word in title_lower for word in ['tutorial', 'guide', 'learn']):
                content_types.setdefault('tutorials', []).append(content.id)
            elif any(word in title_lower for word in ['docs', 'documentation', 'api']):
                content_types.setdefault('documentation', []).append(content.id)
            elif any(word in title_lower for word in ['project', 'github', 'repo']):
                content_types.setdefault('projects', []).append(content.id)
            elif 'leetcode' in title_lower:
                content_types.setdefault('leetcode', []).append(content.id)
            elif any(word in title_lower for word in ['interview', 'question']):
                content_types.setdefault('interviews', []).append(content.id)
            else:
                content_types.setdefault('other', []).append(content.id)
        
        print("\n📊 Content Type Distribution:")
        for content_type, items in content_types.items():
            print(f"   {content_type.capitalize()}: {len(items)} items")
        
        # Create diverse recommendation query
        diverse_query = """
        WITH content_categories AS (
            SELECT 
                id,
                extracted_text,
                quality_score,
                user_id,
                CASE 
                    WHEN LOWER(title) LIKE '%tutorial%' OR LOWER(title) LIKE '%guide%' OR LOWER(title) LIKE '%learn%' THEN 'tutorials'
                    WHEN LOWER(title) LIKE '%docs%' OR LOWER(title) LIKE '%documentation%' OR LOWER(title) LIKE '%api%' THEN 'documentation'
                    WHEN LOWER(title) LIKE '%project%' OR LOWER(title) LIKE '%github%' OR LOWER(title) LIKE '%repo%' THEN 'projects'
                    WHEN LOWER(title) LIKE '%leetcode%' THEN 'leetcode'
                    WHEN LOWER(title) LIKE '%interview%' OR LOWER(title) LIKE '%question%' THEN 'interviews'
                    ELSE 'other'
                END as category
            FROM saved_content 
            WHERE user_id != :user_id
            AND quality_score >= 7
            AND title NOT LIKE '%Test Bookmark%'
            AND title NOT LIKE '%test bookmark%'
        ),
        ranked_content AS (
            SELECT 
                *,
                ROW_NUMBER() OVER (PARTITION BY category ORDER BY quality_score DESC, RANDOM()) as rank_in_category
            FROM content_categories
        )
        SELECT id, extracted_text, quality_score, user_id, category
        FROM ranked_content 
        WHERE rank_in_category <= 2
        ORDER BY RANDOM()
        LIMIT 10
        """
        
        print("\n🔍 Testing Diverse Recommendations:")
        print("-" * 35)
        
        # Test with different user IDs
        for user_id in [1, 2]:
            print(f"\n👤 User {user_id}:")
            
            try:
                result = db.session.execute(text(diverse_query), {'user_id': user_id}).fetchall()
                
                if result:
                    print(f"   Got {len(result)} diverse recommendations:")
                    
                    # Group by category
                    by_category = {}
                    for row in result:
                        category = row[4]  # category column
                        by_category.setdefault(category, []).append(row)
                    
                    for category, items in by_category.items():
                        print(f"     {category.capitalize()}: {len(items)} items")
                        for item in items:
                            title = item[1][:50] + "..." if item[1] else "No title"
                            print(f"       - {title} (Quality: {item[2]})")
                else:
                    print("   No recommendations found")
                    
            except Exception as e:
                print(f"   Error: {e}")
        
        print("\n" + "=" * 40)
        print("✅ Diversity Analysis Complete!")
        print("=" * 40)

if __name__ == "__main__":
    improve_recommendation_diversity() 