#!/usr/bin/env python3
"""
Fix Database Indexes for Fuze Performance
This will dramatically improve query performance
"""

import os
import time
from app import app, db
from sqlalchemy import text

def add_database_indexes():
    """Add critical database indexes for performance"""
    print("🔧 Adding Database Indexes for Performance")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Check if indexes already exist
            print("🔍 Checking existing indexes...")
            
            # Check for user_id index
            result = db.session.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'saved_content' 
                AND indexname LIKE '%user_id%'
            """))
            user_indexes = [row[0] for row in result]
            
            # Check for quality_score index
            result = db.session.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'saved_content' 
                AND indexname LIKE '%quality_score%'
            """))
            quality_indexes = [row[0] for row in result]
            
            # Check for embedding index
            result = db.session.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'saved_content' 
                AND indexname LIKE '%embedding%'
            """))
            embedding_indexes = [row[0] for row in result]
            
            print(f"Found indexes:")
            print(f"  - user_id: {user_indexes}")
            print(f"  - quality_score: {quality_indexes}")
            print(f"  - embedding: {embedding_indexes}")
            
            # Add missing indexes (without CONCURRENTLY)
            indexes_added = 0
            
            # Add user_id index if missing
            if not user_indexes:
                print("➕ Adding user_id index...")
                db.session.execute(text("""
                    CREATE INDEX idx_saved_content_user_id 
                    ON saved_content(user_id)
                """))
                indexes_added += 1
                print("✅ Added user_id index")
            
            # Add quality_score index if missing
            if not quality_indexes:
                print("➕ Adding quality_score index...")
                db.session.execute(text("""
                    CREATE INDEX idx_saved_content_quality_score 
                    ON saved_content(quality_score)
                """))
                indexes_added += 1
                print("✅ Added quality_score index")
            
            # Add composite index for common queries
            print("➕ Adding composite index for recommendations...")
            db.session.execute(text("""
                CREATE INDEX idx_saved_content_recommendations 
                ON saved_content(user_id, quality_score) 
                WHERE embedding IS NOT NULL
            """))
            indexes_added += 1
            print("✅ Added composite index for recommendations")
            
            # Add index for feedback queries
            print("➕ Adding feedback index...")
            db.session.execute(text("""
                CREATE INDEX idx_feedback_content_user 
                ON feedback(content_id, user_id)
            """))
            indexes_added += 1
            print("✅ Added feedback index")
            
            # Commit changes
            db.session.commit()
            
            print(f"\n🎉 Successfully added {indexes_added} indexes!")
            print("💡 These indexes will dramatically improve query performance")
            
            # Test query performance
            print("\n🧪 Testing query performance...")
            
            # Test user query
            start_time = time.time()
            result = db.session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            user_query_time = (time.time() - start_time) * 1000
            
            # Test content query
            start_time = time.time()
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM saved_content 
                WHERE embedding IS NOT NULL AND quality_score >= 5
            """))
            content_count = result.scalar()
            content_query_time = (time.time() - start_time) * 1000
            
            print(f"📊 Performance Test Results:")
            print(f"  - User count query: {user_query_time:.1f}ms")
            print(f"  - Content query: {content_query_time:.1f}ms")
            
            if user_query_time < 100 and content_query_time < 100:
                print("✅ Query performance is now excellent!")
            else:
                print("⚠️ Query performance still needs improvement")
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding indexes: {e}")
            db.session.rollback()
            return False

def optimize_database_settings():
    """Optimize database settings for better performance"""
    print("\n🔧 Optimizing Database Settings")
    print("=" * 40)
    
    with app.app_context():
        try:
            # Set work_mem for better query performance
            print("⚙️ Setting work_mem for better performance...")
            db.session.execute(text("SET work_mem = '256MB'"))
            
            # Set effective_cache_size
            print("⚙️ Setting effective_cache_size...")
            db.session.execute(text("SET effective_cache_size = '1GB'"))
            
            # Set random_page_cost
            print("⚙️ Setting random_page_cost...")
            db.session.execute(text("SET random_page_cost = 1.1"))
            
            print("✅ Database settings optimized")
            return True
            
        except Exception as e:
            print(f"❌ Error optimizing settings: {e}")
            return False

def main():
    """Main function"""
    print("🚀 Fuze Database Performance Optimization")
    print("=" * 50)
    
    # Add indexes
    if add_database_indexes():
        print("\n✅ Database indexes added successfully!")
    else:
        print("\n❌ Failed to add database indexes")
        return
    
    # Optimize settings
    if optimize_database_settings():
        print("\n✅ Database settings optimized!")
    else:
        print("\n⚠️ Failed to optimize database settings")
    
    print("\n" + "=" * 50)
    print("🎯 Database optimization complete!")
    print("💡 Your recommendations should now be much faster!")
    print("\nNext steps:")
    print("1. Restart your Flask application")
    print("2. Test the optimized endpoints")
    print("3. Run the performance diagnostic again")

if __name__ == "__main__":
    main() 