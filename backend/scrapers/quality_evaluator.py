"""
Quality Evaluator Module
Evaluates HTML DOM structure, text word counts, anti-bot challenge markers,
and client-side JS hydration signals to produce multi-dimensional QualityMetrics.
"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from scrapers.models import QualityMetrics
from core.logging_config import get_logger

logger = get_logger(__name__)

CHALLENGE_PATTERNS = [
    r"checking your browser before accessing",
    r"please enable javascript to view",
    r"cloudflare turnstile",
    r"cf-browser-verification",
    r"just a moment\.\.\.",
    r"attention required!\s*\|\s*cloudflare",
    r"access denied",
    r"403 forbidden",
    r"pardon our interruption",
]

HYDRATION_PATTERNS = [
    r"__next_data__",
    r"__nuxt__",
    r"window\.__initial_state__",
    r"<div id=[\"'](root|app)[\"']>\s*</div>",
    r"enable javascript to run this app",
]

DEFAULT_BLOCKED_TITLES = {
    "access denied", "403 forbidden", "404 not found", "just a moment...",
    "attention required!", "untitled", "site error", "security check"
}


class QualityEvaluator:
    """
    Evaluates multi-dimensional quality metrics for extracted web content.
    """
    def evaluate(self, html: str, clean_text: str, title: Optional[str] = None) -> QualityMetrics:
        notes: List[str] = []

        html_lower = html.lower() if html else ""
        text_lower = clean_text.lower() if clean_text else ""

        # 1. Challenge & Anti-Bot Detection
        challenge_detected = False
        for pattern in CHALLENGE_PATTERNS:
            if re.search(pattern, html_lower) or re.search(pattern, text_lower):
                challenge_detected = True
                notes.append(f"Anti-bot challenge pattern matched: {pattern}")
                break

        # 2. JS Hydration Detection
        hydration_detected = False
        for pattern in HYDRATION_PATTERNS:
            if re.search(pattern, html_lower):
                hydration_detected = True
                notes.append(f"JS hydration marker detected: {pattern}")
                break

        # 3. Title Evaluation & Metadata Completeness
        clean_title = title.strip() if title else ""
        has_title = bool(clean_title) and clean_title.lower() not in DEFAULT_BLOCKED_TITLES
        if not has_title:
            notes.append("Missing or invalid page title")

        metadata_score = 100 if has_title else 30

        # 4. Content Density Calculation
        words = clean_text.split() if clean_text else []
        word_count = len(words)

        if word_count > 300:
            content_density = 100
        elif word_count > 150:
            content_density = 80
        elif word_count > 50:
            content_density = 50
        else:
            content_density = 10

        # 5. Structure Quality Evaluation
        has_article_body = False
        structure_quality = 50
        if html:
            soup = BeautifulSoup(html[:100000], 'html.parser')
            has_article = bool(soup.find(['article', 'main']))
            has_h1 = bool(soup.find('h1'))
            has_paragraphs = len(soup.find_all('p')) > 2

            if has_article or (has_h1 and has_paragraphs):
                has_article_body = True
                structure_quality = 100
            elif has_h1 or has_paragraphs:
                structure_quality = 70
            else:
                notes.append("Lacks semantic structure (no <article>, <main>, <h1>, or paragraphs)")
                structure_quality = 30

        # Overall Score calculation weighted across dimensions
        if challenge_detected:
            overall_score = 10
        elif hydration_detected and word_count < 100:
            overall_score = 25
        else:
            overall_score = int(0.4 * content_density + 0.3 * metadata_score + 0.3 * structure_quality)

        overall_score = max(0, min(100, overall_score))

        logger.info(
            "quality_evaluation_complete",
            extra={
                "overall_score": overall_score,
                "content_density": content_density,
                "metadata_completeness": metadata_score,
                "structure_quality": structure_quality,
                "word_count": word_count,
                "challenge_detected": challenge_detected,
                "hydration_detected": hydration_detected
            }
        )

        return QualityMetrics(
            score=overall_score,
            has_title=has_title,
            has_article_body=has_article_body,
            word_count=word_count,
            hydration_detected=hydration_detected,
            challenge_detected=challenge_detected,
            content_density=content_density,
            metadata_completeness=metadata_score,
            structure_quality=structure_quality,
            evaluation_notes=notes
        )
