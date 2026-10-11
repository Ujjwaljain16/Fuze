"""
Decision Engine Module
Determines explicit pipeline execution decisions (ACCEPT, ESCALATE, FAIL) from the QualityMetrics
of a fetch, or from the way a fetch failed, and the tiers still left in the strategy plan.

Tiers (see docs/CONTENT_ACQUISITION.md):
- HTTP: our own fetch of the page.
- READER: a remote reader service that renders JavaScript. Worth trying when our fetch came back
  thin, as an empty JS shell, or as a bot-challenge page.
- ARCHIVE: a Wayback Machine snapshot. Only for pages that are gone (404/410) or blocked; a thin
  live page would almost always be just as thin in the archive.

With no later tier in the plan, every decision is the same as the plain-HTTP engine's.
"""

from typing import Optional, Sequence
from scrapers.models import QualityMetrics, Decision
from core.logging_config import get_logger

logger = get_logger(__name__)

QUALITY_ACCEPT_THRESHOLD = 70
# At or below this many words the page is "thin": not enough to keep as best effort.
THIN_WORD_COUNT = 50
# A page that is a JS hydration shell with fewer words than this was not rendered.
HYDRATION_SHELL_WORDS = 100

READER = "READER"
ARCHIVE = "ARCHIVE"

BLOCKED_STATUSES = (401, 403)
GONE_STATUSES = (404, 410)


class DecisionEngine:
    """
    Evaluates QualityMetrics (or a failed fetch) against the remaining tiers.
    """
    def __init__(self, quality_threshold: int = QUALITY_ACCEPT_THRESHOLD):
        self.quality_threshold = quality_threshold

    @staticmethod
    def _escalate(reason: str, remaining: Sequence[str], *tiers: str) -> Optional[Decision]:
        for tier in tiers:
            if tier in remaining:
                return Decision(action="ESCALATE", reason=reason, next_strategy=tier)
        return None

    def evaluate(self, metrics: QualityMetrics, current_strategy: str,
                 remaining: Sequence[str] = ()) -> Decision:
        """
        Decide on a fetch that produced a page:
        - ACCEPT: quality is sufficient, or there is enough content to use best-effort.
        - ESCALATE: a challenge page, a hydration-only shell or too little content, and a later
          tier can do better.
        - FAIL: as above with nothing left to try.
        """
        if metrics.challenge_detected:
            return (self._escalate("challenge_page_returned", remaining, READER, ARCHIVE)
                    or Decision(action="FAIL", reason="challenge_page_returned", next_strategy=None))

        if metrics.score >= self.quality_threshold:
            return Decision(action="ACCEPT", reason="quality_metrics_passed", next_strategy=None)

        if metrics.hydration_detected and metrics.word_count < HYDRATION_SHELL_WORDS:
            escalation = self._escalate("hydration_only", remaining, READER)
            if escalation:
                return escalation

        if metrics.word_count > THIN_WORD_COUNT:
            return Decision(action="ACCEPT", reason="best_effort_accepted", next_strategy=None)

        return (self._escalate("insufficient_content", remaining, READER)
                or Decision(action="FAIL", reason="insufficient_content", next_strategy=None))

    def evaluate_failure(self, http_status: Optional[int], challenge: bool = False,
                         remaining: Sequence[str] = (), page_blocked: bool = False) -> Decision:
        """
        Decide on a fetch that produced no usable page.

        `http_status` is the target page's status as the tier saw it (None: no answer at all,
        e.g. a timeout). `challenge`: the error page was a bot challenge. `page_blocked`: an
        earlier tier already saw the page blocked.

        Server errors, rate limits and timeouts are not escalated: they are retried later, and
        the reader would usually hit the same wall.
        """
        blocked = challenge or page_blocked or http_status in BLOCKED_STATUSES
        if blocked:
            escalation = self._escalate("blocked", remaining, READER, ARCHIVE)
            if escalation:
                return escalation
        if http_status in GONE_STATUSES:
            escalation = self._escalate("gone", remaining, ARCHIVE)
            if escalation:
                return escalation
        return Decision(action="FAIL", reason="fetch_failed", next_strategy=None)
