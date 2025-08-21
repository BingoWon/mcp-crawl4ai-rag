#!/usr/bin/env python3
"""
验证YouTube处理结果
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.database import create_database_client
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def verify_results():
    """验证YouTube处理结果"""
    client = create_database_client()
    await client.initialize()
    
    try:
        # 检查YouTube chunks
        logger.info('=== YouTube Chunks验证 ===')
        youtube_chunks = await client.fetch_all('''
            SELECT url, LENGTH(content) as content_length, 
                   CASE WHEN embedding IS NOT NULL THEN 'YES' ELSE 'NO' END as has_embedding
            FROM chunks 
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
            ORDER BY url
        ''')
        
        logger.info(f'YouTube chunks总数: {len(youtube_chunks)}')
        for chunk in youtube_chunks:
            logger.info(f'  URL: {chunk["url"]}')
            logger.info(f'  长度: {chunk["content_length"]}字符, embedding: {chunk["has_embedding"]}')
        
        # 检查processed_at状态
        logger.info('\n=== Pages处理状态验证 ===')
        processed_pages = await client.fetch_all('''
            SELECT url, 
                   CASE WHEN processed_at IS NOT NULL THEN 'PROCESSED' ELSE 'PENDING' END as status,
                   processed_at
            FROM pages 
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
            ORDER BY processed_at DESC NULLS LAST
            LIMIT 3
        ''')
        
        for page in processed_pages:
            logger.info(f'  {page["url"]}: {page["status"]}')
            if page["processed_at"]:
                logger.info(f'    处理时间: {page["processed_at"]}')
        
        # 检查chunk内容样本
        logger.info('\n=== Chunk内容样本 ===')
        sample_chunk = await client.fetch_one('''
            SELECT content FROM chunks 
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
            LIMIT 1
        ''')
        
        if sample_chunk:
            try:
                chunk_data = json.loads(sample_chunk['content'])
                logger.info(f'Context: {chunk_data.get("context", "N/A")}')
                logger.info(f'Content预览: {chunk_data.get("content", "")[:100]}...')
            except:
                logger.info(f'Content预览: {sample_chunk["content"][:100]}...')
        
        # 统计信息
        logger.info('\n=== 统计信息 ===')
        stats = await client.fetch_one('''
            SELECT 
                COUNT(*) as total_chunks,
                COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embedding,
                AVG(LENGTH(content)) as avg_content_length
            FROM chunks 
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
        ''')
        
        if stats:
            logger.info(f'总chunks: {stats["total_chunks"]}')
            logger.info(f'有embedding: {stats["with_embedding"]}')
            logger.info(f'平均长度: {stats["avg_content_length"]:.0f}字符')
        
    finally:
        await client.close()


async def main():
    """主函数"""
    logger.info("🔍 开始验证YouTube处理结果...")
    await verify_results()
    logger.info("✅ 验证完成！")


if __name__ == "__main__":
    asyncio.run(main())
