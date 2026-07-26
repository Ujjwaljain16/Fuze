"""
Acquisition Domain Models & DTOs
Immutable frozen dataclasses representing data transformations across the Content Acquisition Pipeline.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


@dataclass(frozen=True)
class FetchMetadata:
    """Provenance and execution metrics for a fetch attempt."""
    strategy: str  # "HTTP", "STEALTH", "DYNAMIC"
    attempts: int
    http_status: int
    redirected: bool
    redirect_chain: List[str] = field(default_factory=list)
    cache_hit: bool = False
    robots_checked: bool = True
    scrapling_version: str = "0.2.0"
    fetch_latency_ms: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class RawFetchResult:
    """Immutable result of raw network acquisition."""
    url: str
    final_url: str
    http_status: int
    headers: Dict[str, str]
    raw_content: bytes
    fetch_metadata: FetchMetadata


@dataclass(frozen=True)
class ExtractionResult:
    """Result of an individual ExtractorPlugin execution."""
    plugin_name: str
    success: bool
    confidence: float  # 0.0 to 1.0
    extracted_data: Dict[str, Any]
    plugin_version: str = "1.0.0"


@dataclass(frozen=True)
class ParsedDocument:
    """Intermediate immutable document produced by the Extractor Pipeline."""
    url: str
    raw_title: Optional[str]
    raw_html: str
    clean_text: str
    markdown_body: str
    plugin_results: List[ExtractionResult] = field(default_factory=list)
    fetch_metadata: Optional[FetchMetadata] = None


@dataclass(frozen=True)
class NormalizedMetadata:
    """Normalized metadata independent of raw providers with confidence and per-field provenance."""
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    published_at: Optional[str] = None
    canonical_url: Optional[str] = None
    language: Optional[str] = None
    reading_time_minutes: int = 0
    keywords: List[str] = field(default_factory=list)
    field_provenance: Dict[str, str] = field(default_factory=dict)  # e.g., {"title": "json_ld", "author": "opengraph"}
    field_confidence: Dict[str, float] = field(default_factory=dict)  # e.g., {"title": 0.95, "author": 0.8}


@dataclass(frozen=True)
class NormalizedDocument:
    """Normalized document before quality evaluation."""
    url: str
    canonical_url: Optional[str]
    markdown_content: str
    metadata: NormalizedMetadata
    provider_raw_payload: Dict[str, Any]  # Stored in bookmark_metadata table
    fetch_metadata: FetchMetadata


@dataclass(frozen=True)
class QualityMetrics:
    """Multi-dimensional metrics evaluated by QualityEvaluator."""
    score: int  # 0 to 100 overall score
    has_title: bool
    has_article_body: bool
    word_count: int
    hydration_detected: bool
    challenge_detected: bool
    content_density: int = 100  # 0-100 score for content vs boilerplate
    metadata_completeness: int = 100  # 0-100 score for present metadata fields
    structure_quality: int = 100  # 0-100 score for semantic HTML structure
    evaluation_notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Decision:
    """Action decision produced by DecisionEngine."""
    action: str  # "ACCEPT", "RETRY", "ESCALATE", "FAIL"
    reason: str  # e.g., "quality_metrics_passed", "challenge_detected", "hydration_detected"
    next_strategy: Optional[str] = None  # "STEALTH", "DYNAMIC"


@dataclass(frozen=True)
class ContentDocument:
    """Canonical immutable document output of the Content Acquisition Pipeline."""
    url: str
    canonical_url: Optional[str]
    content_hash: str  # SHA-256 hex string
    markdown_content: str
    metadata: NormalizedMetadata
    provider_raw_payload: Dict[str, Any]
    quality_metrics: QualityMetrics
    fetch_metadata: FetchMetadata
    extractor_version: str = "2.0.0"
    plugin_versions: Dict[str, str] = field(default_factory=dict)  # e.g., {"opengraph": "1.0.0"}


def compute_content_hash(text: Optional[str]) -> str:
    """
    Compute deterministic SHA-256 content hash of normalized Markdown text.
    Strips leading/trailing whitespace to avoid false positive hash changes.
    """
    if not text:
        return hashlib.sha256(b"").hexdigest()
    normalized_text = text.strip()
    return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
