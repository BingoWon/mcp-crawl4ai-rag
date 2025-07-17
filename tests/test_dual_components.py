#!/usr/bin/env python3
"""
Test Dual Components
测试双组件系统

Test the crawler and processor components running independently.
测试爬取器和处理器组件独立运行。
"""

import sys
import asyncio
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from database import get_database_client, DatabaseOperations
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def test_database_schema():
    """Test that process_count field exists"""
    logger.info("Testing database schema...")

    client = await get_database_client()
    try:
        # Check if process_count column exists
        result = await client.execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'pages' AND column_name = 'process_count'
        """)
        
        if result:
            logger.info("✅ process_count field exists in pages table")
        else:
            logger.error("❌ process_count field missing in pages table")
            return False
            
        # Check index exists
        index_result = await client.execute_query("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'pages' AND indexname = 'idx_pages_process_count'
        """)
        
        if index_result:
            logger.info("✅ process_count index exists")
        else:
            logger.error("❌ process_count index missing")
            return False

        return True
    finally:
        pass


async def test_database_operations():
    """Test new database operations"""
    logger.info("Testing database operations...")

    client = await get_database_client()
    try:
        db_ops = DatabaseOperations(client)
        
        # Test get_next_process_url
        result = await db_ops.get_next_process_url()
        logger.info(f"get_next_process_url result: {result}")
        
        if result:
            url, content = result
            logger.info(f"Next URL to process: {url}")
            logger.info(f"Content length: {len(content)} characters")
            
            # Test update_page_after_process
            await db_ops.update_page_after_process(url)
            logger.info("✅ update_page_after_process completed")
        else:
            logger.info("No URLs available for processing")

        return True
    finally:
        pass


async def check_system_status():
    """Check current system status"""
    logger.info("Checking system status...")

    client = await get_database_client()
    try:
        # Check pages table statistics
        pages_stats = await client.execute_query("""
            SELECT 
                COUNT(*) as total_pages,
                MIN(crawl_count) as min_crawl_count,
                MAX(crawl_count) as max_crawl_count,
                AVG(crawl_count) as avg_crawl_count,
                MIN(process_count) as min_process_count,
                MAX(process_count) as max_process_count,
                AVG(process_count) as avg_process_count
            FROM pages
        """)
        
        if pages_stats:
            stats = pages_stats[0]
            logger.info(f"📊 Pages Statistics:")
            logger.info(f"  Total pages: {stats['total_pages']}")
            logger.info(f"  Crawl count - Min: {stats['min_crawl_count']}, Max: {stats['max_crawl_count']}, Avg: {stats['avg_crawl_count']:.2f}")
            logger.info(f"  Process count - Min: {stats['min_process_count']}, Max: {stats['max_process_count']}, Avg: {stats['avg_process_count']:.2f}")
        
        # Check chunks table statistics
        chunks_stats = await client.execute_query("""
            SELECT COUNT(*) as total_chunks
            FROM chunks
        """)
        
        if chunks_stats:
            logger.info(f"📊 Chunks Statistics:")
            logger.info(f"  Total chunks: {chunks_stats[0]['total_chunks']}")
    finally:
        pass


async def main():
    """Main test function"""
    logger.info("🧪 Testing Dual Components System")
    
    try:
        # Test database schema
        if not await test_database_schema():
            logger.error("Database schema test failed")
            return
            
        # Test database operations
        if not await test_database_operations():
            logger.error("Database operations test failed")
            return
            
        # Check system status
        await check_system_status()
        
        logger.info("✅ All tests passed!")
        
    except Exception as e:
        logger.error(f"Test error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
