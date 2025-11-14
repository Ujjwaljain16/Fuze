#!/usr/bin/env python3
"""
Cleanup Test Data
Remove test bookmarks and improve recommendation diversity
"""
from app import app, db
from models import SavedContent

def cleanup_test_data():
    """Clean up test data and improve recommendations"""
    print("🧹 Cleaning Up Test Data")
    print("=" * 30)
    
    with app.app_context():
        # Find and remove test bookmarks
        test_bookmarks = SavedContent.query.filter(
            SavedContent.title.like('%Test Bookmark%') |
            SavedContent.title.like('%test bookmark%')
        ).all()
        
        print(f"Found {len(test_bookmarks)} test bookmarks:")
        for bookmark in test_bookmarks:
            print(f"   - {bookmark.title} (ID: {bookmark.id})")
        
        if test_bookmarks:
            # Delete test bookmarks
            for bookmark in test_bookmarks:
                db.session.delete(bookmark)
            
            db.session.commit()
            print(f"✅ Deleted {len(test_bookmarks)} test bookmarks")
        else:
            print("✅ No test bookmarks found")
        
        # Check content diversity
        print("\n📊 Content Diversity Analysis:")
        print("-" * 30)
        
        all_content = SavedContent.query.all()
        print(f"Total content: {len(all_content)}")
        
        # Check quality distribution
        quality_scores = [c.quality_score for c in all_content if c.quality_score]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            print(f"Average quality score: {avg_quality:.2f}")
            
            high_quality = [s for s in quality_scores if s >= 8]
            print(f"High quality content (≥8): {len(high_quality)}")
            
            medium_quality = [s for s in quality_scores if 5 <= s < 8]
            print(f"Medium quality content (5-7): {len(medium_quality)}")
        
        # Check embedding coverage
        with_embeddings = [c for c in all_content if c.embedding is not None]
        print(f"Content with embeddings: {len(with_embeddings)}/{len(all_content)}")
        
        # Check content types
        print("\n📚 Content Types:")
        print("-" * 15)
        
        # Analyze titles for content types
        tutorials = [c for c in all_content if any(word in c.title.lower() for word in ['tutorial', 'guide', 'learn'])]
        docs = [c for c in all_content if any(word in c.title.lower() for word in ['docs', 'documentation', 'api'])]
        projects = [c for c in all_content if any(word in c.title.lower() for word in ['project', 'github', 'repo'])]
        leetcode = [c for c in all_content if 'leetcode' in c.title.lower()]
        
        print(f"Tutorials/Guides: {len(tutorials)}")
        print(f"Documentation: {len(docs)}")
        print(f"Projects: {len(projects)}")
        print(f"LeetCode: {len(leetcode)}")
        
        # Show sample of high-quality content
        print("\n🏆 High-Quality Content Sample:")
        print("-" * 30)
        
        high_quality_content = SavedContent.query.filter(
            SavedContent.quality_score >= 8
        ).order_by(SavedContent.quality_score.desc()).limit(5).all()
        
        for i, content in enumerate(high_quality_content, 1):
            print(f"{i}. {content.title}")
            print(f"   Quality: {content.quality_score}, Has Embedding: {content.embedding is not None}")
        
        print("\n" + "=" * 30)
        print("✅ Cleanup Complete!")
        print("=" * 30)

if __name__ == "__main__":
    cleanup_test_data() 