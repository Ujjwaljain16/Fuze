#!/usr/bin/env python3
"""
Debug Recommendations
See what content is available and why recommendations are failing
"""
from app import app, db
from models import SavedContent, User
from sqlalchemy import text

def debug_recommendations():
    """Debug why recommendations are failing"""
    print("🔍 Debugging Recommendations")
    print("=" * 40)
    
    with app.app_context():
        user_id = 1  # ujjwaljain16
        
        print(f"👤 User ID: {user_id}")
        
        # Check total content
        total_content = SavedContent.query.count()
        print(f"📚 Total content in database: {total_content}")
        
        # Check user's content
        user_content = SavedContent.query.filter_by(user_id=user_id).count()
        print(f"👤 User's content: {user_content}")
        
        # Check other users' content
        other_content = SavedContent.query.filter(SavedContent.user_id != user_id).count()
        print(f"👥 Other users' content: {other_content}")
        
        # Check high-quality content
        high_quality = SavedContent.query.filter(SavedContent.quality_score >= 7).count()
        print(f"⭐ High-quality content (≥7): {high_quality}")
        
        # Check content for recommendations (excluding user's own content)
        eligible_content = SavedContent.query.filter(
            SavedContent.user_id != user_id,
            SavedContent.quality_score >= 7
        ).count()
        print(f"🎯 Eligible for recommendations: {eligible_content}")
        
        # Test the actual query
        print("\n🔍 Testing Ultra-Fast Query:")
        print("-" * 30)
        
        try:
            query = """
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
            LIMIT 15
            """
            
            result = db.session.execute(text(query), {'user_id': user_id}).fetchall()
            print(f"✅ Query returned {len(result)} results")
            
            if result:
                print("   Sample results:")
                for i, row in enumerate(result[:3]):
                    print(f"     {i+1}. ID: {row[0]}, Quality: {row[2]}, Category: {row[4]}")
            else:
                print("   ❌ No results from query")
                
        except Exception as e:
            print(f"❌ Query error: {e}")
        
        # Show some sample content
        print("\n📚 Sample Content:")
        print("-" * 20)
        
        sample_content = SavedContent.query.limit(5).all()
        for i, content in enumerate(sample_content):
            print(f"{i+1}. ID: {content.id}, User: {content.user_id}, Quality: {content.quality_score}")
            print(f"   Title: {content.title[:50]}...")
            print(f"   Has Embedding: {content.embedding is not None}")
        
        print("\n" + "=" * 40)
        print("🔍 Debug Complete!")
        print("=" * 40)

if __name__ == "__main__":
    debug_recommendations() 