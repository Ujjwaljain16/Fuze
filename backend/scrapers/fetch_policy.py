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

DEFAULT_STRATEGY_PLAN = ["HTTP", "STEALTH", "DYNAMIC"]

DEFAULT_DOMAIN_POLICIES: Dict[str, List[str]] = {
    "github.com": ["STEALTH", "DYNAMIC"],
    "leetcode.com": ["STEALTH", "DYNAMIC"],
    "medium.com": ["STEALTH", "DYNAMIC"],
    "dev.to": ["STEALTH", "DYNAMIC"],
    "stackoverflow.com": ["STEALTH", "DYNAMIC"],
    "flaviocopes.com": ["STEALTH"],
    "codeforces.com": ["STEALTH"],
    "devdocs.io": ["DYNAMIC"],
    "andreasbm.github.io": ["DYNAMIC"],
    "dashboard.render.com": ["DYNAMIC"],
    "neetcode.io": ["DYNAMIC"],
    "masterjs.vercel.app": ["DYNAMIC"],
    "openml.org": ["DYNAMIC"],
    "www.openml.org": ["DYNAMIC"],
}


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
        """
        Return the candidate fetch strategy plan for a given URL.
        Evaluates static overrides first, then dynamic runtime metrics, then default plan.
        """
        domain = self._get_domain(url)

        # 1. Static Domain Policy Check
        for policy_domain, plan in self.domain_policies.items():
            clean_policy_domain = policy_domain[4:] if policy_domain.startswith("www.") else policy_domain
            if domain == clean_policy_domain or domain.endswith(f".{clean_policy_domain}"):
                # Check runtime adaptation: If HTTP has succeeded 5+ times consecutively on a STEALTH domain, downgrade to HTTP fast-path
                if self._redis and plan[0] != "HTTP":
                    try:
                        http_successes = int(self._redis.get(f"fuze:policy:{domain}:HTTP:success") or 0)
                        http_failures = int(self._redis.get(f"fuze:policy:{domain}:HTTP:failure") or 0)
                        if http_successes >= 5 and http_failures == 0:
                            logger.info("dynamic_policy_downgrade_to_http", extra={"domain": domain})
                            return ["HTTP"] + list(plan)
                    except Exception:
                        pass
                logger.info("fetch_policy_matched_static", extra={"url": url, "domain": domain, "plan": plan})
                return list(plan)

        # 2. Dynamic Policy Check for standard domains (promote to STEALTH if HTTP repeatedly fails)
        if self._redis:
            try:
                http_failures = int(self._redis.get(f"fuze:policy:{domain}:HTTP:failure") or 0)
                if http_failures >= 3:
                    logger.info("dynamic_policy_promote_to_stealth", extra={"domain": domain, "http_failures": http_failures})
                    return ["STEALTH", "DYNAMIC", "HTTP"]
            except Exception:
                pass

        logger.debug("fetch_policy_default", extra={"url": url, "plan": DEFAULT_STRATEGY_PLAN})
        return list(DEFAULT_STRATEGY_PLAN)
