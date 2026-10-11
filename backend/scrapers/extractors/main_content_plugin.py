"""
Main-content extractor (trafilatura): the article body as Markdown, without navigation,
menus, footers or comments. Preferred over the readability and whole-page converters.
"""

from scrapers.extractors.base import ExtractorPlugin
from scrapers.extractors.registry import ExtractorRegistry
from scrapers.models import ExtractionResult
from core.logging_config import get_logger

logger = get_logger(__name__)

try:
    import trafilatura
except ImportError:  # pragma: no cover - declared in requirements.txt
    trafilatura = None

MIN_WORDS = 30


@ExtractorRegistry.register("main_content")
class MainContentPlugin(ExtractorPlugin):
    @property
    def plugin_name(self) -> str:
        return "main_content"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    def extract(self, html: str, url: str) -> ExtractionResult:
        empty = ExtractionResult(plugin_name=self.plugin_name, success=False, confidence=0.0,
                                 extracted_data={}, plugin_version=self.plugin_version)
        if not html or trafilatura is None:
            return empty
        try:
            body = trafilatura.extract(
                html, url=url, output_format="markdown", include_tables=True, include_images=False,
                include_links=False, include_comments=False, favor_precision=True,
            )
        except Exception as e:
            logger.debug("main_content_extract_failed", extra={"url": url, "error": str(e)})
            return empty
        if not body or len(body.split()) < MIN_WORDS:
            return empty
        return ExtractionResult(plugin_name=self.plugin_name, success=True, confidence=0.9,
                                extracted_data={"markdown_body": body.strip()}, plugin_version=self.plugin_version)
