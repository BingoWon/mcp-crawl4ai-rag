#!/usr/bin/env python3
"""
全面检查chunks表数据质量

检查chunks表中是否存在测试数据或其他不正确的数据
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.database import create_database_client
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def check_chunks_data():
    """全面检查chunks表数据质量"""
    logger.info("🔍 开始全面检查chunks表数据质量...")
    
    # 初始化数据库连接
    db_client = create_database_client()
    await db_client.initialize()
    
    try:
        # 检查1：基本统计信息
        logger.info("=" * 80)
        logger.info("检查1：基本统计信息")
        
        total_result = await db_client.fetch_one("SELECT COUNT(*) as count FROM chunks")
        total_chunks = total_result['count']
        logger.info(f"📊 chunks表总记录数: {total_chunks}")
        
        # 检查不同URL的数量
        url_result = await db_client.fetch_one("SELECT COUNT(DISTINCT url) as count FROM chunks")
        unique_urls = url_result['count']
        logger.info(f"📊 唯一URL数量: {unique_urls}")
        
        # 平均每个URL的chunks数
        avg_chunks = total_chunks / unique_urls if unique_urls > 0 else 0
        logger.info(f"📊 平均每个URL的chunks数: {avg_chunks:.2f}")
        
        # 检查2：查找可疑的测试数据
        logger.info("=" * 80)
        logger.info("检查2：查找可疑的测试数据")
        
        # 查找包含"test"关键词的内容
        test_results = await db_client.fetch_all("""
            SELECT id, url, content, LENGTH(content) as content_length
            FROM chunks
            WHERE LOWER(content) LIKE '%test%'
            ORDER BY id
            LIMIT 20
        """)
        
        logger.info(f"📊 包含'test'关键词的chunks: {len(test_results)}")
        
        if test_results:
            logger.warning("⚠️ 发现可疑的测试数据:")
            for i, row in enumerate(test_results[:10]):  # 只显示前10个
                logger.warning(f"   {i+1}. ID: {row['id']}, 长度: {row['content_length']}, URL: {row['url']}")
                content_preview = row['content'][:100].replace('\n', ' ')
                logger.warning(f"      预览: {content_preview}...")
        
        # 检查3：查找异常短的内容
        logger.info("=" * 80)
        logger.info("检查3：查找异常短的内容")
        
        short_results = await db_client.fetch_all("""
            SELECT id, url, content, LENGTH(content) as content_length
            FROM chunks
            WHERE LENGTH(content) < 100
            ORDER BY LENGTH(content) ASC
            LIMIT 20
        """)
        
        logger.info(f"📊 内容长度小于100字符的chunks: {len(short_results)}")
        
        if short_results:
            logger.warning("⚠️ 发现异常短的内容:")
            for i, row in enumerate(short_results[:10]):
                logger.warning(f"   {i+1}. ID: {row['id']}, 长度: {row['content_length']}, URL: {row['url']}")
                content_preview = row['content'][:50].replace('\n', ' ')
                logger.warning(f"      内容: {content_preview}...")
        
        # 检查4：查找特定的问题URL
        logger.info("=" * 80)
        logger.info("检查4：查找特定的问题URL")
        
        swift_results = await db_client.fetch_all("""
            SELECT id, url, content, LENGTH(content) as content_length
            FROM chunks
            WHERE url = 'https://developer.apple.com/documentation/swift'
            ORDER BY id
        """)
        
        logger.info(f"📊 Swift文档URL的chunks数量: {len(swift_results)}")
        
        if swift_results:
            logger.info("📋 Swift文档的所有chunks:")
            for i, row in enumerate(swift_results):
                logger.info(f"   {i+1}. ID: {row['id']}, 长度: {row['content_length']}")
                content_preview = row['content'][:100].replace('\n', ' ')
                logger.info(f"      预览: {content_preview}...")
                
                # 检查是否是JSON格式的测试数据
                try:
                    parsed = json.loads(row['content'])
                    if isinstance(parsed, dict) and 'content' in parsed:
                        logger.error(f"❌ 发现JSON格式的测试数据: ID {row['id']}")
                        logger.error(f"   JSON内容: {json.dumps(parsed, indent=2)}")
                except json.JSONDecodeError:
                    pass  # 不是JSON，正常
        
        # 检查5：查找其他可疑模式
        logger.info("=" * 80)
        logger.info("检查5：查找其他可疑模式")
        
        # 查找包含JSON结构的内容
        json_results = await db_client.fetch_all("""
            SELECT id, url, content, LENGTH(content) as content_length
            FROM chunks
            WHERE content LIKE '%{%}%' AND content LIKE '%"content"%'
            ORDER BY id
            LIMIT 10
        """)
        
        logger.info(f"📊 可能包含JSON结构的chunks: {len(json_results)}")
        
        if json_results:
            logger.warning("⚠️ 发现可能的JSON结构数据:")
            for i, row in enumerate(json_results):
                logger.warning(f"   {i+1}. ID: {row['id']}, 长度: {row['content_length']}, URL: {row['url']}")
                content_preview = row['content'][:100].replace('\n', ' ')
                logger.warning(f"      预览: {content_preview}...")
        
        # 检查6：URL分布统计
        logger.info("=" * 80)
        logger.info("检查6：URL分布统计")
        
        url_stats = await db_client.fetch_all("""
            SELECT url, COUNT(*) as chunk_count, 
                   MIN(LENGTH(content)) as min_length,
                   MAX(LENGTH(content)) as max_length,
                   AVG(LENGTH(content))::int as avg_length
            FROM chunks
            GROUP BY url
            ORDER BY chunk_count DESC
            LIMIT 20
        """)
        
        logger.info("📊 URL chunks数量排行榜 (前20):")
        for i, row in enumerate(url_stats):
            logger.info(f"   {i+1}. {row['url'][:80]}...")
            logger.info(f"      chunks数: {row['chunk_count']}, 长度范围: {row['min_length']}-{row['max_length']}, 平均: {row['avg_length']}")
        
        # 检查7：embedding字段状态
        logger.info("=" * 80)
        logger.info("检查7：embedding字段状态")
        
        embedding_stats = await db_client.fetch_one("""
            SELECT 
                COUNT(*) as total,
                COUNT(embedding) as with_embedding,
                COUNT(*) - COUNT(embedding) as without_embedding
            FROM chunks
        """)
        
        logger.info(f"📊 embedding字段统计:")
        logger.info(f"   总记录数: {embedding_stats['total']}")
        logger.info(f"   有embedding: {embedding_stats['with_embedding']}")
        logger.info(f"   无embedding: {embedding_stats['without_embedding']}")
        
        if embedding_stats['without_embedding'] > 0:
            logger.warning(f"⚠️ 发现 {embedding_stats['without_embedding']} 个记录缺少embedding")
        
    except Exception as e:
        logger.error(f"❌ 检查过程中出错: {e}")
        
    finally:
        await db_client.close()
        logger.info("🔒 数据库连接已关闭")


async def main():
    """主函数"""
    logger.info("🚀 开始chunks表数据质量检查...")
    await check_chunks_data()
    logger.info("🎉 检查完成！")


if __name__ == "__main__":
    asyncio.run(main())
