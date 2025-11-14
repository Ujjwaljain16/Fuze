"""
Database Migration: Add Project Embeddings

This script adds the new embedding columns to the projects table and
generates embeddings for all existing projects.
"""

import logging
import sys
import os
from sqlalchemy import text, inspect
from sqlalchemy.exc import OperationalError

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Project
from project_embedding_manager import ProjectEmbeddingManager
from database_connection_manager import get_database_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_database_connection():
    """Check if database connection is working"""
    try:
        engine = get_database_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def check_pgvector_extension():
    """Check if pgvector extension is available"""
    try:
        engine = get_database_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
            if result.fetchone():
                logger.info("✅ pgvector extension is available")
                return True
            else:
                logger.error("❌ pgvector extension not found. Please install it first.")
                return False
    except Exception as e:
        logger.error(f"❌ Failed to check pgvector extension: {e}")
        return False

def add_embedding_columns():
    """Add embedding columns to projects table"""
    try:
        engine = get_database_engine()
        
        # Check if columns already exist
        inspector = inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('projects')]
        
        columns_to_add = []
        
        if 'tech_embedding' not in existing_columns:
            columns_to_add.append("ADD COLUMN tech_embedding vector(384)")
        
        if 'description_embedding' not in existing_columns:
            columns_to_add.append("ADD COLUMN description_embedding vector(384)")
        
        if 'combined_embedding' not in existing_columns:
            columns_to_add.append("ADD COLUMN combined_embedding vector(384)")
        
        if 'embeddings_updated' not in existing_columns:
            columns_to_add.append("ADD COLUMN embeddings_updated TIMESTAMP")
        
        if not columns_to_add:
            logger.info("✅ All embedding columns already exist")
            return True
        
        # Add columns
        with engine.connect() as conn:
            for column_sql in columns_to_add:
                sql = f"ALTER TABLE projects {column_sql}"
                logger.info(f"🔄 Adding column: {sql}")
                conn.execute(text(sql))
            
            conn.commit()
            logger.info("✅ Successfully added embedding columns")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to add embedding columns: {e}")
        return False

