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
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from crawler.core import Crawler
from processor.core import Processor
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Configuration from environment variables
TARGET_URL = os.getenv("TARGET_URL", "https://developer.apple.com/documentation/")
ENABLE_CRAWLER = os.getenv("ENABLE_CRAWLER", "true").lower() == "true"
ENABLE_PROCESSOR = os.getenv("ENABLE_PROCESSOR", "true").lower() == "true"


async def main():
    """Unified crawler system with configurable components"""
    logger.info("🚀 Unified Crawler System Starting")
    logger.info(f"Target: {TARGET_URL}")
    logger.info(f"Components: Crawler={ENABLE_CRAWLER}, Processor={ENABLE_PROCESSOR}")

    # Validate configuration
    if not ENABLE_CRAWLER and not ENABLE_PROCESSOR:
        logger.warning("⚠️ Both crawler and processor are disabled. System will exit.")
        return

    try:
        # Log enabled components
        if ENABLE_CRAWLER:
            logger.info("✅ Crawler component enabled")

        if ENABLE_PROCESSOR:
            logger.info("✅ Processor component enabled")

        # Start enabled components
        if ENABLE_CRAWLER and ENABLE_PROCESSOR:
            # Both components enabled
            async with Crawler() as crawler, Processor() as processor:
                await asyncio.gather(
                    crawler.start_crawling(TARGET_URL),
                    processor.start_processing()
                )
        elif ENABLE_CRAWLER:
            # Only crawler enabled
            async with Crawler() as crawler:
                await crawler.start_crawling(TARGET_URL)
        elif ENABLE_PROCESSOR:
            # Only processor enabled
            async with Processor() as processor:
                await processor.start_processing()

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
