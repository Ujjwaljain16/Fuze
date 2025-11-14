#!/usr/bin/env python3
"""
Database Connection Monitor
Monitor and diagnose database connection issues
"""

import os
import time
import logging
from dotenv import load_dotenv
from database_utils import get_db_connection_count, get_db_engine, check_database_connection

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def monitor_connections():
    """Monitor database connections in real-time"""
    logger.info("Starting database connection monitoring...")
    logger.info("Press Ctrl+C to stop monitoring")
    
    try:
        while True:
            # Check connection health
            is_healthy = check_database_connection()
            
            # Get connection count
            connection_count = get_db_connection_count()
            
            # Get engine info
            engine = get_db_engine()
            if engine:
                pool = engine.pool
                pool_size = pool.size()
                checked_in = pool.checkedin()
                checked_out = pool.checkedout()
                overflow = pool.overflow()
                
                logger.info(f"Connection Status: {'HEALTHY' if is_healthy else 'UNHEALTHY'}")
                logger.info(f"Total Connections: {connection_count}")
                logger.info(f"Pool Size: {pool_size}")
                logger.info(f"Checked In: {checked_in}")
                logger.info(f"Checked Out: {checked_out}")
                logger.info(f"Overflow: {overflow}")
                logger.info(f"Pool Utilization: {(checked_out + overflow) / (pool_size + overflow) * 100:.1f}%")
                
                # Warning if connections are getting high
                if checked_out + overflow > (pool_size + overflow) * 0.8:
                    logger.warning("⚠️  Connection pool is getting full!")
                if overflow > 0:
                    logger.warning(f"⚠️  Using {overflow} overflow connections")
                    
            else:
                logger.error("❌ Could not get database engine")
            
            logger.info("-" * 50)
            time.sleep(5)  # Check every 5 seconds
            
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring error: {e}")

def diagnose_connection_issues():
    """Diagnose common connection issues"""
    logger.info("Diagnosing database connection issues...")
    
    # Check environment variables
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("❌ DATABASE_URL not found in environment variables")
        return False
    else:
        logger.info("✅ DATABASE_URL found")
    
    # Check database connectivity
    if check_database_connection():
        logger.info("✅ Database connection is healthy")
    else:
        logger.error("❌ Database connection failed")
        return False
    
    # Check connection pool
    engine = get_db_engine()
    if engine:
        pool = engine.pool
        logger.info(f"✅ Connection pool initialized with size {pool.size()}")
        
        # Test a simple query
        try:
            from sqlalchemy import text
            session = engine.connect()
            result = session.execute(text('SELECT 1'))
            result.fetchone()
            session.close()
            logger.info("✅ Database query test successful")
        except Exception as e:
            logger.error(f"❌ Database query test failed: {e}")
            return False
    else:
        logger.error("❌ Could not initialize database engine")
        return False
    
    logger.info("✅ Database connection diagnosis completed successfully")
    return True

def reset_connection_pool():
    """Reset the database connection pool"""
    logger.info("Resetting database connection pool...")
    
    try:
        from database_utils import close_db_session
        
        # Close all sessions
        close_db_session()
        
        # Wait a moment
        time.sleep(2)
        
        # Test connection
        if check_database_connection():
            logger.info("✅ Connection pool reset successful")
            return True
        else:
            logger.error("❌ Connection pool reset failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error resetting connection pool: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "monitor":
            monitor_connections()
        elif command == "diagnose":
            diagnose_connection_issues()
        elif command == "reset":
            reset_connection_pool()
        else:
            print("Usage: python monitor_database_connections.py [monitor|diagnose|reset]")
            print("  monitor  - Monitor connections in real-time")
            print("  diagnose - Diagnose connection issues")
            print("  reset    - Reset connection pool")
    else:
        # Default to diagnose
        diagnose_connection_issues()
