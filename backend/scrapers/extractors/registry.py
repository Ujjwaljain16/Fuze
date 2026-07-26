"""
Extractor Plugin Registry
Provides centralized dynamic registration and discovery for ExtractorPlugin implementations.
"""

from typing import Dict, List, Type
from scrapers.extractors.base import ExtractorPlugin
from core.logging_config import get_logger

logger = get_logger(__name__)


class ExtractorRegistry:
    """
    Registry for ExtractorPlugins enabling dynamic plugin discovery and customization.
    """
    _registry: Dict[str, Type[ExtractorPlugin]] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register an ExtractorPlugin class by name."""
        def decorator(plugin_cls: Type[ExtractorPlugin]):
            cls._registry[name] = plugin_cls
            logger.info("extractor_plugin_registered", extra={"name": name, "class": plugin_cls.__name__})
            return plugin_cls
        return decorator

    @classmethod
    def register_plugin_class(cls, name: str, plugin_cls: Type[ExtractorPlugin]):
        """Directly register an ExtractorPlugin class."""
        cls._registry[name] = plugin_cls

    @classmethod
    def get_plugin(cls, name: str) -> ExtractorPlugin:
        """Instantiate and return a plugin by registered name."""
        if name not in cls._registry:
            raise KeyError(f"No extractor plugin registered with name '{name}'")
        return cls._registry[name]()

    @classmethod
    def get_all_plugins(cls) -> List[ExtractorPlugin]:
        """Instantiate and return all registered plugins in standard order."""
        return [plugin_cls() for plugin_cls in cls._registry.values()]

    @classmethod
    def list_registered_names(cls) -> List[str]:
        """Return list of registered plugin names."""
        return list(cls._registry.keys())
