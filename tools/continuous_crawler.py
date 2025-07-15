#!/usr/bin/env python3
"""
Continuous Crawler - Simplified
持续爬取器 - 极简版

Continuously crawls Apple documentation and stores data to database.
持续爬取Apple文档并存储数据到数据库。
"""

import sys
import asyncio
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from crawler import IndependentCrawler
from utils.logger import setup_logger

logger = setup_logger(__name__)


# ============================================================================
# CONFIGURATION - Single hyperparameter + .env variables
# ============================================================================

# Hyperparameter: Starting URL for crawling
TARGET_URL = "https://developer.apple.com/documentation/"


async def main():
    """Continuous Apple documentation crawler with database-driven priority"""
    logger.info("🚀 Database-Driven Continuous Crawler Starting")
    logger.info(f"Target: {TARGET_URL}")

    try:
        async with IndependentCrawler() as crawler:
            await crawler.start_infinite_crawl(TARGET_URL)
    except KeyboardInterrupt:
        logger.info("Crawler interrupted by user")
    except Exception as e:
        logger.error(f"Crawler error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Crawler interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
