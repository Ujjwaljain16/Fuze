#!/usr/bin/env python3
"""
Database Index Optimization Script
==================================

Creates comprehensive indexes for production performance.
Run this script after database migrations to ensure optimal query performance.
"""

import os
import sys
import logging
from sqlalchemy import text, inspect

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Production indexes for optimal performance
PRODUCTION_INDEXES = {
    'saved_content': [
        # User isolation - CRITICAL for security and performance
        "CREATE INDEX IF NOT EXISTS idx_saved_content_user_id ON saved_content(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_saved_content_user_quality ON saved_content(user_id, quality_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_saved_content_user_saved_at ON saved_content(user_id, saved_at DESC)",
        
        # Content filtering
        "CREATE INDEX IF NOT EXISTS idx_saved_content_quality ON saved_content(quality_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_saved_content_has_text ON saved_content(user_id) WHERE extracted_text IS NOT NULL AND extracted_text != ''",
        
        # Vector search optimization (PostgreSQL with pgvector)
        "CREATE INDEX IF NOT EXISTS idx_saved_content_embedding ON saved_content USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)",
    ],
    
    'projects': [
        # User isolation
        "CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_projects_user_created ON projects(user_id, created_at DESC)",
        
        # Vector search
        "CREATE INDEX IF NOT EXISTS idx_projects_embedding ON projects USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)",
    ],
    
    'tasks': [
        # Project relationship
        "CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_project_created ON tasks(project_id, created_at DESC)",
        
        # Vector search
        "CREATE INDEX IF NOT EXISTS idx_tasks_embedding ON tasks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)",
    ],
    
    'subtasks': [
        # Task relationship
        "CREATE INDEX IF NOT EXISTS idx_subtasks_task_id ON subtasks(task_id)",
        "CREATE INDEX IF NOT EXISTS idx_subtasks_task_completed ON subtasks(task_id, completed)",
    ],
    
    'content_analysis': [
        # Content relationship
        "CREATE INDEX IF NOT EXISTS idx_content_analysis_content_id ON content_analysis(content_id)",
        "CREATE INDEX IF NOT EXISTS idx_content_analysis_relevance ON content_analysis(relevance_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_content_analysis_type ON content_analysis(content_type)",
    ],
    
    'user_feedback': [
        # Already has indexes, but ensure they exist
        "CREATE INDEX IF NOT EXISTS idx_user_feedback_user ON user_feedback(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_feedback_content ON user_feedback(content_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_feedback_timestamp ON user_feedback(timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_user_feedback_user_content ON user_feedback(user_id, content_id)",
    ],
    
    'feedback': [
        # User isolation
        "CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_feedback_content_id ON feedback(content_id)",
        "CREATE INDEX IF NOT EXISTS idx_feedback_project_id ON feedback(project_id)",
    ],
    
    'users': [
        # Case-insensitive username and email lookups (critical for login)
        "CREATE INDEX IF NOT EXISTS idx_users_username_lower ON users(LOWER(username))",
        "CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users(LOWER(email))",
        "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)",
    ],
}

