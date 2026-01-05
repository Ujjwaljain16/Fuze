#!/usr/bin/env python3
"""
Database Keep-Alive Ping Script

This script performs a simple database health check to prevent Supabase
from pausing due to inactivity. It's designed to be run periodically
via GitHub Actions or cron jobs.

Usage:
    python scripts/ping_db.py

Environment Variables:
    DATABASE_URL - PostgreSQL database connection string
"""

import os
import sys
import time
from datetime import datetime

# Load environment variables from .env file (for local testing)
try:
    from dotenv import load_dotenv
    # Try to load from project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"📁 Loaded environment variables from: {env_path}")
    else:
        load_dotenv()  # Try to load from current directory
except ImportError:
    # python-dotenv not installed, assume env vars are set externally (e.g., in CI/CD)
    pass

try:
    import psycopg2
    from psycopg2 import pool
except ImportError:
    print("❌ Error: psycopg2 is not installed")
    print("Install it with: pip install psycopg2-binary")
    sys.exit(1)


def ping_database():
    """
    Perform a simple database health check.
    
    Returns:
        bool: True if successful, False otherwise
    """
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ Error: DATABASE_URL environment variable is not set")
        return False
    
    # Mask password in logs for security
    safe_url = database_url.split('@')[1] if '@' in database_url else 'unknown'
    print(f"🔄 Pinging database at {safe_url}...")
    print(f"⏰ Timestamp: {datetime.utcnow().isoformat()}Z")
    
    connection = None
    cursor = None
    
    try:
        start_time = time.time()
        
        # Create a simple connection pool
        connection_pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=2,
            dsn=database_url,
            connect_timeout=30
        )
        
        if connection_pool:
            # Get a connection from the pool
            connection = connection_pool.getconn()
            
            # Create a cursor
            cursor = connection.cursor()
            
            # Execute a simple query
            cursor.execute("SELECT 1 as ping, current_timestamp as server_time, version() as pg_version")
            result = cursor.fetchone()
            
            elapsed_time = time.time() - start_time
            
            if result:
                print(f"✅ Database ping successful!")
                print(f"   Response: {result[0]}")
                print(f"   Server Time: {result[1]}")
                print(f"   PostgreSQL Version: {result[2][:50]}...")  # Truncate version string
                print(f"   Response Time: {elapsed_time:.3f}s")
                
                # Additional connection pool stats
                cursor.execute("""
                    SELECT count(*) as active_connections 
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """)
                active_conns = cursor.fetchone()
                if active_conns:
                    print(f"   Active Connections: {active_conns[0]}")
                
                return True
            else:
                print("❌ Database ping failed: No result returned")
                return False
                
    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        return False
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        # Clean up resources
        if cursor:
            cursor.close()
        if connection:
            connection.close()
        print("🔌 Connection closed")


def main():
    """Main entry point"""
    print("=" * 60)
    print("Database Keep-Alive Ping Script")
    print("=" * 60)
    
    success = ping_database()
    
    print("=" * 60)
    
    if success:
        print("✅ Ping completed successfully")
        sys.exit(0)
    else:
        print("❌ Ping failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
