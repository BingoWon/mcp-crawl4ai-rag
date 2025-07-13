#!/usr/bin/env python3
"""
Continuous Crawler - Environment Variable Driven
持续爬取器 - 环境变量驱动

A unified crawler that continuously crawls and stores data to database.
统一的爬取器，持续爬取并存储数据到数据库。

Environment Variables:
- CRAWL_TARGET_URL: Target URL to crawl (default: Apple visionOS docs)
- CRAWL_MAX_DEPTH: Maximum crawl depth (default: 2)
- CRAWL_MAX_CONCURRENT: Maximum concurrent requests (default: 5)
- CRAWL_INTERVAL: Interval between crawls in seconds (default: 3600)
- CRAWL_MODE: Crawl mode 'smart' or 'single' (default: smart)
- CRAWL_CONTINUOUS: Enable continuous mode (default: false)
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from crawler import IndependentCrawler
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CrawlerConfig:
    """Environment variable driven crawler configuration"""
    
    # Core configuration
    TARGET_URL = os.getenv('CRAWL_TARGET_URL', 'https://developer.apple.com/documentation/visionos/')
    MAX_DEPTH = int(os.getenv('CRAWL_MAX_DEPTH', '2'))
    MAX_CONCURRENT = int(os.getenv('CRAWL_MAX_CONCURRENT', '5'))
    
    # Continuous mode configuration
    CRAWL_INTERVAL = int(os.getenv('CRAWL_INTERVAL', '3600'))  # 1 hour
    CRAWL_MODE = os.getenv('CRAWL_MODE', 'smart').lower()  # smart | single
    CONTINUOUS = os.getenv('CRAWL_CONTINUOUS', 'false').lower() == 'true'
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        if not cls.TARGET_URL.startswith(('http://', 'https://')):
            logger.error(f"Invalid TARGET_URL: {cls.TARGET_URL}")
            return False
        
        if cls.CRAWL_MODE not in ['smart', 'single']:
            logger.error(f"Invalid CRAWL_MODE: {cls.CRAWL_MODE}")
            return False
        
        return True
    
    @classmethod
    def display(cls):
        """Display current configuration"""
        logger.info("Crawler Configuration:")
        logger.info(f"  Target URL: {cls.TARGET_URL}")
        logger.info(f"  Max Depth: {cls.MAX_DEPTH}")
        logger.info(f"  Max Concurrent: {cls.MAX_CONCURRENT}")
        logger.info(f"  Crawl Mode: {cls.CRAWL_MODE}")
        logger.info(f"  Continuous: {cls.CONTINUOUS}")
        if cls.CONTINUOUS:
            logger.info(f"  Interval: {cls.CRAWL_INTERVAL}s ({cls.CRAWL_INTERVAL/3600:.1f}h)")


async def execute_single_crawl() -> Dict[str, Any]:
    """Execute single page crawl"""
    logger.info(f"Starting single page crawl: {CrawlerConfig.TARGET_URL}")
    
    async with IndependentCrawler() as crawler:
        result = await crawler.crawl_single_page(CrawlerConfig.TARGET_URL)
    
    if result["success"]:
        logger.info("Single page crawl completed successfully")
        logger.info(f"Chunks stored: {result.get('chunks_stored', 'N/A')}")
        logger.info(f"Source ID: {result.get('source_id', 'N/A')}")
        logger.info(f"Total characters: {result.get('total_characters', 'N/A')}")
    else:
        logger.error(f"Single page crawl failed: {result.get('error', 'Unknown error')}")
    
    return result


async def execute_smart_crawl() -> Dict[str, Any]:
    """Execute smart website crawl"""
    logger.info(f"Starting smart crawl: {CrawlerConfig.TARGET_URL}")
    
    async with IndependentCrawler() as crawler:
        result = await crawler.smart_crawl_url(CrawlerConfig.TARGET_URL)
    
    if result["success"]:
        logger.info("Smart crawl completed successfully")
        logger.info(f"Crawl type: {result.get('crawl_type', 'N/A')}")
        logger.info(f"Total pages: {result.get('total_pages', 'N/A')}")
        logger.info(f"Total chunks: {result.get('total_chunks', 'N/A')}")
        logger.info(f"Sources updated: {result.get('sources_updated', 'N/A')}")
    else:
        logger.error(f"Smart crawl failed: {result.get('error', 'Unknown error')}")
    
    return result


async def execute_crawl() -> Dict[str, Any]:
    """Execute crawl based on configuration"""
    start_time = datetime.now()
    logger.info(f"Starting crawl at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        if CrawlerConfig.CRAWL_MODE == 'single':
            result = await execute_single_crawl()
        else:
            result = await execute_smart_crawl()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Crawl completed in {duration:.1f}s")
        
        return result
        
    except Exception as e:
        logger.error(f"Crawl failed with exception: {e}")
        return {"success": False, "error": str(e)}


async def continuous_crawl():
    """Run continuous crawling loop"""
    logger.info("Starting continuous crawl mode")
    
    crawl_count = 0
    while True:
        try:
            crawl_count += 1
            logger.info(f"=== Crawl #{crawl_count} ===")
            
            result = await execute_crawl()
            
            if CrawlerConfig.CONTINUOUS:
                logger.info(f"Waiting {CrawlerConfig.CRAWL_INTERVAL}s until next crawl...")
                await asyncio.sleep(CrawlerConfig.CRAWL_INTERVAL)
            else:
                logger.info("Single run mode, exiting")
                break
                
        except KeyboardInterrupt:
            logger.info("Continuous crawl interrupted by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error in continuous crawl: {e}")
            if CrawlerConfig.CONTINUOUS:
                logger.info("Continuing despite error...")
                await asyncio.sleep(60)  # Wait 1 minute before retry
            else:
                break


async def main():
    """Main entry point"""
    logger.info("🚀 Continuous Crawler Starting")
    logger.info("=" * 60)
    
    # Validate configuration
    if not CrawlerConfig.validate():
        logger.error("Configuration validation failed")
        return
    
    # Display configuration
    CrawlerConfig.display()
    
    # Execute crawling
    await continuous_crawl()
    
    logger.info("Continuous Crawler Finished")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Crawler interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
