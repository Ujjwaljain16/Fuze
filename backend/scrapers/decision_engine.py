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
        Determine pipeline action:
        - ACCEPT: Quality is sufficient, no further fetching needed.
        - ESCALATE: Quality is insufficient or challenge/hydration detected; escalate to next tier.
        - FAIL: Max strategy tier reached and quality remains unacceptable.
        """
        # Case 1: Anti-bot challenge or Cloudflare block detected
        if metrics.challenge_detected:
            if current_strategy == "HTTP":
                return Decision(action="ESCALATE", reason="challenge_detected", next_strategy="STEALTH")
            elif current_strategy == "STEALTH":
                return Decision(action="ESCALATE", reason="stealth_blocked_challenge_persists", next_strategy="DYNAMIC")
            else:
                return Decision(action="FAIL", reason="challenge_failed_all_tiers", next_strategy=None)

        # Case 2: Client-side JS Hydration required (empty body)
        if metrics.hydration_detected and metrics.word_count < 150:
            if current_strategy == "HTTP":
                return Decision(action="ESCALATE", reason="hydration_detected_http", next_strategy="STEALTH")
            elif current_strategy == "STEALTH":
                return Decision(action="ESCALATE", reason="hydration_requires_dynamic_js", next_strategy="DYNAMIC")

        # Case 3: Quality score below threshold or missing title/content
        if metrics.score < self.quality_threshold or not metrics.has_title or metrics.word_count < 100:
            if current_strategy == "HTTP":
                return Decision(action="ESCALATE", reason="quality_below_threshold_http", next_strategy="STEALTH")
            elif current_strategy == "STEALTH":
                return Decision(action="ESCALATE", reason="quality_below_threshold_stealth", next_strategy="DYNAMIC")

        # Case 4: Quality metrics acceptable
        if metrics.score >= self.quality_threshold:
            return Decision(action="ACCEPT", reason="quality_metrics_passed", next_strategy=None)

        # Case 5: Final fallback on Dynamic strategy completion
        if current_strategy == "DYNAMIC":
            if metrics.word_count > 50:
                return Decision(action="ACCEPT", reason="dynamic_best_effort_accepted", next_strategy=None)
            return Decision(action="FAIL", reason="dynamic_insufficient_content", next_strategy=None)

        return Decision(action="ACCEPT", reason="default_accepted", next_strategy=None)
