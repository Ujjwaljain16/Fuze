#!/usr/bin/env python3
"""
Check and Optimize pgvector Setup
Verify your current vector database configuration and performance
"""

import os
import time
import logging
from dotenv import load_dotenv
from database_utils import get_db_session

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_pgvector_extension():
    """Check if pgvector extension is properly installed"""
    try:
        session = get_db_session()
        if not session:
            logger.error("Could not get database session")
            return False
        
        # Check if pgvector extension is available
        result = session.execute("SELECT * FROM pg_extension WHERE extname = 'vector'")
        extension = result.fetchone()
        
        if extension:
            logger.info("✅ pgvector extension is installed")
            
            # Check version
            version_result = session.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            version = version_result.fetchone()
            if version:
                logger.info(f"✅ pgvector version: {version[0]}")
            
            return True
        else:
            logger.error("❌ pgvector extension not found")
            return False
            
    except Exception as e:
        logger.error(f"Error checking pgvector extension: {e}")
        return False

def check_vector_tables():
    """Check if vector tables exist and have proper structure"""
    try:
        session = get_db_session()
        if not session:
            return False
        
        # Check content_analysis table
        result = session.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'content_analysis' 
            AND column_name = 'embedding'
        """)
        
        embedding_col = result.fetchone()
        if embedding_col:
            logger.info(f"✅ Embedding column found: {embedding_col[1]}")
            
            # Check if it's a vector type
            if 'vector' in embedding_col[1].lower():
                logger.info("✅ Embedding column is vector type")
            else:
                logger.warning(f"⚠️  Embedding column type: {embedding_col[1]} (should be vector)")
        else:
            logger.error("❌ Embedding column not found in content_analysis")
            return False
        
        # Check table size
        size_result = session.execute("""
            SELECT COUNT(*) as total_rows,
                   COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embeddings
            FROM content_analysis
        """)
        
        size_data = size_result.fetchone()
        if size_data:
            total_rows, with_embeddings = size_data
            logger.info(f"📊 Total rows: {total_rows:,}")
            logger.info(f"📊 Rows with embeddings: {with_embeddings:,}")
            logger.info(f"📊 Embedding coverage: {(with_embeddings/total_rows*100):.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking vector tables: {e}")
        return False

def check_vector_indexes():
    """Check if proper vector indexes exist"""
    try:
        session = get_db_session()
        if not session:
            return False
        
        # Check for HNSW indexes
        result = session.execute("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'content_analysis' 
            AND indexdef LIKE '%hnsw%'
        """)
        
        hnsw_indexes = result.fetchall()
        if hnsw_indexes:
            logger.info(f"✅ Found {len(hnsw_indexes)} HNSW index(es):")
            for idx in hnsw_indexes:
                logger.info(f"   - {idx[0]}")
        else:
            logger.warning("⚠️  No HNSW indexes found")
            
            # Check for any vector indexes
            any_vector_result = session.execute("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'content_analysis' 
                AND indexdef LIKE '%vector%'
            """)
            
            any_vector = any_vector_result.fetchall()
            if any_vector:
                logger.info(f"ℹ️  Found {len(any_vector)} other vector index(es):")
                for idx in any_vector:
                    logger.info(f"   - {idx[0]}: {idx[1][:100]}...")
            else:
                logger.error("❌ No vector indexes found - this will cause slow queries!")
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking vector indexes: {e}")
        return False

def test_vector_query_performance():
    """Test vector similarity query performance"""
    try:
        session = get_db_session()
        if not session:
            return False
        
        # Check if we have any embeddings to test with
        result = session.execute("""
            SELECT embedding FROM content_analysis 
            WHERE embedding IS NOT NULL 
            LIMIT 1
        """)
        
        test_embedding = result.fetchone()
        if not test_embedding:
            logger.warning("⚠️  No embeddings found to test with")
            return False
        
        # Test similarity query performance
        start_time = time.time()
        
        # Simple similarity query
        similarity_result = session.execute("""
            SELECT id, title, 
                   1 - (embedding <=> %s) as similarity
            FROM content_analysis 
            WHERE embedding IS NOT NULL 
            ORDER BY embedding <=> %s 
            LIMIT 10
        """, (test_embedding[0], test_embedding[0]))
        
        results = similarity_result.fetchall()
        query_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        logger.info(f"✅ Vector similarity query completed in {query_time:.2f}ms")
        logger.info(f"✅ Retrieved {len(results)} results")
        
        if query_time < 10:
            logger.info("🚀 Excellent performance (<10ms)")
        elif query_time < 50:
            logger.info("✅ Good performance (<50ms)")
        elif query_time < 100:
            logger.info("⚠️  Acceptable performance (<100ms)")
        else:
            logger.warning(f"⚠️  Slow performance ({query_time:.2f}ms) - consider optimizing indexes")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing vector query performance: {e}")
        return False

def get_optimization_recommendations():
    """Provide optimization recommendations based on current setup"""
    logger.info("\n🔧 OPTIMIZATION RECOMMENDATIONS:")
    
    try:
        session = get_db_session()
        if not session:
            return
        
        # Check embedding dimensions
        result = session.execute("""
            SELECT array_length(embedding, 1) as dimensions
            FROM content_analysis 
            WHERE embedding IS NOT NULL 
            LIMIT 1
        """)
        
        dim_result = result.fetchone()
        if dim_result:
            dimensions = dim_result[0]
            logger.info(f"📏 Current embedding dimensions: {dimensions}")
            
            if dimensions > 512:
                logger.info("💡 Consider reducing dimensions to 384-512 for better performance")
            else:
                logger.info("✅ Dimensions are well-optimized")
        
        # Check for missing indexes
        missing_index_result = session.execute("""
            SELECT COUNT(*) as missing_indexes
            FROM content_analysis 
            WHERE embedding IS NOT NULL
        """)
        
        missing_count = missing_index_result.fetchone()
        if missing_count and missing_count[0] > 0:
            logger.info("💡 Consider creating HNSW index for better similarity search performance")
            logger.info("   CREATE INDEX ON content_analysis USING hnsw (embedding vector_cosine_ops)")
        
        # General recommendations
        logger.info("\n💡 General Recommendations:")
        logger.info("1. Ensure HNSW indexes exist for fast similarity search")
        logger.info("2. Consider batch processing for embedding generation")
        logger.info("3. Monitor query performance and add indexes as needed")
        logger.info("4. Use connection pooling (already implemented)")
        
    except Exception as e:
        logger.error(f"Error getting optimization recommendations: {e}")

def main():
    """Main diagnostic function"""
    logger.info("🔍 pgvector Setup Diagnostic")
    logger.info("=" * 50)
    
    # Check extension
    if not check_pgvector_extension():
        logger.error("❌ pgvector extension not available - cannot continue")
        return
    
    logger.info("")
    
    # Check tables
    if not check_vector_tables():
        logger.error("❌ Vector tables not properly configured")
        return
    
    logger.info("")
    
    # Check indexes
    if not check_vector_indexes():
        logger.warning("⚠️  Vector indexes may need optimization")
    
    logger.info("")
    
    # Test performance
    if not test_vector_query_performance():
        logger.warning("⚠️  Could not test vector query performance")
    
    logger.info("")
    
    # Get recommendations
    get_optimization_recommendations()
    
    logger.info("\n" + "=" * 50)
    logger.info("✅ Diagnostic completed!")

if __name__ == "__main__":
    main() 