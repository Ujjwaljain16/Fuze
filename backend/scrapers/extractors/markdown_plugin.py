"""
Markdown Converter Extractor Plugin
Transforms clean HTML DOM into structured, semantic Markdown.
"""

from bs4 import BeautifulSoup
from scrapers.extractors.base import ExtractorPlugin
from scrapers.extractors.registry import ExtractorRegistry
from scrapers.models import ExtractionResult
from core.logging_config import get_logger

logger = get_logger(__name__)


@ExtractorRegistry.register("markdown")
class MarkdownPlugin(ExtractorPlugin):
    @property
    def plugin_name(self) -> str:
        return "markdown"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    def extract(self, html: str, url: str) -> ExtractionResult:
        if not html:
            return ExtractionResult(plugin_name=self.plugin_name, success=False, confidence=0.0, extracted_data={}, plugin_version=self.plugin_version)

        try:
            soup = BeautifulSoup(html[:300000], 'html.parser')
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()

            markdown_lines = []

            for elem in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'pre', 'blockquote', 'table']):
                name = elem.name
                text = elem.get_text().strip()

                if not text:
                    continue

                if name == 'h1':
                    markdown_lines.append(f"\n# {text}\n")
                elif name == 'h2':
                    markdown_lines.append(f"\n## {text}\n")
                elif name == 'h3':
                    markdown_lines.append(f"\n### {text}\n")
                elif name == 'h4':
                    markdown_lines.append(f"\n#### {text}\n")
                elif name == 'p':
                    markdown_lines.append(f"{text}\n")
                elif name == 'blockquote':
                    markdown_lines.append(f"> {text}\n")
                elif name == 'pre':
                    code_text = elem.get_text()
                    markdown_lines.append(f"```\n{code_text}\n```\n")
                elif name in ('ul', 'ol'):
                    for li in elem.find_all('li'):
                        li_text = li.get_text().strip()
                        if li_text:
                            markdown_lines.append(f"- {li_text}")
                    markdown_lines.append("")
                elif name == 'table':
                    rows = elem.find_all('tr')
                    for r in rows:
                        cols = [c.get_text().strip() for c in r.find_all(['th', 'td'])]
                        if cols:
                            markdown_lines.append("| " + " | ".join(cols) + " |")
                    markdown_lines.append("")

            markdown_body = "\n".join(markdown_lines).strip()

            if not markdown_body:
                markdown_body = soup.get_text(separator='\n\n', strip=True)

            has_data = bool(markdown_body and len(markdown_body) > 30)

            return ExtractionResult(
                plugin_name=self.plugin_name,
                success=has_data,
                confidence=0.85 if has_data else 0.0,
                extracted_data={"markdown_body": markdown_body},
                plugin_version=self.plugin_version
            )
        except Exception as e:
            logger.warning("markdown_extraction_failed", extra={"url": url, "error": str(e)})
            return ExtractionResult(plugin_name=self.plugin_name, success=False, confidence=0.0, extracted_data={}, plugin_version=self.plugin_version)
