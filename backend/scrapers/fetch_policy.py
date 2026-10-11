"""
Fetch Policy Module
Provides configurable static per-domain policies as well as runtime dynamic policy adaptation
based on strategy success/failure metrics stored in Redis.
"""

import os
from urllib.parse import urlparse
from typing import Dict, List, Optional
from utils.redis_utils import get_redis_client
from core.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_STRATEGY_PLAN = ["HTTP"]

DEFAULT_DOMAIN_POLICIES: Dict[str, List[str]] = {}


def env_flag(name: str, default: bool) -> bool:
    """A boolean environment switch, read on every call so it can change without a code deploy."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def reader_enabled() -> bool:
    """Tier READER: a remote reader service renders the page. It receives the page's URL only.
    On by default; see docs/CONTENT_ACQUISITION.md for why and how to turn it off."""
    return env_flag("ENABLE_READER_FALLBACK", True)


def archive_enabled() -> bool:
    """Tier ARCHIVE: a Wayback Machine snapshot for pages that are gone or block us.
    The Internet Archive receives the page's URL only."""
    return env_flag("ENABLE_ARCHIVE_FALLBACK", True)


def escalation_tiers() -> List[str]:
    """The tiers that follow our own fetch, in order, as enabled right now."""
    tiers = []
    if reader_enabled():
        tiers.append("READER")
    if archive_enabled():
        tiers.append("ARCHIVE")
    return tiers


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
        """Return the ordered fetch strategies for a URL: our own fetch (or a domain's own plan),
        then whichever escalation tiers are enabled. The decision engine decides at run time
        whether a tier is actually tried."""
        domain = self._get_domain(url)
        plan = list(DEFAULT_STRATEGY_PLAN)
        for policy_domain, domain_plan in self.domain_policies.items():
            clean = policy_domain[4:] if policy_domain.startswith("www.") else policy_domain
            if domain == clean or domain.endswith(f".{clean}"):
                plan = list(domain_plan)
                break
        return plan + [tier for tier in escalation_tiers() if tier not in plan]
