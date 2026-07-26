"""
Robots Manager Module
Fetches, caches, and evaluates target domain robots.txt rules to ensure compliance.
"""

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import requests
from typing import Optional
from utils.redis_utils import get_redis_client
from core.logging_config import get_logger

logger = get_logger(__name__)

ROBOTS_CACHE_TTL = 86400  # 24 Hours
DEFAULT_USER_AGENT = "FUZEBot/2.0 (+https://fuze.app/bot)"


class RobotsManager:
    """
    Parses, caches, and checks target domain robots.txt compliance.
    """
    def __init__(self, user_agent: str = DEFAULT_USER_AGENT):
        self.user_agent = user_agent
        self._redis = get_redis_client()

    def _get_robots_url(self, target_url: str) -> str:
        parsed = urlparse(target_url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def can_fetch(self, target_url: str, user_agent: Optional[str] = None) -> bool:
        """
        Check if user agent is permitted to fetch target_url by robots.txt rules.
        Defaults to True if robots.txt cannot be fetched or parsed.
        """
        agent = user_agent or self.user_agent
        robots_url = self._get_robots_url(target_url)
        domain = urlparse(target_url).netloc.lower()

        robots_txt_content = self._get_cached_robots_txt(domain)
        if robots_txt_content is None:
            robots_txt_content = self._fetch_robots_txt(robots_url)
            if robots_txt_content is not None:
                self._cache_robots_txt(domain, robots_txt_content)

        if not robots_txt_content:
            # If robots.txt doesn't exist or failed to load, allow fetch by default
            return True

        try:
            parser = RobotFileParser()
            parser.parse(robots_txt_content.splitlines())
            allowed = parser.can_fetch(agent, target_url)
            if not allowed:
                logger.warning("robots_txt_disallowed", extra={"url": target_url, "user_agent": agent})
            return allowed
        except Exception as e:
            logger.warning("robots_txt_parse_error", extra={"url": target_url, "error": str(e)})
            return True

    def _fetch_robots_txt(self, robots_url: str) -> Optional[str]:
        try:
            resp = requests.get(robots_url, timeout=5, headers={"User-Agent": self.user_agent})
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            logger.debug("robots_txt_fetch_failed", extra={"robots_url": robots_url, "error": str(e)})
        return None

    def _get_cached_robots_txt(self, domain: str) -> Optional[str]:
        if not self._redis:
            return None
        try:
            return self._redis.get(f"fuze:robots_txt:{domain}")
        except Exception:
            return None

    def _cache_robots_txt(self, domain: str, content: str):
        if not self._redis:
            return
        try:
            self._redis.setex(f"fuze:robots_txt:{domain}", ROBOTS_CACHE_TTL, content)
        except Exception as e:
            logger.warning("robots_txt_cache_error", extra={"domain": domain, "error": str(e)})
