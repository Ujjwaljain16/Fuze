"""
Readability & Boilerplate Removal Extractor Plugin
Parses main article content, title, and cleans DOM boilerplate.
"""

from typing import Optional
from bs4 import BeautifulSoup
try:
    from readability import Document
except ImportError:
    Document = None

from scrapers.extractors.base import ExtractorPlugin
from scrapers.extractors.registry import ExtractorRegistry
from scrapers.models import ExtractionResult
from core.logging_config import get_logger

logger = get_logger(__name__)


@ExtractorRegistry.register("readability")
class ReadabilityPlugin(ExtractorPlugin):
    @property
    def plugin_name(self) -> str:
        return "readability"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    def extract(self, html: str, url: str) -> ExtractionResult:
        if not html:
            return ExtractionResult(plugin_name=self.plugin_name, success=False, confidence=0.0, extracted_data={}, plugin_version=self.plugin_version)

        clean_title: Optional[str] = None
        clean_html: Optional[str] = None
        clean_text: Optional[str] = None

        try:
            if Document is not None:
                try:
                    doc = Document(html)
                    clean_title = doc.title()
                    clean_html = doc.summary()
                except Exception as e:
                    logger.debug("readability_lxml_failed", extra={"url": url, "error": str(e)})

            soup = BeautifulSoup(clean_html or html[:300000], 'html.parser')

            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe", "noscript"]):
                tag.decompose()

            if not clean_title:
                h1 = soup.find('h1')
                if h1 and h1.get_text().strip():
                    clean_title = h1.get_text().strip()
                elif soup.title and soup.title.string:
                    clean_title = soup.title.string.strip()

            clean_text = soup.get_text(separator=' ', strip=True)

            has_data = bool(clean_text and len(clean_text) > 50)
            confidence = 0.85 if Document and has_data else (0.7 if has_data else 0.0)

            return ExtractionResult(
                plugin_name=self.plugin_name,
                success=has_data,
                confidence=confidence,
                extracted_data={
                    "title": clean_title,
                    "clean_html": clean_html or str(soup),
                    "clean_text": clean_text
                },
                plugin_version=self.plugin_version
            )
        except Exception as e:
            logger.warning("readability_extraction_failed", extra={"url": url, "error": str(e)})
            return ExtractionResult(plugin_name=self.plugin_name, success=False, confidence=0.0, extracted_data={}, plugin_version=self.plugin_version)
