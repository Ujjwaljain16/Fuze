#!/usr/bin/env python3
"""
SSL Connection Fix Script
Fixes SSL connection issues with PostgreSQL database
"""

import os
import sys
import time
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ssl_connection():
    """Test SSL connection with different configurations"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    logger.info("Testing SSL connection configurations...")
    
    # Test different SSL modes
    ssl_modes = ['prefer', 'require', 'verify-ca', 'verify-full']
    
    for ssl_mode in ssl_modes:
        try:
            logger.info(f"Testing SSL mode: {ssl_mode}")
            
            # Create test connection string
            if 'sslmode=' in database_url:
                test_url = database_url.replace('sslmode=' + database_url.split('sslmode=')[1].split('&')[0], f'sslmode={ssl_mode}')
            else:
                separator = '&' if '?' in database_url else '?'
                test_url = f"{database_url}{separator}sslmode={ssl_mode}"
            
            # Test connection
            from sqlalchemy import create_engine, text
            engine = create_engine(
                test_url,
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args={
                    'connect_timeout': 10,
                    'application_name': 'ssl_test'
                }
            )
            
            with engine.connect() as conn:
                result = conn.execute(text('SELECT 1'))
                logger.info(f"✅ SSL mode '{ssl_mode}' works successfully")
                engine.dispose()
                return ssl_mode
                
        except Exception as e:
            logger.warning(f"❌ SSL mode '{ssl_mode}' failed: {e}")
            continue
    
    logger.error("All SSL modes failed")
    return False

def fix_database_config():
    """Fix database configuration for SSL issues"""
    logger.info("Fixing database configuration...")
    
    # Test current connection
    try:
        from models import db
        with db.engine.connect() as conn:
            conn.execute(db.text('SELECT 1'))
            logger.info("✅ Current database connection works")
            return True
    except Exception as e:
        logger.warning(f"Current connection failed: {e}")
    
    # Try to refresh connections
    try:
        from database_utils import refresh_database_connections
        if refresh_database_connections():
            logger.info("✅ Database connections refreshed successfully")
            return True
    except Exception as e:
        logger.warning(f"Failed to refresh connections: {e}")
    
    return False

def update_environment_ssl():
    """Update environment variables for SSL configuration"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL not set")
        return False
    
    # Check if SSL mode is already set
    if 'sslmode=' in database_url:
        current_ssl = database_url.split('sslmode=')[1].split('&')[0]
        logger.info(f"Current SSL mode: {current_ssl}")
        
        # If it's 'require' and failing, try 'prefer'
        if current_ssl == 'require':
            logger.info("Trying to change SSL mode from 'require' to 'prefer'")
            new_url = database_url.replace('sslmode=require', 'sslmode=prefer')
            
            # Test the new URL
            try:
                from sqlalchemy import create_engine, text
                engine = create_engine(
                    new_url,
                    pool_pre_ping=True,
                    pool_recycle=300
                )
                
                with engine.connect() as conn:
                    conn.execute(text('SELECT 1'))
                    logger.info("✅ New SSL configuration works")
                    engine.dispose()
                    
                    # Update the environment variable
                    os.environ['DATABASE_URL'] = new_url
                    logger.info("Updated DATABASE_URL with new SSL configuration")
                    return True
                    
            except Exception as e:
                logger.warning(f"New SSL configuration failed: {e}")
    
    return False

def main():
    """Main function to fix SSL connections"""
    logger.info("🔧 Starting SSL connection fix...")
    
    # Step 1: Test current SSL configuration
    logger.info("Step 1: Testing current SSL configuration")
    if fix_database_config():
        logger.info("✅ Database connection is working")
        return True
    
    # Step 2: Test different SSL modes
    logger.info("Step 2: Testing different SSL modes")
    working_ssl_mode = test_ssl_connection()
    
    if working_ssl_mode:
        logger.info(f"✅ Found working SSL mode: {working_ssl_mode}")
        
        # Step 3: Update environment configuration
        logger.info("Step 3: Updating environment configuration")
        if update_environment_ssl():
            logger.info("✅ Environment updated successfully")
            
            # Step 4: Test final configuration
            logger.info("Step 4: Testing final configuration")
            if fix_database_config():
                logger.info("🎉 SSL connection issues resolved!")
                return True
    
    # Step 5: Try alternative approach - disable SSL temporarily
    logger.info("Step 5: Trying alternative approach - SSL fallback")
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            # Remove SSL mode completely to allow fallback
            if 'sslmode=' in database_url:
                new_url = database_url.replace('sslmode=' + database_url.split('sslmode=')[1].split('&')[0], '')
                # Clean up any double separators
                new_url = new_url.replace('&&', '&').replace('??', '?')
                new_url = new_url.rstrip('&?')
                
                os.environ['DATABASE_URL'] = new_url
                logger.info("Temporarily disabled SSL for fallback")
                
                if fix_database_config():
                    logger.info("✅ Connection works without SSL (fallback mode)")
                    return True
    except Exception as e:
        logger.warning(f"SSL fallback failed: {e}")
    
    logger.error("❌ Failed to resolve SSL connection issues")
    return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 SSL connection issues have been resolved!")
        print("You can now restart your application.")
    else:
        print("\n❌ SSL connection issues could not be resolved automatically.")
        print("Please check your database configuration and network settings.")
    
    sys.exit(0 if success else 1)
