"""
Image & Asset Extractor Plugin
Extracts main article image and image asset lists from target HTML.
"""

from urllib.parse import urljoin
from bs4 import BeautifulSoup
from scrapers.extractors.base import ExtractorPlugin
from scrapers.extractors.registry import ExtractorRegistry
from scrapers.models import ExtractionResult
from core.logging_config import get_logger

logger = get_logger(__name__)


@ExtractorRegistry.register("image")
class ImagePlugin(ExtractorPlugin):
    @property
    def plugin_name(self) -> str:
        return "image"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    def extract(self, html: str, url: str) -> ExtractionResult:
        if not html:
            return ExtractionResult(plugin_name=self.plugin_name, success=False, confidence=0.0, extracted_data={}, plugin_version=self.plugin_version)

        images = []
        main_image_url = None

        try:
            soup = BeautifulSoup(html[:300000], 'html.parser')
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if not src or src.startswith('data:'):
                    continue
                abs_url = urljoin(url, src.strip())
                if abs_url not in images:
                    images.append(abs_url)

            if images:
                main_image_url = images[0]

            return ExtractionResult(
                plugin_name=self.plugin_name,
                success=bool(images),
                confidence=0.8 if images else 0.0,
                extracted_data={
                    "main_image_url": main_image_url,
                    "images": images[:20]
                },
                plugin_version=self.plugin_version
            )
        except Exception as e:
            logger.warning("image_extraction_failed", extra={"url": url, "error": str(e)})
            return ExtractionResult(plugin_name=self.plugin_name, success=False, confidence=0.0, extracted_data={}, plugin_version=self.plugin_version)
