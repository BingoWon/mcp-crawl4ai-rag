#!/usr/bin/env python3
"""
批量并发优化测试脚本
测试新的批量爬取和连接池复用功能
"""

import sys
import asyncio
import time
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from crawler.core import BatchCrawler
from database import get_database_client, DatabaseOperations
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def test_batch_optimization():
    """测试批量优化效果"""
    logger.info("🚀 Starting batch optimization test")
    
    # Test configuration
    test_url = "https://developer.apple.com/documentation/"
    batch_size = 3
    max_concurrent = 2
    
    try:
        # Initialize database
        db_client = await get_database_client()
        db_operations = DatabaseOperations(db_client)
        
        # Test batch URL retrieval
        logger.info("Testing batch URL retrieval...")
        start_time = time.time()
        
        # Insert test URL if not exists
        await db_operations.insert_url_if_not_exists(test_url)
        
        # Get batch URLs
        batch_urls = await db_operations.get_urls_batch(batch_size)
        
        retrieval_time = time.time() - start_time
        logger.info(f"✅ Batch URL retrieval: {len(batch_urls)} URLs in {retrieval_time:.3f}s")
        
        # Test batch crawler
        logger.info("Testing batch crawler...")
        start_time = time.time()
        
        if batch_urls:
            async with BatchCrawler(batch_size=batch_size, max_concurrent=max_concurrent) as crawler:
                # Test a small batch to avoid overwhelming the system
                await crawler._process_batch(batch_urls[:2])  # Test with 2 URLs
        
        crawl_time = time.time() - start_time
        logger.info(f"✅ Batch crawling: 2 URLs in {crawl_time:.3f}s")
        
        # Performance summary
        logger.info("📊 Performance Test Summary:")
        logger.info(f"   - Batch size: {batch_size}")
        logger.info(f"   - Max concurrent: {max_concurrent}")
        logger.info(f"   - URL retrieval: {retrieval_time:.3f}s")
        logger.info(f"   - Batch crawling: {crawl_time:.3f}s")
        logger.info("✅ Batch optimization test completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

async def main():
    """主函数"""
    try:
        await test_batch_optimization()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
