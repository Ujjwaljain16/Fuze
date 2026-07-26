"""
Table & Code Block Extractor Plugin
Parses code blocks (language + code snippet) and HTML data tables.
"""

from typing import Any, Dict, List
from bs4 import BeautifulSoup
from scrapers.extractors.base import ExtractorPlugin
from scrapers.extractors.registry import ExtractorRegistry
from scrapers.models import ExtractionResult
from core.logging_config import get_logger

logger = get_logger(__name__)


@ExtractorRegistry.register("table_code")
class TableCodePlugin(ExtractorPlugin):
    @property
    def plugin_name(self) -> str:
        return "table_code"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    def extract(self, html: str, url: str) -> ExtractionResult:
        if not html:
            return ExtractionResult(plugin_name=self.plugin_name, success=False, confidence=0.0, extracted_data={}, plugin_version=self.plugin_version)

        code_blocks: List[Dict[str, str]] = []
        tables: List[Dict[str, Any]] = []

        try:
            soup = BeautifulSoup(html[:300000], 'html.parser')

            for pre in soup.find_all(['pre', 'code']):
                code_text = pre.get_text().strip()
                if len(code_text) > 10:
                    lang = pre.get('class', [''])[0] if isinstance(pre.get('class'), list) else ""
                    lang = lang.replace('language-', '').replace('lang-', '')
                    code_blocks.append({
                        "language": lang or "plain",
                        "code": code_text[:2000]
                    })

            for tbl in soup.find_all('table'):
                headers = [th.get_text().strip() for th in tbl.find_all('th')]
                rows = []
                for tr in tbl.find_all('tr'):
                    cells = [td.get_text().strip() for td in tr.find_all('td')]
                    if cells:
                        rows.append(cells)
                if headers or rows:
                    tables.append({
                        "headers": headers,
                        "rows": rows[:50]
                    })

            has_data = bool(code_blocks or tables)

            return ExtractionResult(
                plugin_name=self.plugin_name,
                success=has_data,
                confidence=0.9 if has_data else 0.0,
                extracted_data={
                    "code_blocks": code_blocks[:10],
                    "tables": tables[:10]
                },
                plugin_version=self.plugin_version
            )
        except Exception as e:
            logger.warning("table_code_extraction_failed", extra={"url": url, "error": str(e)})
            return ExtractionResult(plugin_name=self.plugin_name, success=False, confidence=0.0, extracted_data={}, plugin_version=self.plugin_version)
