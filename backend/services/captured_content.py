"""
Page content captured by the browser extension.

The extension reads the page the user is looking at (rendered, signed in, after JavaScript ran)
and sends it with the save, so the server doesn't have to fetch it. That covers login-walled and
script-built pages, which a plain HTTP fetch can't read and which the host forbids headless
browsers for.

The payload comes from the client, so it is untrusted: it is size-capped, stripped of control
characters, and the HTML is only ever parsed by the extractor, never stored or served.
"""

import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

from core.logging_config import get_logger

logger = get_logger(__name__)

CAPTURE_STRATEGY = 'EXTENSION'
MAX_CAPTURED_TEXT_BYTES = 500_000
MAX_CAPTURED_HTML_BYTES = 1_000_000
MAX_CANONICAL_URL_BYTES = 2048
# A server fetch replaces captured content only when it has this many times the words.
CLEARLY_BETTER_RATIO = 1.5
# Keep the extractor's Markdown (it keeps headings and code blocks) unless it lost this much of
# the text the user actually saw.
MIN_EXTRACTED_SHARE = 0.6

_LANG = re.compile(r'^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{1,8})*$')
_HORIZONTAL_SPACE = re.compile(r'[^\S\n]+')
_BLANK_RUNS = re.compile(r'\n{3,}')


class CaptureRejected(ValueError):
    """The captured payload is malformed (400) or too large (413)."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class CapturedPage:
    text: str
    html: Optional[str] = None
    canonical_url: Optional[str] = None
    lang: Optional[str] = None


def _utf8_len(value: str) -> int:
    return len(value.encode('utf-8', errors='replace'))


def clean_captured_text(text: str) -> str:
    """Drop control and format characters (keeping newlines and tabs), tidy whitespace."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = ''.join(ch for ch in text if ch in '\n\t' or unicodedata.category(ch)[0] != 'C')
    lines = [_HORIZONTAL_SPACE.sub(' ', line).strip() for line in text.split('\n')]
    return _BLANK_RUNS.sub('\n\n', '\n'.join(lines)).strip()


