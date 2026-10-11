"""
Decision Engine Module
Determines explicit pipeline execution decisions (ACCEPT, ESCALATE, RETRY, FAIL)
based on QualityMetrics and the current fetch strategy.
"""

from typing import Optional
from scrapers.models import QualityMetrics, Decision
from core.logging_config import get_logger

logger = get_logger(__name__)

QUALITY_ACCEPT_THRESHOLD = 70


class DecisionEngine:
    """
    Evaluates QualityMetrics and current strategy to make explicit escalation decisions.
    """
    def __init__(self, quality_threshold: int = QUALITY_ACCEPT_THRESHOLD):
        self.quality_threshold = quality_threshold

    def evaluate(self, metrics: QualityMetrics, current_strategy: str) -> Decision:
        """
        Determine pipeline action for a plain-HTTP fetch:
        - ACCEPT: quality is sufficient, or there is enough content to use best-effort.
        - FAIL: a bot-challenge page was returned, or there is too little content.
        """
        if metrics.challenge_detected:
            return Decision(action="FAIL", reason="challenge_page_returned", next_strategy=None)

        if metrics.score >= self.quality_threshold:
            return Decision(action="ACCEPT", reason="quality_metrics_passed", next_strategy=None)

        if metrics.word_count > 50:
            return Decision(action="ACCEPT", reason="best_effort_accepted", next_strategy=None)

        return Decision(action="FAIL", reason="insufficient_content", next_strategy=None)