def create_indexes(db, use_concurrent: bool = False):
    """
    Create all production indexes
    
    Args:
        db: SQLAlchemy database instance
        use_concurrent: Use CONCURRENTLY for PostgreSQL (requires autocommit mode)
    """
    logger.info(" Creating production database indexes...")
    
    inspector = inspect(db.engine)
    existing_indexes = set()
    
    # Get all existing indexes
    for table_name in inspector.get_table_names():
        indexes = inspector.get_indexes(table_name)
        existing_indexes.update([idx['name'] for idx in indexes])
    
    logger.info(f"📋 Found {len(existing_indexes)} existing indexes")
    
    created_count = 0
    skipped_count = 0
    error_count = 0
    
    # Check if PostgreSQL
    database_url = str(db.engine.url)
    is_postgresql = 'postgresql' in database_url or 'postgres' in database_url
    
    for table_name, index_sqls in PRODUCTION_INDEXES.items():
        # Check if table exists
        if table_name not in inspector.get_table_names():
            logger.warning(f" Table {table_name} does not exist, skipping indexes")
            continue
        
        for index_sql in index_sqls:
            try:
                # Extract index name from SQL
                index_name = index_sql.split('idx_')[1].split()[0] if 'idx_' in index_sql else None
                
                if index_name and index_name in existing_indexes:
                    logger.debug(f" Index {index_name} already exists, skipping")
                    skipped_count += 1
                    continue
                
                # Prepare SQL
                final_sql = index_sql
                needs_concurrent = use_concurrent and is_postgresql and 'CREATE INDEX' in index_sql
                
                if needs_concurrent:
                    # For CONCURRENTLY, remove IF NOT EXISTS (not supported together)
                    final_sql = final_sql.replace('CREATE INDEX IF NOT EXISTS', 'CREATE INDEX CONCURRENTLY')
                    final_sql = final_sql.replace('IF NOT EXISTS', '')
                    
                    # CONCURRENTLY requires autocommit - use raw psycopg2 connection
                    logger.info(f" Creating index (CONCURRENTLY): {index_name or 'unnamed'}")
                    try:
                        # Get raw psycopg2 connection directly
                        raw_conn = db.engine.raw_connection()
                        try:
                            # Set isolation level to 0 (autocommit) for CONCURRENTLY
                            # This is required because CONCURRENTLY cannot run in a transaction
                            old_isolation = raw_conn.isolation_level
                            raw_conn.set_isolation_level(0)  # 0 = autocommit
                            cursor = raw_conn.cursor()
                            cursor.execute(final_sql)
                            cursor.close()
                            # Restore original isolation level
                            raw_conn.set_isolation_level(old_isolation)
                        except Exception as conn_error:
                            # Restore isolation level even on error
                            try:
                                raw_conn.set_isolation_level(old_isolation)
                            except:
                                pass
                            raise conn_error
                        finally:
                            raw_conn.close()
                    except Exception as conn_error:
                        # If CONCURRENTLY fails, will be caught by outer exception handler
                        raise conn_error
                else:
                    # Regular index creation (can use transaction)
                    logger.info(f" Creating index: {index_name or 'unnamed'}")
                    db.session.execute(text(final_sql))
                    db.session.commit()
                
                created_count += 1
                
                if index_name:
                    existing_indexes.add(index_name)
                    
            except Exception as e:
                error_count += 1
                error_msg = str(e).lower()
                
                # Ignore "already exists" errors
                if 'already exists' in error_msg or 'duplicate' in error_msg:
                    logger.debug(f" Index already exists (error: {e})")
                    skipped_count += 1
                    error_count -= 1  # Don't count as error
                elif 'concurrent' in error_msg and ('transaction' in error_msg or 'cannot run' in error_msg):
                    logger.warning(f" CONCURRENTLY failed (transaction issue), retrying without CONCURRENTLY: {e}")
                    # Retry without CONCURRENTLY
                    try:
                        retry_sql = index_sql.replace('CONCURRENTLY', '').replace('CREATE INDEX IF NOT EXISTS', 'CREATE INDEX IF NOT EXISTS')
                        db.session.execute(text(retry_sql))
                        db.session.commit()
                        created_count += 1
                        error_count -= 1  # Adjust counts
                        if index_name:
                            existing_indexes.add(index_name)
                    except Exception as retry_error:
                        retry_error_msg = str(retry_error).lower()
                        if 'already exists' in retry_error_msg:
                            logger.debug(f" Index already exists: {retry_error}")
                            skipped_count += 1
                            error_count -= 1
                        else:
                            logger.error(f" Failed to create index even without CONCURRENTLY: {retry_error}")
                else:
                    logger.error(f" Failed to create index: {e}")
                    if not needs_concurrent:
                        db.session.rollback()
    
    logger.info(f" Index creation complete:")
    logger.info(f"   Created: {created_count}")
    logger.info(f"   Skipped: {skipped_count}")
    logger.info(f"   Errors: {error_count}")
    
    return {
        'created': created_count,
        'skipped': skipped_count,
        'errors': error_count
    }

def verify_indexes(db):
    """Verify that critical indexes exist"""
    logger.info(" Verifying critical indexes...")
    
    inspector = inspect(db.engine)
    all_indexes = {}
    
    for table_name in inspector.get_table_names():
        indexes = inspector.get_indexes(table_name)
        all_indexes[table_name] = [idx['name'] for idx in indexes]
    
    # Critical indexes that must exist
    critical_indexes = {
        'saved_content': ['idx_saved_content_user_id'],
        'projects': ['idx_projects_user_id'],
        'users': ['idx_users_username_lower', 'idx_users_email_lower'],
    }
    
    missing_indexes = []
    for table, required_indexes in critical_indexes.items():
        if table not in all_indexes:
            logger.warning(f" Table {table} not found in database")
            missing_indexes.extend([f"{table}.{idx}" for idx in required_indexes])
        else:
            for idx in required_indexes:
                if idx not in all_indexes[table]:
                    missing_indexes.append(f"{table}.{idx}")
    
    if missing_indexes:
        logger.warning(f" Missing critical indexes: {missing_indexes}")
        logger.info(" These indexes will be created on next run or can be created manually")
        # Don't fail verification - these are important but not critical for basic operation
        # They'll be created by the index creation function
        return len(missing_indexes) == 0
    else:
        logger.info(" All critical indexes verified")
        return True

if __name__ == "__main__":
    from run_production import app, db
    
    with app.app_context():
        # Check if PostgreSQL (for vector indexes)
        database_url = os.environ.get('DATABASE_URL', '')
        is_postgresql = 'postgresql' in database_url or 'postgres' in database_url
        
        if not is_postgresql:
            logger.warning(" Not using PostgreSQL - vector indexes will be skipped")
            # Remove vector index SQLs
            for table_indexes in PRODUCTION_INDEXES.values():
                table_indexes[:] = [idx for idx in table_indexes if 'vector' not in idx.lower()]
        
        # Create indexes
        result = create_indexes(db, use_concurrent=is_postgresql)
        
        # Verify
        verify_indexes(db)
        
        logger.info(" Database index optimization complete!")

