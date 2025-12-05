"""
Task Queue Service using RQ (Redis Queue)
Handles asynchronous background job processing for bookmark content extraction
"""

import os
import ssl
import logging
from typing import Optional
from rq import Queue, Connection, Retry
from rq.job import Job
from redis import Redis
from utils.redis_utils import redis_cache

logger = logging.getLogger(__name__)

# Get Redis connection for RQ
def get_redis_connection():
    """Get Redis connection for RQ queue"""
    # RQ needs a Redis connection with decode_responses=False for binary data
    # Create connection from environment variables (same config as redis_cache)
    redis_url = os.environ.get('REDIS_URL')
    
    if redis_url:
        # Convert redis:// to rediss:// for Upstash TLS
        if 'upstash.io' in redis_url and redis_url.startswith('redis://'):
            redis_url = redis_url.replace('redis://', 'rediss://', 1)
            logger.info("Converted Upstash URL to use TLS (rediss://)")
        
        # Use REDIS_URL if available
        try:
            # Base connection parameters
            conn_params = {
                'decode_responses': False,
                'socket_connect_timeout': 30,
                'socket_timeout': 60,
                'socket_keepalive': True,
                'health_check_interval': 30,
                'retry_on_timeout': True,
                'retry_on_error': [ConnectionError, TimeoutError]
            }
            
            # Add SSL parameters for rediss:// URLs
            if redis_url.startswith('rediss://'):
                conn_params['ssl_cert_reqs'] = ssl.CERT_NONE
                conn_params['ssl_check_hostname'] = False
            
            return Redis.from_url(redis_url, **conn_params)
        except Exception as e:
            logger.warning(f"Failed to create Redis connection from URL: {e}")
    
    # Use individual connection parameters
    redis_host = os.environ.get('REDIS_HOST', 'localhost')
    redis_port = int(os.environ.get('REDIS_PORT', 6379))
    redis_db = int(os.environ.get('REDIS_DB', 0))
    redis_password = os.environ.get('REDIS_PASSWORD')
    use_ssl = os.environ.get('REDIS_SSL', 'false').lower() == 'true'
    
    # Auto-detect TLS for cloud providers
    if not use_ssl and any(provider in redis_host for provider in ['upstash.io', 'redislabs.com', 'redis.cache']):
        use_ssl = True
    
    connection_params = {
        'host': redis_host,
        'port': redis_port,
        'db': redis_db,
        'password': redis_password,
        'decode_responses': False,
        'socket_connect_timeout': 30,
        'socket_timeout': 60,
        'socket_keepalive': True,
        'health_check_interval': 30,
        'retry_on_timeout': True,
        'retry_on_error': [ConnectionError, TimeoutError]
    }
    
    if use_ssl:
        connection_params['ssl'] = True
        connection_params['ssl_cert_reqs'] = ssl.CERT_NONE
        connection_params['ssl_check_hostname'] = False
    
    try:
        return Redis(**connection_params)
    except Exception as e:
        logger.warning(f"Failed to create Redis connection: {e}")
        # Final fallback: basic local connection
        return Redis(host='localhost', port=6379, db=0, decode_responses=False)

# Create Redis connection for RQ
redis_conn = None
try:
    redis_conn = get_redis_connection()
    # Test connection
    redis_conn.ping()
    logger.info("RQ Redis connection established successfully")
except Exception as e:
    logger.warning(f"RQ Redis connection failed: {e}. Background jobs will use fallback threading.")
    redis_conn = None

# Create queue instances
# 'default' queue for normal priority tasks
# 'high' queue for urgent tasks (optional, can use same queue)
default_queue = None
high_queue = None

if redis_conn:
    try:
        default_queue = Queue('default', connection=redis_conn)
        high_queue = Queue('high', connection=redis_conn)
        logger.info("RQ queues initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RQ queues: {e}")
        default_queue = None
        high_queue = None

def enqueue_bookmark_processing(bookmark_id: int, url: str, user_id: int, queue_name: str = 'default') -> Optional[Job]:
    """
    Enqueue a bookmark processing task
    
    Args:
        bookmark_id: ID of the bookmark to process
        url: URL to scrape and process
        user_id: ID of the user who owns the bookmark
        queue_name: Queue name ('default' or 'high')
    
    Returns:
        Job instance if enqueued successfully, None otherwise
    """
    if not redis_conn or not default_queue:
        logger.warning("RQ not available, falling back to threading")
        return None
    
    try:
        # Import the task function (avoid circular imports)
        # Use string reference for better RQ compatibility
        from blueprints.bookmarks import process_bookmark_content_task
        
        # Select queue
        queue = high_queue if queue_name == 'high' else default_queue
        
        # Enqueue the task with retry logic
        # Retry up to 2 times with exponential backoff
        job = queue.enqueue(
            process_bookmark_content_task,  # Function reference
            bookmark_id,
            url,
            user_id,
            job_timeout='10m',  # 10 minute timeout for scraping/embedding
            retry=Retry(max=2, interval=[60, 300]),  # Retry after 1min, then 5min
            job_id=f"bookmark_process_{bookmark_id}_{user_id}"  # Unique job ID
        )
        
        logger.info(f"Enqueued bookmark processing job {job.id} for bookmark {bookmark_id}")
        return job
    except Exception as e:
        logger.error(f"Failed to enqueue bookmark processing job: {e}", exc_info=True)
        return None

def get_job_status(job_id: str) -> Optional[dict]:
    """
    Get status of a job
    
    Args:
        job_id: Job ID
    
    Returns:
        Dictionary with job status info or None if job not found
    """
    if not redis_conn:
        return None
    
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        return {
            'id': job.id,
            'status': job.get_status(),
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
            'result': str(job.result) if job.result else None,
            'exc_info': job.exc_info if job.is_failed else None
        }
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        return None

def is_rq_available() -> bool:
    """Check if RQ is available and working"""
    return redis_conn is not None and default_queue is not None

