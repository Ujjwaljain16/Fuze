#!/usr/bin/env python3
"""
Database Security Migration Script
===================================

Fixes Supabase database linter security issues:
1. Enables Row Level Security (RLS) on all tables
2. Creates RLS policies for user isolation
3. Fixes function search_path security issues
4. Documents extension and Postgres version requirements

Run this script after database initialization to enable RLS.
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

# Tables that need RLS enabled
TABLES_WITH_RLS = [
    'users',
    'projects',
    'saved_content',
    'content_analysis',
    'feedback',
    'user_feedback',
    'tasks',
    'subtasks'
]

# Functions that need search_path fixed
FUNCTIONS_TO_FIX = [
    'normalize_embedding',
    'match_bookmarks'
]

def enable_rls_on_table(db, table_name: str):
    """Enable Row Level Security on a table"""
    try:
        # Check if RLS is already enabled
        check_sql = text("""
            SELECT tablename, rowsecurity 
            FROM pg_tables 
            WHERE schemaname = 'public' AND tablename = :table_name
        """)
        result = db.session.execute(check_sql, {'table_name': table_name}).fetchone()
        
        if result and result[1]:  # rowsecurity is True
            logger.info(f"✅ RLS already enabled on {table_name}")
            return True
        
        # Enable RLS
        enable_sql = text(f"ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY;")
        db.session.execute(enable_sql)
        db.session.commit()
        logger.info(f"✅ Enabled RLS on {table_name}")
        return True
    except Exception as e:
        error_msg = str(e).lower()
        if 'already' in error_msg or 'duplicate' in error_msg:
            logger.info(f"✅ RLS already enabled on {table_name}")
            return True
        logger.error(f"❌ Failed to enable RLS on {table_name}: {e}")
        db.session.rollback()
        return False

def create_rls_policy(db, table_name: str, policy_name: str, policy_sql: str):
    """Create an RLS policy"""
    try:
        # Check if policy already exists
        check_sql = text("""
            SELECT policyname 
            FROM pg_policies 
            WHERE schemaname = 'public' 
            AND tablename = :table_name 
            AND policyname = :policy_name
        """)
        result = db.session.execute(check_sql, {
            'table_name': table_name,
            'policy_name': policy_name
        }).fetchone()
        
        if result:
            logger.info(f"✅ Policy {policy_name} already exists on {table_name}")
            return True
        
        # Create policy
        db.session.execute(text(policy_sql))
        db.session.commit()
        logger.info(f"✅ Created RLS policy {policy_name} on {table_name}")
        return True
    except Exception as e:
        error_msg = str(e).lower()
        if 'already exists' in error_msg or 'duplicate' in error_msg:
            logger.info(f"✅ Policy {policy_name} already exists on {table_name}")
            return True
        logger.error(f"❌ Failed to create policy {policy_name} on {table_name}: {e}")
        db.session.rollback()
        return False

def create_user_isolation_policies(db):
    """Create RLS policies for user data isolation
    
    Note: Since we use Flask/JWT authentication (not Supabase Auth),
    we create policies that allow service_role (our app) to access all data,
    but restrict direct database access. Application-level security ensures
    user isolation via JWT tokens and user_id filtering.
    """
    
    policies = []
    
    # For Flask/JWT apps, we allow service_role to bypass RLS
    # Application-level security (JWT + user_id filtering) handles isolation
    
    # Users table - allow service role (our Flask app) to access
    policies.append({
        'table': 'users',
        'name': 'users_service_role_access',
        'sql': """
            CREATE POLICY users_service_role_access ON public.users
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
        """
    })
    
    # Saved Content - allow service role access (app handles user filtering)
    policies.append({
        'table': 'saved_content',
        'name': 'saved_content_service_role_access',
        'sql': """
            CREATE POLICY saved_content_service_role_access ON public.saved_content
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
        """
    })
    
    # Projects - allow service role access
    policies.append({
        'table': 'projects',
        'name': 'projects_service_role_access',
        'sql': """
            CREATE POLICY projects_service_role_access ON public.projects
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
        """
    })
    
    # Tasks - allow service role access
    policies.append({
        'table': 'tasks',
        'name': 'tasks_service_role_access',
        'sql': """
            CREATE POLICY tasks_service_role_access ON public.tasks
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
        """
    })
    
    # Subtasks - allow service role access
    policies.append({
        'table': 'subtasks',
        'name': 'subtasks_service_role_access',
        'sql': """
            CREATE POLICY subtasks_service_role_access ON public.subtasks
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
        """
    })
    
    # Content Analysis - allow service role access
    policies.append({
        'table': 'content_analysis',
        'name': 'content_analysis_service_role_access',
        'sql': """
            CREATE POLICY content_analysis_service_role_access ON public.content_analysis
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
        """
    })
    
    # Feedback - allow service role access
    policies.append({
        'table': 'feedback',
        'name': 'feedback_service_role_access',
        'sql': """
            CREATE POLICY feedback_service_role_access ON public.feedback
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
        """
    })
    
    # User Feedback - allow service role access
    policies.append({
        'table': 'user_feedback',
        'name': 'user_feedback_service_role_access',
        'sql': """
            CREATE POLICY user_feedback_service_role_access ON public.user_feedback
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
        """
    })
    
    return policies

def fix_function_search_path(db, function_name: str):
    """Fix function search_path security issue"""
    try:
        # Check if function exists
        check_sql = text("""
            SELECT proname, prosecdef 
            FROM pg_proc 
            WHERE proname = :function_name 
            AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        """)
        result = db.session.execute(check_sql, {'function_name': function_name}).fetchone()
        
        if not result:
            logger.warning(f"⚠️  Function {function_name} not found - may be created by Supabase/pgvector")
            return False
        
        # Get function signature to recreate it with secure search_path
        get_func_sql = text("""
            SELECT pg_get_functiondef(oid) as definition
            FROM pg_proc 
            WHERE proname = :function_name 
            AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            LIMIT 1
        """)
        func_result = db.session.execute(get_func_sql, {'function_name': function_name}).fetchone()
        
        if func_result:
            logger.info(f"ℹ️  Function {function_name} exists but may need manual fix")
            logger.info(f"   To fix: ALTER FUNCTION public.{function_name} SET search_path = '';")
            logger.info(f"   Or recreate with: SET search_path = ''; in function definition")
        
        # Try to set search_path to empty (most secure)
        try:
            fix_sql = text(f"ALTER FUNCTION public.{function_name} SET search_path = '';")
            db.session.execute(fix_sql)
            db.session.commit()
            logger.info(f"✅ Fixed search_path for {function_name}")
            return True
        except Exception as fix_error:
            logger.warning(f"⚠️  Could not auto-fix {function_name}: {fix_error}")
            logger.info(f"   Manual fix required - see Supabase dashboard or run SQL manually")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️  Could not check/fix function {function_name}: {e}")
        return False

def create_security_schema():
    """Create a separate schema for extensions (optional, for future use)"""
    try:
        # Create extensions schema
        create_schema_sql = text("CREATE SCHEMA IF NOT EXISTS extensions;")
        db.session.execute(create_schema_sql)
        db.session.commit()
        logger.info("✅ Created extensions schema (for future use)")
        return True
    except Exception as e:
        logger.warning(f"⚠️  Could not create extensions schema: {e}")
        db.session.rollback()
        return False

def run_security_migration(db):
    """Run complete security migration"""
    logger.info("🔒 Starting database security migration...")
    
    # Check if PostgreSQL
    database_url = str(db.engine.url)
    is_postgresql = 'postgresql' in database_url or 'postgres' in database_url
    
    if not is_postgresql:
        logger.warning("⚠️  Not using PostgreSQL - RLS is PostgreSQL-only")
        logger.info("   SQLite doesn't support RLS - security handled at application level")
        return {'success': False, 'reason': 'Not PostgreSQL'}
    
    # Check if Supabase (has auth schema)
    try:
        check_auth = text("SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'auth');")
        has_auth = db.session.execute(check_auth).scalar()
        
        if not has_auth:
            logger.warning("⚠️  Auth schema not found - may not be Supabase")
            logger.info("   Creating application-level RLS policies instead")
    except:
        has_auth = False
    
    results = {
        'rls_enabled': 0,
        'policies_created': 0,
        'functions_fixed': 0,
        'errors': []
    }
    
    # 1. Enable RLS on all tables
    logger.info("\n📋 Step 1: Enabling Row Level Security on tables...")
    for table_name in TABLES_WITH_RLS:
        if enable_rls_on_table(db, table_name):
            results['rls_enabled'] += 1
    
    # 2. Create RLS policies
    logger.info("\n📋 Step 2: Creating RLS policies for user isolation...")
    logger.info("   Note: Using service_role policies (Flask/JWT handles user isolation)")
    
    policies = create_user_isolation_policies(db)
    for policy in policies:
        if create_rls_policy(db, policy['table'], policy['name'], policy['sql']):
            results['policies_created'] += 1
    
    # 3. Fix function search_path
    logger.info("\n📋 Step 3: Fixing function search_path security...")
    for function_name in FUNCTIONS_TO_FIX:
        if fix_function_search_path(db, function_name):
            results['functions_fixed'] += 1
    
    # 4. Create extensions schema (optional)
    logger.info("\n📋 Step 4: Creating extensions schema...")
    create_security_schema()
    
    logger.info("\n✅ Security migration complete!")
    logger.info(f"   RLS enabled on: {results['rls_enabled']} tables")
    logger.info(f"   Policies created: {results['policies_created']}")
    logger.info(f"   Functions fixed: {results['functions_fixed']}")
    
    logger.info("\n📝 Notes:")
    logger.info("   - Vector extension in public schema is acceptable for Supabase")
    logger.info("   - Postgres version upgrade: Check Supabase dashboard for upgrade options")
    logger.info("   - Functions may need manual fix if auto-fix failed")
    
    return results

if __name__ == "__main__":
    from run_production import app, db
    
    with app.app_context():
        results = run_security_migration(db)
        
        if results.get('success') is False:
            logger.warning("Migration skipped (not PostgreSQL)")
        else:
            logger.info("\n🎉 Database security migration completed successfully!")

