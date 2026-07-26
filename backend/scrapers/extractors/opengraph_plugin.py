"""
OpenGraph & Twitter Cards Extractor Plugin
Parses og:title, og:description, og:image, og:type, twitter:card, etc.
"""

from bs4 import BeautifulSoup
from scrapers.extractors.base import ExtractorPlugin
from scrapers.extractors.registry import ExtractorRegistry
from scrapers.models import ExtractionResult
from core.logging_config import get_logger

logger = get_logger(__name__)


@ExtractorRegistry.register("opengraph")
class OpenGraphPlugin(ExtractorPlugin):
    @property
    def plugin_name(self) -> str:
        return "opengraph"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    def extract(self, html: str, url: str) -> ExtractionResult:
        if not html:
            return ExtractionResult(plugin_name=self.plugin_name, success=False, confidence=0.0, extracted_data={}, plugin_version=self.plugin_version)

        og_data = {}
        twitter_data = {}

        try:
            soup = BeautifulSoup(html[:200000], 'html.parser')

            for tag in soup.find_all('meta', property=True):
                prop = tag.get('property', '').lower()
                content = tag.get('content', '').strip()
                if prop.startswith('og:') and content:
                    key = prop[3:]
                    og_data[key] = content

            for tag in soup.find_all('meta', attrs={'name': True}):
                name = tag.get('name', '').lower()
                content = tag.get('content', '').strip()
                if name.startswith('twitter:') and content:
                    key = name[8:]
                    twitter_data[key] = content

            has_data = bool(og_data or twitter_data)
            confidence = 0.9 if ('title' in og_data or 'image' in og_data) else (0.5 if has_data else 0.0)

            return ExtractionResult(
                plugin_name=self.plugin_name,
                success=has_data,
                confidence=confidence,
                extracted_data={
                    "open_graph": og_data,
                    "twitter_card": twitter_data
                },
                plugin_version=self.plugin_version
            )
        except Exception as e:
            logger.warning("opengraph_extraction_failed", extra={"url": url, "error": str(e)})
            return ExtractionResult(plugin_name=self.plugin_name, success=False, confidence=0.0, extracted_data={}, plugin_version=self.plugin_version)