def create_embedding_indexes():
    """Create indexes for fast similarity search"""
    try:
        engine = get_database_engine()
        
        with engine.connect() as conn:
            # Check if indexes already exist
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'projects' 
                AND indexname LIKE '%embedding%'
            """))
            existing_indexes = [row[0] for row in result.fetchall()]
            
            indexes_to_create = []
            
            if 'idx_projects_tech_embedding' not in existing_indexes:
                indexes_to_create.append("""
                    CREATE INDEX idx_projects_tech_embedding 
                    ON projects USING ivfflat (tech_embedding vector_cosine_ops)
                """)
            
            if 'idx_projects_combined_embedding' not in existing_indexes:
                indexes_to_create.append("""
                    CREATE INDEX idx_projects_combined_embedding 
                    ON projects USING ivfflat (combined_embedding vector_cosine_ops)
                """)
            
            if not indexes_to_create:
                logger.info("✅ All embedding indexes already exist")
                return True
            
            # Create indexes
            for index_sql in indexes_to_create:
                logger.info(f"🔄 Creating index...")
                conn.execute(text(index_sql))
            
            conn.commit()
            logger.info("✅ Successfully created embedding indexes")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to create embedding indexes: {e}")
        return False

def test_embedding_generation():
    """Test if embedding generation works"""
    try:
        logger.info("🧪 Testing embedding generation...")
        
        # Test basic embedding generation
        from embedding_utils import get_embedding
        test_text = "React JavaScript tutorial"
        
        try:
            embedding = get_embedding(test_text)
            if embedding is not None and len(embedding) == 384:
                logger.info("✅ Embedding generation test successful")
                logger.info(f"   Generated embedding of length: {len(embedding)}")
                return True
            else:
                logger.error(f"❌ Embedding generation failed - unexpected result: {type(embedding)}")
                return False
        except Exception as e:
            logger.error(f"❌ Embedding generation test failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Could not test embedding generation: {e}")
        return False

def generate_project_embeddings():
    """Generate embeddings for all existing projects"""
    try:
        logger.info("🔄 Starting project embedding generation...")
        
        # Get database engine and create session
        engine = get_database_engine()
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Get all projects
            projects = session.query(Project).all()
            logger.info(f"📊 Found {len(projects)} projects to process")
            
            if not projects:
                logger.info("ℹ️ No projects found to process - this is normal for a new database")
                return True
            
            # Initialize embedding manager with session
            try:
                embedding_manager = ProjectEmbeddingManager(session)
                logger.info("✅ Project embedding manager initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize project embedding manager: {e}")
                return False
            
            # Generate embeddings for all projects
            try:
                results = embedding_manager.update_all_project_embeddings()
                
                logger.info(f"✅ Embedding generation completed:")
                logger.info(f"   Total: {results['total']}")
                logger.info(f"   Success: {results['success']}")
                logger.info(f"   Failure: {results['failure']}")
                
                return results['failure'] == 0
                
            except Exception as e:
                logger.error(f"❌ Failed to generate project embeddings: {e}")
                return False
            
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to generate project embeddings: {e}")
        return False

def verify_migration():
    """Verify that the migration was successful"""
    try:
        engine = get_database_engine()
        
        with engine.connect() as conn:
            # Check columns
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'projects' 
                AND column_name LIKE '%embedding%'
                ORDER BY column_name
            """))
            
            columns = result.fetchall()
            logger.info("📋 Embedding columns in projects table:")
            for col in columns:
                logger.info(f"   {col[0]}: {col[1]}")
            
            # Check indexes
            result = conn.execute(text("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'projects' 
                AND indexname LIKE '%embedding%'
                ORDER BY indexname
            """))
            
            indexes = result.fetchall()
            logger.info("📋 Embedding indexes:")
            for idx in indexes:
                logger.info(f"   {idx[0]}")
            
            # Check sample project embeddings
            result = conn.execute(text("""
                SELECT COUNT(*) as total_projects,
                       COUNT(tech_embedding) as with_tech_emb,
                       COUNT(combined_embedding) as with_combined_emb
                FROM projects
            """))
            
            stats = result.fetchone()
            logger.info("📊 Project embedding statistics:")
            logger.info(f"   Total projects: {stats[0]}")
            logger.info(f"   With tech embeddings: {stats[1]}")
            logger.info(f"   With combined embeddings: {stats[2]}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to verify migration: {e}")
        return False

def main():
    """Main migration function"""
    logger.info("🚀 Starting Project Embeddings Migration")
    logger.info("=" * 50)
    
    # Step 1: Check prerequisites
    if not check_database_connection():
        logger.error("❌ Cannot proceed without database connection")
        return False
    
    if not check_pgvector_extension():
        logger.error("❌ Cannot proceed without pgvector extension")
        return False
    
    # Step 2: Add columns
    logger.info("\n📝 Step 1: Adding embedding columns...")
    if not add_embedding_columns():
        logger.error("❌ Failed to add embedding columns")
        return False
    
    # Step 3: Create indexes
    logger.info("\n🔍 Step 2: Creating embedding indexes...")
    if not create_embedding_indexes():
        logger.error("❌ Failed to create embedding indexes")
        return False
    
    # Step 4: Test embedding generation
    logger.info("\n🧪 Step 3: Testing embedding generation...")
    if not test_embedding_generation():
        logger.error("❌ Embedding generation test failed")
        return False
    
    # Step 5: Generate embeddings
    logger.info("\n🧠 Step 4: Generating project embeddings...")
    if not generate_project_embeddings():
        logger.error("❌ Failed to generate project embeddings")
        return False
    
    # Step 6: Verify migration
    logger.info("\n✅ Step 5: Verifying migration...")
    if not verify_migration():
        logger.error("❌ Migration verification failed")
        return False
    
    logger.info("\n🎉 Project Embeddings Migration Completed Successfully!")
    logger.info("=" * 50)
    logger.info("Next steps:")
    logger.info("1. Your recommendation engines can now use project embeddings")
    logger.info("2. Use ProjectEmbeddingManager for enhanced recommendations")
    logger.info("3. Monitor performance and adjust similarity thresholds as needed")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 Unexpected error during migration: {e}")
        sys.exit(1)
