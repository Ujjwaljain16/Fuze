"""
Fetch Policy Module
Provides configurable static per-domain policies as well as runtime dynamic policy adaptation
based on strategy success/failure metrics stored in Redis.
"""

from urllib.parse import urlparse
from typing import Dict, List, Optional
from utils.redis_utils import get_redis_client
from core.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_STRATEGY_PLAN = ["HTTP"]

DEFAULT_DOMAIN_POLICIES: Dict[str, List[str]] = {}


class FetchPolicy:
    """
    Evaluates target domain policies and constructs an ordered list of candidate fetch strategies.
    Supports static domain overrides + dynamic runtime adaptation based on success rates.
    """
    def __init__(self, domain_policies: Optional[Dict[str, List[str]]] = None):
        self.domain_policies = domain_policies if domain_policies is not None else DEFAULT_DOMAIN_POLICIES
        self._redis = get_redis_client()

    def _get_domain(self, url: str) -> str:
        domain = urlparse(url).netloc.lower()
        return domain[4:] if domain.startswith("www.") else domain

    def record_success(self, url: str, strategy: str):
        """Record successful fetch for domain/strategy in Redis for dynamic policy learning."""
        if not self._redis:
            return
        domain = self._get_domain(url)
        try:
            pipe = self._redis.pipeline()
            pipe.incr(f"fuze:policy:{domain}:{strategy}:success")
            pipe.expire(f"fuze:policy:{domain}:{strategy}:success", 86400)
            pipe.execute()
        except Exception as e:
            logger.debug("record_policy_success_failed", extra={"domain": domain, "error": str(e)})

    def record_failure(self, url: str, strategy: str):
        """Record failed fetch for domain/strategy in Redis for dynamic promotion/demotion."""
        if not self._redis:
            return
        domain = self._get_domain(url)
        try:
            pipe = self._redis.pipeline()
            pipe.incr(f"fuze:policy:{domain}:{strategy}:failure")
            pipe.expire(f"fuze:policy:{domain}:{strategy}:failure", 86400)
            pipe.execute()
        except Exception as e:
            logger.debug("record_policy_failure_failed", extra={"domain": domain, "error": str(e)})

    def get_strategy_plan(self, url: str) -> List[str]:
        """Return the ordered fetch strategies for a URL (plain HTTP only)."""
        domain = self._get_domain(url)
        for policy_domain, plan in self.domain_policies.items():
            clean = policy_domain[4:] if policy_domain.startswith("www.") else policy_domain
            if domain == clean or domain.endswith(f".{clean}"):
                return list(plan)
        return list(DEFAULT_STRATEGY_PLAN)
