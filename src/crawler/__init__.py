"""
Independent Crawler Module
独立爬虫模块

This module provides standalone crawling functionality without MCP dependencies.
该模块提供独立的爬虫功能，不依赖MCP框架。
"""

from .core import IndependentCrawler

# Apple-specific components
from .apple_content_extractor import AppleContentExtractor
from .apple_stealth_crawler import AppleStealthCrawler

__all__ = [
    "IndependentCrawler",
    "AppleContentExtractor",
    "AppleStealthCrawler"
]
