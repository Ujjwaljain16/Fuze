"""
Cache Manager Module
Manages 24-hour Redis raw HTML gzip storage and NormalizedDocument caching for deterministic revalidation.
"""

import gzip
import json
import hashlib
from dataclasses import asdict
from typing import Dict, Optional, Tuple, Any
from utils.redis_utils import get_redis_client
from core.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_HTML_CACHE_TTL = 86400  # 24 Hours in seconds


class CacheManager:
    """
    Manages raw HTML response caching and NormalizedDocument JSON caching in Redis.
    """
    def __init__(self, ttl_seconds: int = DEFAULT_HTML_CACHE_TTL):
        self.ttl_seconds = ttl_seconds
        self._redis = get_redis_client()

    def _make_url_key(self, url: str, prefix: str = "html_cache") -> str:
        url_hash = hashlib.sha256(url.strip().encode('utf-8')).hexdigest()
        return f"fuze:{prefix}:{url_hash}"

    def get_raw_html_cache(self, url: str) -> Optional[bytes]:
        """Fetch gzip-compressed raw HTML from Redis cache if present."""
        if not self._redis:
            return None
        try:
            cached_gzip = self._redis.get(self._make_url_key(url, "html_cache"))
            if cached_gzip and isinstance(cached_gzip, bytes):
                logger.info("html_cache_hit", extra={"url": url})
                return gzip.decompress(cached_gzip)
        except Exception as e:
            logger.warning("html_cache_read_error", extra={"url": url, "error": str(e)})
        return None

    def set_raw_html_cache(self, url: str, raw_bytes: bytes) -> bool:
        """Compress and store raw HTML bytes in Redis with 24h TTL."""
        if not self._redis or not raw_bytes:
            return False
        try:
            compressed = gzip.compress(raw_bytes)
            key = self._make_url_key(url, "html_cache")
            self._redis.setex(key, self.ttl_seconds, compressed)
            logger.info("html_cache_stored", extra={"url": url, "raw_bytes": len(raw_bytes), "compressed_bytes": len(compressed)})
            return True
        except Exception as e:
            logger.warning("html_cache_write_error", extra={"url": url, "error": str(e)})
            return False

    def get_normalized_doc_cache(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch cached NormalizedDocument dict from Redis."""
        if not self._redis:
            return None
        try:
            cached_json = self._redis.get(self._make_url_key(url, "norm_doc"))
            if cached_json:
                data_str = cached_json.decode('utf-8') if isinstance(cached_json, bytes) else str(cached_json)
                logger.info("norm_doc_cache_hit", extra={"url": url})
                return json.loads(data_str)
        except Exception as e:
            logger.warning("norm_doc_cache_read_error", extra={"url": url, "error": str(e)})
        return None

    def set_normalized_doc_cache(self, url: str, norm_doc_data: Dict[str, Any]) -> bool:
        """Store NormalizedDocument dict in Redis with 24h TTL."""
        if not self._redis or not norm_doc_data:
            return False
        try:
            key = self._make_url_key(url, "norm_doc")
            payload = json.dumps(norm_doc_data, default=str)
            self._redis.setex(key, self.ttl_seconds, payload.encode('utf-8'))
            logger.info("norm_doc_cache_stored", extra={"url": url})
            return True
        except Exception as e:
            logger.warning("norm_doc_cache_write_error", extra={"url": url, "error": str(e)})
            return False

    def build_revalidation_headers(self, etag: Optional[str] = None, last_modified: Optional[str] = None) -> Dict[str, str]:
        """Build HTTP headers for conditional GET requests (304 Not Modified)."""
        headers = {}
        if etag:
            headers['If-None-Match'] = etag
        if last_modified:
            headers['If-Modified-Since'] = last_modified
        return headers
