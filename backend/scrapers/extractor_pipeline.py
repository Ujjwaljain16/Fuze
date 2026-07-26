"""
Extractor Pipeline Module
Orchestrates execution of pluggable extraction plugins across RawFetchResult HTML.
"""

from typing import List, Optional
from scrapers.extractors.base import ExtractorPlugin
from scrapers.extractors.registry import ExtractorRegistry
import scrapers.extractors.opengraph_plugin
import scrapers.extractors.jsonld_plugin
import scrapers.extractors.readability_plugin
import scrapers.extractors.markdown_plugin
import scrapers.extractors.image_plugin
import scrapers.extractors.table_code_plugin
from scrapers.models import RawFetchResult, ParsedDocument, ExtractionResult
from core.logging_config import get_logger

logger = get_logger(__name__)


class ExtractorPipeline:
    """
    Executes a sequence of ExtractorPlugins dynamically loaded from ExtractorRegistry.
    """
    def __init__(self, plugins: Optional[List[ExtractorPlugin]] = None):
        self.plugins = plugins if plugins is not None else ExtractorRegistry.get_all_plugins()

    def process(self, fetch_result: RawFetchResult) -> ParsedDocument:
        html_str = ""
        if fetch_result.raw_content:
            try:
                html_str = fetch_result.raw_content.decode('utf-8', errors='replace')
            except Exception:
                html_str = str(fetch_result.raw_content)

        plugin_results: List[ExtractionResult] = []
        parsed_title: Optional[str] = None
        clean_text: str = ""
        markdown_body: str = ""

        for plugin in self.plugins:
            try:
                result = plugin.extract(html_str, fetch_result.url)
                plugin_results.append(result)

                if result.plugin_name == "readability" and result.success:
                    parsed_title = result.extracted_data.get("title")
                    clean_text = result.extracted_data.get("clean_text", "")

                if result.plugin_name == "markdown" and result.success:
                    markdown_body = result.extracted_data.get("markdown_body", "")

            except Exception as e:
                logger.warning(
                    "extractor_plugin_failed",
                    extra={"plugin": plugin.plugin_name, "url": fetch_result.url, "error": str(e)}
                )
                plugin_results.append(
                    ExtractionResult(plugin_name=plugin.plugin_name, success=False, confidence=0.0, extracted_data={}, plugin_version=plugin.plugin_version)
                )

        if not markdown_body and clean_text:
            markdown_body = clean_text

        logger.info(
            "extractor_pipeline_complete",
            extra={"url": fetch_result.url, "plugins_run": len(self.plugins), "plugins_succeeded": sum(1 for r in plugin_results if r.success)}
        )

        return ParsedDocument(
            url=fetch_result.url,
            raw_title=parsed_title,
            raw_html=html_str,
            clean_text=clean_text,
            markdown_body=markdown_body,
            plugin_results=plugin_results,
            fetch_metadata=fetch_result.fetch_metadata
        )
