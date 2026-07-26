"""
Base Extractor Plugin Interface
Defines the abstract interface for modular extraction plugins in the Content Acquisition Pipeline.
"""

from abc import ABC, abstractmethod
from scrapers.models import ExtractionResult


class ExtractorPlugin(ABC):
    """
    Abstract interface for single-responsibility extraction plugins.
    """
    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Unique identifier for the plugin."""
        pass

    @property
    def plugin_version(self) -> str:
        """Version string of the plugin."""
        return "1.0.0"

    @abstractmethod
    def extract(self, html: str, url: str) -> ExtractionResult:
        """
        Execute extraction on raw HTML.
        Returns ExtractionResult(plugin_name, success, confidence, extracted_data).
        """
        pass
