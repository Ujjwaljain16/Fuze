#!/usr/bin/env python3
"""
Quick Performance Fix for Fuze Recommendation System
Addresses the most common bottlenecks immediately
"""

import os
import sys
import time
from redis_utils import redis_cache
from models import db, SavedContent
from sqlalchemy import create_engine, text

def check_redis_status():
    """Check if Redis is running and accessible"""
    print("🔍 Checking Redis status...")
    
    try:
        redis_cache.redis_client.ping()
        print("✅ Redis is running and accessible")
        return True
    except Exception as e:
        print(f"❌ Redis is not accessible: {e}")
        print("💡 To fix this:")
        print("   1. Start Redis server: redis-server")
        print("   2. Or install Redis: python setup_redis.py install")
        return False

def check_database_indexes():
    """Check and suggest database indexes"""
    print("\n🔍 Checking database indexes...")
    
    try:
        # Check if we have the necessary indexes
        from app import app
        with app.app_context():
            engine = db.engine
        
        # Check for embedding index
        result = engine.execute(text("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'saved_content' 
            AND indexname LIKE '%embedding%'
        """))
        
        embedding_indexes = [row[0] for row in result]
        
        if not embedding_indexes:
            print("⚠️ No embedding indexes found")
            print("💡 To improve performance, add this index:")
            print("   CREATE INDEX idx_saved_content_embedding ON saved_content USING ivfflat (embedding vector_cosine_ops);")
        else:
            print(f"✅ Found embedding indexes: {embedding_indexes}")
        
        # Check for quality_score index
        result = engine.execute(text("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'saved_content' 
            AND indexname LIKE '%quality_score%'
        """))
        
        quality_indexes = [row[0] for row in result]
        
        if not quality_indexes:
            print("⚠️ No quality_score index found")
            print("💡 To improve performance, add this index:")
            print("   CREATE INDEX idx_saved_content_quality ON saved_content(quality_score);")
        else:
            print(f"✅ Found quality_score indexes: {quality_indexes}")
        
        # Check for user_id index
        result = engine.execute(text("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'saved_content' 
            AND indexname LIKE '%user_id%'
        """))
        
        user_indexes = [row[0] for row in result]
        
        if not user_indexes:
            print("⚠️ No user_id index found")
            print("💡 To improve performance, add this index:")
            print("   CREATE INDEX idx_saved_content_user ON saved_content(user_id);")
        else:
            print(f"✅ Found user_id indexes: {user_indexes}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking database indexes: {e}")
        return False

def check_embedding_coverage():
    """Check how many bookmarks have embeddings"""
    print("\n🔍 Checking embedding coverage...")
    
    try:
        from app import app
        with app.app_context():
            total_bookmarks = SavedContent.query.count()
            bookmarks_with_embeddings = SavedContent.query.filter(
                SavedContent.embedding.isnot(None)
            ).count()
        
        coverage_percentage = (bookmarks_with_embeddings / total_bookmarks * 100) if total_bookmarks > 0 else 0
        
        print(f"📊 Embedding Coverage:")
        print(f"   Total bookmarks: {total_bookmarks}")
        print(f"   With embeddings: {bookmarks_with_embeddings}")
        print(f"   Coverage: {coverage_percentage:.1f}%")
        
        if coverage_percentage < 80:
            print("⚠️ Low embedding coverage - this will slow down recommendations")
            print("💡 To fix this:")
            print("   python generate_all_embeddings.py")
        else:
            print("✅ Good embedding coverage")
        
        return coverage_percentage >= 80
        
    except Exception as e:
        print(f"❌ Error checking embedding coverage: {e}")
        return False

def check_cache_effectiveness():
    """Check Redis cache effectiveness"""
    print("\n🔍 Checking cache effectiveness...")
    
    if not redis_cache.connected:
        print("❌ Redis not connected - caching disabled")
        return False
    
    try:
        # Test cache operations
        test_key = "performance_test"
        test_data = {"test": "data", "timestamp": time.time()}
        
        # Test set
        start_time = time.time()
        redis_cache.redis_client.setex(test_key, 60, str(test_data))
        set_time = (time.time() - start_time) * 1000
        
        # Test get
        start_time = time.time()
        cached_data = redis_cache.redis_client.get(test_key)
        get_time = (time.time() - start_time) * 1000
        
        # Clean up
        redis_cache.redis_client.delete(test_key)
        
        print(f"📊 Cache Performance:")
        print(f"   Set operation: {set_time:.1f}ms")
        print(f"   Get operation: {get_time:.1f}ms")
        
        if set_time > 10 or get_time > 5:
            print("⚠️ Cache operations are slow")
            print("💡 This could indicate Redis performance issues")
        else:
            print("✅ Cache operations are fast")
        
        return set_time < 10 and get_time < 5
        
    except Exception as e:
        print(f"❌ Error testing cache: {e}")
        return False

def optimize_embedding_utils():
    """Optimize embedding utilities for better performance"""
    print("\n🔧 Optimizing embedding utilities...")
    
    try:
        # Check if we can import the embedding model
        from sentence_transformers import SentenceTransformer
        
        # Test model loading
        start_time = time.time()
        model = SentenceTransformer('all-MiniLM-L6-v2')
        load_time = time.time() - start_time
        
        print(f"📊 Model Loading:")
        print(f"   Load time: {load_time:.2f}s")
        
        if load_time > 5:
            print("⚠️ Model loading is slow")
            print("💡 Consider using a smaller model or pre-loading")
        else:
            print("✅ Model loading is fast")
        
        # Test embedding generation
        test_text = "Python web development with Flask and SQLAlchemy"
        start_time = time.time()
        embedding = model.encode([test_text])[0]
        encode_time = (time.time() - start_time) * 1000
        
        print(f"📊 Embedding Generation:")
        print(f"   Single embedding: {encode_time:.1f}ms")
        
        if encode_time > 500:
            print("⚠️ Embedding generation is slow")
            print("💡 Consider using batch processing")
        else:
            print("✅ Embedding generation is fast")
        
        return encode_time < 500
        
    except Exception as e:
        print(f"❌ Error optimizing embedding utilities: {e}")
        return False

def create_performance_config():
    """Create a performance configuration file"""
    print("\n🔧 Creating performance configuration...")
    
    config_content = """# Performance Configuration for Fuze
# Add these environment variables to improve performance

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Database Configuration
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30

# Embedding Configuration
EMBEDDING_BATCH_SIZE=32
EMBEDDING_CACHE_SIZE=1000

# Recommendation Configuration
MAX_RECOMMENDATIONS=10
SIMILARITY_THRESHOLD=0.25
CACHE_DURATION=1800

# Logging Configuration
LOG_LEVEL=INFO
PERFORMANCE_LOGGING=true
"""
    
    try:
        with open('.env.performance', 'w') as f:
            f.write(config_content)
        print("✅ Created .env.performance file")
        print("💡 Add these variables to your .env file for better performance")
        return True
    except Exception as e:
        print(f"❌ Error creating performance config: {e}")
        return False

def generate_quick_fixes():
    """Generate a list of quick fixes"""
    print("\n🔧 Quick Fixes Summary:")
    print("=" * 50)
    
    fixes = []
    
    # Check Redis
    if not check_redis_status():
        fixes.append("Start Redis server: redis-server")
    
    # Check database indexes
    if not check_database_indexes():
        fixes.append("Add database indexes for better query performance")
    
    # Check embedding coverage
    if not check_embedding_coverage():
        fixes.append("Generate embeddings: python generate_all_embeddings.py")
    
    # Check cache effectiveness
    if not check_cache_effectiveness():
        fixes.append("Optimize Redis configuration")
    
    # Check embedding performance
    if not optimize_embedding_utils():
        fixes.append("Consider using batch embedding processing")
    
    # Create performance config
    create_performance_config()
    
    if fixes:
        print("\n🚨 IMMEDIATE ACTIONS NEEDED:")
        print("-" * 30)
        for i, fix in enumerate(fixes, 1):
            print(f"{i}. {fix}")
    else:
        print("\n✅ No immediate fixes needed - system is well optimized!")
    
    print("\n💡 ADDITIONAL OPTIMIZATIONS:")
    print("-" * 30)
    print("1. Use the new optimized endpoints:")
    print("   - /api/recommendations/optimized")
    print("   - /api/recommendations/optimized-project/<id>")
    print("2. Monitor performance with: python performance_diagnostic.py")
    print("3. Compare engines with: python test_performance_comparison.py")

def main():
    """Main performance fix function"""
    print("🚀 Fuze Quick Performance Fix")
    print("=" * 40)
    
    # Run all checks and fixes
    generate_quick_fixes()
    
    print("\n" + "=" * 40)
    print("🎯 Performance optimization complete!")
    print("=" * 40)

if __name__ == "__main__":
    main() 