def _clean_canonical(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or _utf8_len(value) > MAX_CANONICAL_URL_BYTES or any(ch.isspace() for ch in value):
        return None
    parsed = urlparse(value)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return None
    return value


def _clean_lang(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.strip().replace('_', '-')
    if not _LANG.match(value):
        return None
    # saved_content.language holds 10 characters; the primary subtag is what matters for search.
    return value if len(value) <= 10 else value.split('-')[0]


def parse_captured(raw: Any) -> Optional[CapturedPage]:
    """Validate and sanitize the `captured` field of a save request. None when absent."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise CaptureRejected('captured must be an object')

    text = raw.get('text')
    html = raw.get('html')
    if text is None:
        text = ''
    if not isinstance(text, str):
        raise CaptureRejected('captured.text must be a string')
    if html is not None and not isinstance(html, str):
        raise CaptureRejected('captured.html must be a string')

    # Sizes are checked on what was sent, before any cleanup could shrink it.
    if _utf8_len(text) > MAX_CAPTURED_TEXT_BYTES:
        raise CaptureRejected(f'captured.text is larger than {MAX_CAPTURED_TEXT_BYTES} bytes', status=413)
    if html is not None and _utf8_len(html) > MAX_CAPTURED_HTML_BYTES:
        raise CaptureRejected(f'captured.html is larger than {MAX_CAPTURED_HTML_BYTES} bytes', status=413)

    text = clean_captured_text(text)
    html = html.replace('\x00', '') if html else None
    if not text and not (html and html.strip()):
        raise CaptureRejected('captured page has no text')

    return CapturedPage(
        text=text,
        html=html or None,
        canonical_url=_clean_canonical(raw.get('canonical_url')),
        lang=_clean_lang(raw.get('lang')),
    )


def _word_count(text: Optional[str]) -> int:
    return len(text.split()) if text else 0


def build_captured_document(url: str, page: CapturedPage, title: Optional[str] = None):
    """Run the normal extraction and quality stages on captured content, with no network access."""
    from scrapers.extractor_pipeline import ExtractorPipeline
    from scrapers.models import ContentDocument, FetchMetadata, NormalizedMetadata, RawFetchResult, compute_content_hash
    from scrapers.normalizer import MetadataNormalizer
    from scrapers.quality_evaluator import QualityEvaluator

    fetch_meta = FetchMetadata(strategy=CAPTURE_STRATEGY, attempts=0, http_status=200, redirected=False,
                               robots_checked=False)
    plugin_versions = {}
    payload = {}
    body = page.text
    metadata = NormalizedMetadata(title=(title or '').strip() or url)

    if page.html:
        raw = RawFetchResult(url=url, final_url=page.canonical_url or url, http_status=200,
                             headers={'content-type': 'text/html; charset=utf-8'},
                             raw_content=page.html.encode('utf-8', errors='replace'), fetch_metadata=fetch_meta)
        parsed = ExtractorPipeline().process(raw)
        plugin_versions = {r.plugin_name: r.plugin_version for r in parsed.plugin_results}
        normalized = MetadataNormalizer().normalize(parsed)
        payload = dict(normalized.provider_raw_payload)
        metadata = normalized.metadata
        if not metadata.title or metadata.title == url:
            metadata = replace(metadata, title=(title or '').strip() or parsed.raw_title or url)
        extracted = normalized.markdown_content or ''
        if _word_count(extracted) >= MIN_EXTRACTED_SHARE * _word_count(page.text):
            body = extracted

    words = _word_count(body)
    metadata = replace(
        metadata,
        canonical_url=page.canonical_url or metadata.canonical_url or url,
        language=page.lang or metadata.language,
        reading_time_minutes=metadata.reading_time_minutes or (max(1, round(words / 200)) if words else 0),
    )
    quality = QualityEvaluator().evaluate(html=page.html or '', clean_text=body, title=metadata.title)
    payload['capture'] = {
        'source': 'extension',
        'canonical_url': page.canonical_url,
        'lang': page.lang,
        'text_bytes': _utf8_len(page.text),
        'html_bytes': _utf8_len(page.html) if page.html else 0,
    }
    return ContentDocument(
        url=url,
        canonical_url=metadata.canonical_url,
        content_hash=compute_content_hash(body),
        markdown_content=body,
        metadata=metadata,
        provider_raw_payload=payload,
        quality_metrics=quality,
        fetch_metadata=fetch_meta,
        plugin_versions=plugin_versions,
    )


def has_captured_content(bookmark) -> bool:
    return getattr(bookmark, 'strategy_used', None) == CAPTURE_STRATEGY and bool(getattr(bookmark, 'extracted_text', None))


def fetch_beats_capture(captured_text: Optional[str], doc) -> bool:
    """Whether a server fetch should replace content the extension captured.

    The capture is what the user saw, signed in and rendered, so it wins unless the fetch is
    clearly better: not a challenge page and with substantially more words.
    """
    if doc.outcome != 'ok' or doc.quality_metrics.challenge_detected:
        return False
    old_words = _word_count(captured_text)
    return _word_count(doc.markdown_content) >= max(old_words * CLEARLY_BETTER_RATIO, old_words + 1)


def capture_replaces(bookmark, doc) -> bool:
    """Whether a new capture should replace what is stored: yes, unless the stored text is
    clearly better or the capture is a challenge page."""
    if doc.quality_metrics.challenge_detected and bookmark.extracted_text:
        return False
    stored_words = _word_count(bookmark.extracted_text)
    return stored_words < max(_word_count(doc.markdown_content) * CLEARLY_BETTER_RATIO, 1)


def store_captured_document(uow, bookmark, doc) -> None:
    """Persist a captured document on the bookmark exactly as a successful fetch would."""
    from models import BookmarkMetadata
    from services.bookmark_processing_service import truncate_title

    if not bookmark.title or bookmark.title == 'Untitled Bookmark':
        bookmark.title = truncate_title((doc.metadata.title or '').strip())
    changed = bookmark.content_hash != doc.content_hash
    bookmark.extracted_text = doc.markdown_content.replace('\x00', '')
    bookmark.quality_score = doc.quality_metrics.score
    bookmark.author = doc.metadata.author[:255] if doc.metadata.author else None
    bookmark.reading_time = doc.metadata.reading_time_minutes
    bookmark.language = doc.metadata.language
    bookmark.content_hash = doc.content_hash
    bookmark.strategy_used = CAPTURE_STRATEGY
    bookmark.extractor_version = doc.extractor_version
    bookmark.scrape_status = 'SUCCESS'
    bookmark.scraped_at = datetime.utcnow()
    if changed:
        # New text needs a new embedding; PENDING also lets the reconciler retry a deferred one.
        bookmark.embedding_status = 'PENDING'

    meta = uow.session.query(BookmarkMetadata).filter_by(bookmark_id=bookmark.id).first()
    if meta:
        meta.jsonb_payload = doc.provider_raw_payload
        meta.updated_at = datetime.utcnow()
    else:
        uow.session.add(BookmarkMetadata(bookmark_id=bookmark.id, jsonb_payload=doc.provider_raw_payload))
