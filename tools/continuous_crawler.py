#!/usr/bin/env python3
"""
Continuous Crawler - Simplified
持续爬取器 - 极简版

Continuously crawls Apple documentation and stores data to database.
持续爬取Apple文档并存储数据到数据库。

Uses existing .env configuration (MAX_DEPTH, etc.)
使用现有的.env配置（MAX_DEPTH等）
"""

import os
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

# Global configuration from .env
MAX_DEPTH = int(os.getenv('MAX_DEPTH', '2'))


async def main():
    """Continuous Apple documentation crawler"""
    logger.info("🚀 Continuous Crawler Starting")
    logger.info(f"Target: {TARGET_URL} | Depth: {MAX_DEPTH}")

    crawl_count = 0
    while True:
        try:
            crawl_count += 1
            logger.info(f"=== Crawl #{crawl_count} ===")

            async with IndependentCrawler() as crawler:
                result = await crawler.smart_crawl_url(TARGET_URL)

            if result.get("success") and result.get("total_pages", 0) > 0:
                logger.info(f"✅ {result['total_pages']} pages, {result['total_chunks']} chunks")
            elif result.get("success"):
                logger.info("✅ No new pages found, crawling complete")
                break
            else:
                logger.warning(f"❌ Crawl failed: {result.get('error', 'Unknown')}")

        except KeyboardInterrupt:
            logger.info("Crawler interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Crawler interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
