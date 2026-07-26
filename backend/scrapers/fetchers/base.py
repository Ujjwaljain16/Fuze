"""
Base Fetcher Interface
Defines the abstract interface for fetcher strategy implementations across tiers.
"""

from abc import ABC, abstractmethod
from scrapers.models import RawFetchResult


class BaseFetcher(ABC):
    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Name of the strategy ('HTTP', 'STEALTH', 'DYNAMIC')."""
        pass

    @abstractmethod
    def fetch(self, url: str) -> RawFetchResult:
        """Fetch target URL and return RawFetchResult."""
        pass
