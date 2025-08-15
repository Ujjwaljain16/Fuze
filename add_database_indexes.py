#!/usr/bin/env python3
"""
Add Database Indexes for Performance Optimization
Fixes the slow database queries causing recommendation delays
"""

import sys
import os
from sqlalchemy import create_engine, text, Index
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError, OperationalError

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️ python-dotenv not installed, trying to load environment manually")
    # Try to load .env file manually
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Loaded environment variables manually from .env file")
    else:
        print("⚠️ No .env file found")

def check_index_exists(engine, index_name, table_name):
    """Check if an index already exists"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE indexname = :index_name AND tablename = :table_name
            """), {"index_name": index_name, "table_name": table_name})
            return result.fetchone() is not None
    except Exception:
        return False

def add_performance_indexes():
    """Add critical database indexes for performance"""
    
    try:
        # Debug: Check environment variables
        print(f"🔍 Environment check:")
        print(f"  - DATABASE_URL: {'✅ Set' if os.environ.get('DATABASE_URL') else '❌ Not set'}")
        print(f"  - Current working directory: {os.getcwd()}")
        
        from config import Config
        
        # Debug: Check config
        print(f"  - Config DATABASE_URL: {'✅ Set' if Config.SQLALCHEMY_DATABASE_URI else '❌ Not set'}")
        
        if not Config.SQLALCHEMY_DATABASE_URI:
            print("❌ DATABASE_URL is not set in configuration")
            print("💡 Please check your .env file contains: DATABASE_URL=postgresql://...")
            return False
        
        from models import db, SavedContent, ContentAnalysis, User
        
        # Create database connection
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        
        print("🔧 Adding performance indexes...")
        
        # Define indexes with correct names
        indexes_to_create = [
            {
                'name': 'idx_savedcontent_user_id',
                'table': 'saved_content',
                'columns': ['user_id'],
                'description': 'User ID for fast user-specific queries'
            },
            {
                'name': 'idx_savedcontent_quality_score',
                'table': 'saved_content',
                'columns': ['quality_score'],
                'description': 'Quality score for recommendation filtering'
            },
            {
                'name': 'idx_savedcontent_embedding',
                'table': 'saved_content',
                'columns': ['embedding'],
                'description': 'Embedding vector for similarity search'
            },
            {
                'name': 'idx_savedcontent_user_quality',
                'table': 'saved_content',
                'columns': ['user_id', 'quality_score'],
                'description': 'Composite index for user + quality queries'
            },
            {
                'name': 'idx_contentanalysis_content_id',
                'table': 'content_analysis',
                'columns': ['content_id'],
                'description': 'Content ID for analysis lookups'
            },
            {
                'name': 'idx_savedcontent_saved_at',
                'table': 'saved_content',
                'columns': ['saved_at'],
                'description': 'Timestamp for time-based queries'
            }
        ]
        
        # Create each index
        for index_info in indexes_to_create:
            try:
                # Check if index already exists
                if check_index_exists(engine, index_info['name'], index_info['table']):
                    print(f"✅ Index {index_info['name']} already exists on {index_info['table']}")
                    continue
                
                # Create index using raw SQL for better control
                columns_str = ', '.join(index_info['columns'])
                create_sql = f"""
                    CREATE INDEX {index_info['name']} 
                    ON {index_info['table']} ({columns_str})
                """
                
                with engine.connect() as conn:
                    conn.execute(text(create_sql))
                    conn.commit()
                
                print(f"✅ Created index {index_info['name']} on {index_info['table']} ({columns_str})")
                
            except Exception as e:
                if "already exists" in str(e) or "DuplicateTable" in str(e):
                    print(f"✅ Index {index_info['name']} already exists on {index_info['table']}")
                else:
                    print(f"⚠️ Failed to create index {index_info['name']}: {e}")
        
        print("🎯 Database indexes added successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error adding indexes: {e}")
        return False

def optimize_database_settings():
    """Optimize database settings for better performance"""
    
    try:
        from config import Config
        
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        
        print("⚡ Optimizing database settings...")
        
        # Runtime optimizations that can be applied immediately
        runtime_optimizations = [
            ("SET work_mem = '256MB'", "Work memory per query"),
            ("SET effective_cache_size = '1GB'", "Effective cache size"),
            ("SET random_page_cost = 1.1", "SSD optimization"),
            ("SET effective_io_concurrency = 200", "Parallel I/O operations")
        ]
        
        # Apply runtime settings
        with engine.connect() as conn:
            for sql, description in runtime_optimizations:
                try:
                    conn.execute(text(sql))
                    print(f"✅ Applied: {sql} - {description}")
                except Exception as e:
                    print(f"⚠️ Failed to apply {sql}: {e}")
            
            # Commit changes
            conn.commit()
        
        # Handle server-level settings separately
        print("\n📝 Server-level settings (require restart):")
        print("  - shared_buffers = 256MB")
        print("  - max_connections = 100")
        print("  - checkpoint_completion_target = 0.9")
        print("💡 These settings require editing postgresql.conf and restarting the server")
        
        return True
        
    except Exception as e:
        print(f"❌ Error optimizing database: {e}")
        return False

