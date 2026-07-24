"""
Task Queue Service using RQ (Redis Queue)
Handles asynchronous background job processing for bookmark content extraction
with lazy Redis initialization, thread safety, job deduplication, and error sanitization.
"""

import os
import ssl
import uuid
import threading
from typing import Optional, Dict, Any
from rq import Queue, Retry
from rq.job import Job
from redis import Redis, RedisError
from core.logging_config import get_logger

logger = get_logger(__name__)

_redis_conn: Optional[Redis] = None
_connection_lock = threading.Lock()


def _create_redis_connection() -> Optional[Redis]:
    """Create and return a configured Redis connection instance for RQ."""
    redis_url = os.environ.get('REDIS_URL')

    if redis_url:
        if 'upstash.io' in redis_url and redis_url.startswith('redis://'):
            redis_url = redis_url.replace('redis://', 'rediss://', 1)
            logger.info("rq_redis_url_tls_conversion", extra={"original": "redis://upstash.io", "updated": "rediss://upstash.io"})

        try:
            conn_params = {
                'decode_responses': False,
                'socket_connect_timeout': 10,
                'socket_timeout': 30,
                'socket_keepalive': True,
                'health_check_interval': 30
            }

            if redis_url.startswith('rediss://'):
                allow_unverified = os.environ.get('REDIS_ALLOW_UNVERIFIED_SSL', 'false').lower() == 'true'
                if allow_unverified:
                    conn_params['ssl_cert_reqs'] = ssl.CERT_NONE
                    conn_params['ssl_check_hostname'] = False
                else:
                    conn_params['ssl_cert_reqs'] = ssl.CERT_REQUIRED
                    conn_params['ssl_check_hostname'] = True

            client = Redis.from_url(redis_url, **conn_params)
            client.ping()
            logger.info("rq_redis_connection_established")
            return client
        except Exception as e:
            logger.error("rq_redis_conn_url_failed", extra={"error": str(e)})
            return None

    redis_host = os.environ.get('REDIS_HOST')
    if not redis_host:
        if os.environ.get('FLASK_ENV') == 'production':
            logger.error("rq_redis_host_missing_in_production")
            return None
        redis_host = 'localhost'

    redis_port = int(os.environ.get('REDIS_PORT', 6379))
    redis_db = int(os.environ.get('REDIS_DB', 0))
    redis_password = os.environ.get('REDIS_PASSWORD')
    use_ssl = os.environ.get('REDIS_SSL', 'false').lower() == 'true'

    if not use_ssl and any(provider in redis_host for provider in ['upstash.io', 'redislabs.com', 'redis.cache']):
        use_ssl = True

    connection_params = {
        'host': redis_host,
        'port': redis_port,
        'db': redis_db,
        'password': redis_password,
        'decode_responses': False,
        'socket_connect_timeout': 10,
        'socket_timeout': 30,
        'socket_keepalive': True,
        'health_check_interval': 30
    }

    if use_ssl:
        connection_params['ssl'] = True
        allow_unverified = os.environ.get('REDIS_ALLOW_UNVERIFIED_SSL', 'false').lower() == 'true'
        if allow_unverified:
            connection_params['ssl_cert_reqs'] = ssl.CERT_NONE
            connection_params['ssl_check_hostname'] = False
        else:
            connection_params['ssl_cert_reqs'] = ssl.CERT_REQUIRED
            connection_params['ssl_check_hostname'] = True

    try:
        client = Redis(**connection_params)
        client.ping()
        logger.info("rq_redis_connection_established")
        return client
    except Exception as e:
        logger.error("rq_redis_conn_params_failed", extra={"error": str(e)})
        return None


def get_redis_connection() -> Optional[Redis]:
    """Lazy thread-safe access to Redis connection."""
    global _redis_conn
    if _redis_conn is not None:
        return _redis_conn

    with _connection_lock:
        if _redis_conn is None:
            _redis_conn = _create_redis_connection()
        return _redis_conn


def get_queue(name: str = 'default') -> Optional[Queue]:
    """Get fresh Queue instance for the specified queue name."""
    conn = get_redis_connection()
    if not conn:
        return None
    try:
        return Queue(name, connection=conn)
    except Exception as e:
        logger.error("rq_queue_creation_failed", extra={"name": name, "error": str(e)})
        return None


def enqueue_bookmark_processing(bookmark_id: int, url: str, user_id: int, queue_name: str = 'default') -> Optional[Job]:
    """
    Enqueue a bookmark processing task asynchronously using RQ.
    Prevents duplicate enqueueing and avoids job ID collisions.
    """
    queue = get_queue(queue_name)
    if not queue:
        logger.warning("rq_queue_unavailable", extra={"bookmark_id": bookmark_id})
        return None

    try:
        from services.bookmark_processing_service import process_bookmark_content_task

        unique_job_id = f"bookmark_process_{bookmark_id}_{uuid.uuid4().hex[:8]}"

        job = queue.enqueue(
            process_bookmark_content_task,
            bookmark_id,
            url,
            user_id,
            job_timeout='10m',
            retry=Retry(max=2, interval=[60, 300]),
            job_id=unique_job_id
        )

        logger.info("rq_job_enqueued", extra={"job_id": job.id, "bookmark_id": bookmark_id, "user_id": user_id})
        return job
    except Exception as e:
        logger.error("rq_job_enqueue_failed", extra={"bookmark_id": bookmark_id, "error": str(e)})
        return None


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get status of a job safely without exposing sensitive stack trace info or massive payloads.
    """
    conn = get_redis_connection()
    if not conn or not job_id:
        return None

    try:
        job = Job.fetch(job_id, connection=conn)
        failed_reason = None
        if job.is_failed and job.exc_info:
            lines = str(job.exc_info).strip().splitlines()
            failed_reason = lines[-1] if lines else "Task execution failed"

        result_summary = None
        if job.result:
            result_summary = str(job.result)[:200]

        return {
            'id': job.id,
            'status': job.get_status(),
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
            'result_summary': result_summary,
            'failed_reason': failed_reason
        }
    except Exception as e:
        logger.error("rq_job_status_fetch_failed", extra={"job_id": job_id, "error": str(e)})
        return None


def is_rq_available() -> bool:
    """Check if RQ is connected and operational by verifying connection ping."""
    conn = get_redis_connection()
    if not conn:
        return False
    try:
        return bool(conn.ping())
    except RedisError:
        return False
    except Exception:
        return False
