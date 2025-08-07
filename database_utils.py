"""
Database utilities for handling connection issues and retries
"""

import time
import logging
from functools import wraps
from sqlalchemy.exc import OperationalError, DisconnectionError
from sqlalchemy import text
from models import db

logger = logging.getLogger(__name__)

def retry_on_connection_error(max_retries=3, delay=1):
    """
    Decorator to retry database operations on connection errors
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DisconnectionError) as e:
                    last_exception = e
                    logger.warning(f"Database connection error on attempt {attempt + 1}/{max_retries}: {e}")
                    
                    if attempt < max_retries - 1:
                        # Wait before retrying, with exponential backoff
                        wait_time = delay * (2 ** attempt)
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        
                        # Try to refresh the connection
                        try:
                            db.session.rollback()
                            db.session.close()
                            db.session.remove()
                        except Exception as rollback_error:
                            logger.warning(f"Error during session cleanup: {rollback_error}")
            
            # If we get here, all retries failed
            logger.error(f"All {max_retries} attempts failed. Last error: {last_exception}")
            raise last_exception
            
        return wrapper
    return decorator

def check_database_connection():
    """
    Check if database connection is healthy
    """
    try:
        # Try a simple query
        result = db.session.execute(text('SELECT 1'))
        result.fetchone()
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

def ensure_database_connection():
    """
    Ensure database connection is available, retry if needed
    """
    if not check_database_connection():
        logger.warning("Database connection lost, attempting to reconnect...")
        
        try:
            # Close existing sessions
            db.session.rollback()
            db.session.close()
            db.session.remove()
            
            # Wait a moment
            time.sleep(1)
            
            # Try to reconnect
            if check_database_connection():
                logger.info("Database reconnection successful")
                return True
            else:
                logger.error("Database reconnection failed")
                return False
                
        except Exception as e:
            logger.error(f"Error during database reconnection: {e}")
            return False
    
    return True

def safe_db_operation(operation_func, *args, **kwargs):
    """
    Safely execute a database operation with retry logic
    """
    @retry_on_connection_error(max_retries=3, delay=1)
    def execute_operation():
        return operation_func(*args, **kwargs)
    
    return execute_operation()

def get_db_session():
    """
    Get a database session with connection health check
    """
    if not ensure_database_connection():
        raise OperationalError("Unable to establish database connection", None, None)
    
    return db.session 