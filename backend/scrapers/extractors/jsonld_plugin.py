"""
JSON-LD & Schema.org Extractor Plugin
Extracts application/ld+json structured schemas from target HTML.
"""

import json
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from scrapers.extractors.base import ExtractorPlugin
from scrapers.extractors.registry import ExtractorRegistry
from scrapers.models import ExtractionResult
from core.logging_config import get_logger

logger = get_logger(__name__)


@ExtractorRegistry.register("json_ld")
class JSONLDPlugin(ExtractorPlugin):
    @property
    def plugin_name(self) -> str:
        return "json_ld"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    def extract(self, html: str, url: str) -> ExtractionResult:
        if not html:
            return ExtractionResult(plugin_name=self.plugin_name, success=False, confidence=0.0, extracted_data={}, plugin_version=self.plugin_version)

        schemas: List[Dict[str, Any]] = []

        try:
            soup = BeautifulSoup(html[:300000], 'html.parser')
            for script in soup.find_all('script', type='application/ld+json'):
                content = script.string
                if not content or not content.strip():
                    continue
                try:
                    data = json.loads(content.strip())
                    if isinstance(data, list):
                        schemas.extend([d for d in data if isinstance(d, dict)])
                    elif isinstance(data, dict):
                        schemas.append(data)
                except Exception:
                    continue

            flattened_schemas = []
            for s in schemas:
                if "@graph" in s and isinstance(s["@graph"], list):
                    flattened_schemas.extend([g for g in s["@graph"] if isinstance(g, dict)])
                else:
                    flattened_schemas.append(s)

            has_data = len(flattened_schemas) > 0
            confidence = 0.98 if has_data else 0.0

            return ExtractionResult(
                plugin_name=self.plugin_name,
                success=has_data,
                confidence=confidence,
                extracted_data={"schema_org": flattened_schemas},
                plugin_version=self.plugin_version
            )
        except Exception as e:
            logger.warning("jsonld_extraction_failed", extra={"url": url, "error": str(e)})
            return ExtractionResult(plugin_name=self.plugin_name, success=False, confidence=0.0, extracted_data={}, plugin_version=self.plugin_version)
