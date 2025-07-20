#!/usr/bin/env python3
"""
NEON Cloud Database Setup Test
测试NEON云数据库设置

Validates NEON database connection and setup for the crawl4ai-rag project.
验证crawl4ai-rag项目的NEON数据库连接和设置。
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import get_database_client, DatabaseOperations
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def test_neon_setup():
    """Test NEON database setup and functionality"""
    logger.info("🚀 Testing NEON cloud database setup")
    
    try:
        # Test database connection
        logger.info("🔗 Testing NEON database connection...")
        client = await get_database_client()
        
        # Test basic query
        version = await client.fetch_one("SELECT version()")
        logger.info(f"✅ Connected to: {version['version']}")
        
        # Test database operations
        logger.info("📊 Testing database operations...")
        db_ops = DatabaseOperations(client)
        
        # Test table existence
        tables = await client.fetch_all("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        table_names = [table['table_name'] for table in tables]
        logger.info(f"📋 Available tables: {table_names}")
        
        # Test pgvector extension
        logger.info("🧮 Testing pgvector extension...")
        extensions = await client.fetch_all("""
            SELECT extname 
            FROM pg_extension 
            WHERE extname = 'vector'
        """)
        
        if extensions:
            logger.info("✅ pgvector extension is available")
        else:
            logger.warning("⚠️ pgvector extension not found")
        
        # Test data counts
        if 'pages' in table_names:
            pages_count = await client.fetch_one("SELECT COUNT(*) as count FROM pages")
            logger.info(f"📄 Pages in database: {pages_count['count']:,}")
        
        if 'chunks' in table_names:
            chunks_count = await client.fetch_one("SELECT COUNT(*) as count FROM chunks")
            logger.info(f"🧩 Chunks in database: {chunks_count['count']:,}")
            
            # Test vector data
            vector_count = await client.fetch_one("SELECT COUNT(*) as count FROM chunks WHERE embedding IS NOT NULL")
            logger.info(f"🔢 Vector embeddings: {vector_count['count']:,}")
        
        logger.info("🎉 NEON database setup test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ NEON database setup test failed: {e}")
        return False

async def main():
    """Main test function"""
    success = await test_neon_setup()
    
    if success:
        logger.info("✅ NEON cloud database is ready for use!")
    else:
        logger.error("❌ NEON database setup issues detected")
        logger.info("💡 Please check your NEON configuration in .env file")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
