#!/usr/bin/env python3
"""
Unified Crawler System
统一爬虫系统

Continuously crawls Apple documentation with integrated processing:
crawling, chunking, embedding, and storage.
持续爬取Apple文档并集成处理：爬取、分块、嵌入和存储。
"""

import sys
import asyncio
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from crawler.core import BatchCrawler
from processor.core import ContentProcessor
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Hyperparameter: Starting URL for crawling
TARGET_URL = "https://developer.apple.com/documentation/"


async def main():
    """Unified crawler system with integrated crawling and processing"""
    logger.info("🚀 Unified Crawler System Starting")
    logger.info(f"Target: {TARGET_URL}")
    logger.info("Running integrated crawling and processing...")

    try:
        # Start both crawler and processor concurrently
        async with BatchCrawler(batch_size=5, max_concurrent=5) as crawler, ContentProcessor() as processor:
            await asyncio.gather(
                crawler.start_crawling(TARGET_URL),
                processor.start_processing()
            )
    except KeyboardInterrupt:
        logger.info("Unified system interrupted by user")
    except Exception as e:
        logger.error(f"System error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("System interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
