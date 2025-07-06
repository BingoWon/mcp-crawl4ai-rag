"""
Independent Crawler Module
独立爬虫模块

This module provides standalone crawling functionality without MCP dependencies.
该模块提供独立的爬虫功能，不依赖MCP框架。
"""

from .core import IndependentCrawler
from .config import CrawlerConfig

# Apple-specific components
try:
    from .apple_content_extractor import AppleContentExtractor
    from .apple_stealth_crawler import AppleStealthCrawler
    APPLE_COMPONENTS_AVAILABLE = True
except ImportError:
    APPLE_COMPONENTS_AVAILABLE = False
    AppleContentExtractor = None
    AppleStealthCrawler = None

__all__ = [
    "IndependentCrawler",
    "CrawlerConfig",
    "AppleContentExtractor",
    "AppleStealthCrawler",
    "APPLE_COMPONENTS_AVAILABLE"
]