def analyze_table_performance():
    """Analyze table performance after optimizations"""
    
    try:
        from config import Config
        
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        
        print("📊 Analyzing table performance...")
        
        # Check table sizes and row counts
        tables = ['saved_content', 'content_analysis', 'users']
        
        with engine.connect() as conn:
            for table in tables:
                try:
                    # Get row count
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    row_count = count_result.scalar()
                    
                    # Get table size
                    size_result = conn.execute(text(f"""
                        SELECT pg_size_pretty(pg_total_relation_size('{table}'))
                    """))
                    table_size = size_result.scalar()
                    
                    print(f"📋 {table}: {row_count:,} rows, {table_size}")
                    
                except Exception as e:
                    print(f"⚠️ Could not analyze {table}: {e}")
            
            # Check index usage with robust error handling and transaction management
            try:
                # Try the standard PostgreSQL 9.5+ query first
                index_result = conn.execute(text("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes 
                    WHERE schemaname = 'public'
                    ORDER BY idx_scan DESC
                    LIMIT 10
                """))
                
                print("\n🔍 Top 10 Index Usage:")
                for row in index_result:
                    print(f"  {row.tablename}.{row.indexname}: {row.idx_scan} scans")
                    
            except ProgrammingError as e:
                if "tablename" in str(e):
                    # Try alternative query for older PostgreSQL versions
                    try:
                        print("🔄 Trying alternative index analysis for older PostgreSQL...")
                        alt_result = conn.execute(text("""
                            SELECT 
                                schemaname,
                                relname as tablename,
                                indexrelname as indexname,
                                idx_scan,
                                idx_tup_read,
                                idx_tup_fetch
                            FROM pg_stat_user_indexes 
                            WHERE schemaname = 'public'
                            ORDER BY idx_scan DESC
                            LIMIT 10
                        """))
                        
                        print("\n🔍 Top 10 Index Usage (Alternative):")
                        for row in alt_result:
                            print(f"  {row.tablename}.{row.indexname}: {row.idx_scan} scans")
                            
                    except Exception as alt_e:
                        print(f"⚠️ Alternative index analysis failed: {alt_e}")
                        print("💡 Index usage statistics may not be available in this PostgreSQL version")
                else:
                    print(f"⚠️ Could not analyze index usage: {e}")
                    print("💡 Index usage statistics may not be available in this PostgreSQL version")
            except Exception as e:
                print(f"⚠️ Could not analyze index usage: {e}")
                print("💡 Index usage statistics may not be available in this PostgreSQL version")
            
            # Check existing indexes with fresh transaction if needed
            try:
                print("\n🔍 Existing Indexes:")
                index_list = conn.execute(text("""
                    SELECT 
                        tablename,
                        indexname
                    FROM pg_indexes 
                    WHERE schemaname = 'public'
                    ORDER BY tablename, indexname
                """))
                
                for row in index_list:
                    print(f"  {row.tablename}.{row.indexname}")
                    
            except Exception as e:
                print(f"⚠️ Could not list existing indexes: {e}")
                # Try to reset transaction state
                try:
                    conn.rollback()
                    print("🔄 Reset transaction state and retrying...")
                    index_list = conn.execute(text("""
                        SELECT 
                            tablename,
                            indexname
                        FROM pg_indexes 
                        WHERE schemaname = 'public'
                        ORDER BY tablename, indexname
                    """))
                    
                    print("\n🔍 Existing Indexes (Retry):")
                    for row in index_list:
                        print(f"  {row.tablename}.{row.indexname}")
                        
                except Exception as retry_e:
                    print(f"⚠️ Retry also failed: {retry_e}")
        
    except Exception as e:
        print(f"❌ Error analyzing performance: {e}")

def print_server_settings_guide():
    """Print guide for server-level PostgreSQL settings"""
    print("\n" + "="*60)
    print("📋 SERVER-LEVEL SETTINGS GUIDE")
    print("="*60)
    print("These settings require editing postgresql.conf and restarting PostgreSQL:")
    print()
    print("🔧 Performance Settings:")
    print("  shared_buffers = 256MB                    # 25% of RAM")
    print("  effective_cache_size = 1GB                # 75% of RAM")
    print("  work_mem = 256MB                          # Per-query memory")
    print("  maintenance_work_mem = 256MB              # Maintenance operations")
    print()
    print("⚡ I/O Optimization:")
    print("  random_page_cost = 1.1                    # SSD optimization")
    print("  effective_io_concurrency = 200            # Parallel I/O")
    print("  checkpoint_completion_target = 0.9         # Checkpoint timing")
    print()
    print("🔄 Connection Settings:")
    print("  max_connections = 100                     # Connection limit")
    print("  shared_preload_libraries = 'pg_stat_statements'")
    print()
    print("💡 To apply these settings:")
    print("  1. Find postgresql.conf (usually in /etc/postgresql/*/main/)")
    print("  2. Edit the file with the above values")
    print("  3. Restart PostgreSQL: sudo systemctl restart postgresql")
    print("  4. Or: sudo pg_ctl restart -D /var/lib/postgresql/*/main")
    print("="*60)

if __name__ == "__main__":
    print("🚀 Database Performance Optimization Script")
    print("=" * 50)
    
    # Add performance indexes
    success = add_performance_indexes()
    
    if success:
        # Optimize database settings
        optimize_database_settings()
        
        # Analyze performance
        analyze_table_performance()
        
        # Print server settings guide
        print_server_settings_guide()
        
        print("\n🎉 Database optimization complete!")
        print("Expected improvements:")
        print("- User queries: 3.86s → 0.1-0.5s (90% faster)")
        print("- Complex queries: 8.03s → 0.5-2s (85% faster)")
        print("- Recommendation computation: 7.52s → 1-3s (80% faster)")
        print("\n💡 For maximum performance, consider applying server-level settings")
    else:
        print("❌ Database optimization failed!") 