#!/usr/bin/env python3
"""
测试批次级别标记修复

验证修复后的批量更新工具是否正确标记processed_at字段
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "tools"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.database import create_database_client, DatabaseOperations
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def test_batch_marking():
    """测试批次级别标记功能"""
    logger.info("🧪 测试批次级别标记修复...")
    
    # 初始化数据库连接
    db_client = create_database_client()
    await db_client.initialize()
    db_operations = DatabaseOperations(db_client)
    
    try:
        # 测试1：检查是否有待处理的数据
        logger.info("=" * 60)
        logger.info("测试1：检查待处理数据")
        
        batch = await db_operations.get_process_urls_batch(5)
        logger.info(f"📊 获取到 {len(batch)} 个待处理页面")
        
        if not batch:
            logger.warning("⚠️ 没有待处理的页面，测试无法进行")
            return
        
        # 显示获取到的页面
        for i, (url, content) in enumerate(batch):
            logger.info(f"   页面{i+1}: {url[:80]}...")
            logger.info(f"   内容长度: {len(content)} 字符")
        
        # 测试2：模拟批次处理后的标记
        logger.info("=" * 60)
        logger.info("测试2：模拟批次标记")
        
        urls = [url for url, _ in batch]
        logger.info(f"📝 准备标记 {len(urls)} 个页面为已处理...")
        
        # 标记为已处理
        marked_count = await db_operations.mark_pages_processed(urls)
        logger.info(f"✅ 成功标记了 {marked_count} 个页面")
        
        # 测试3：验证标记效果
        logger.info("=" * 60)
        logger.info("测试3：验证标记效果")
        
        # 再次尝试获取相同的批次
        new_batch = await db_operations.get_process_urls_batch(5)
        logger.info(f"📊 再次获取到 {len(new_batch)} 个待处理页面")
        
        # 检查是否获取到了不同的页面
        if new_batch:
            new_urls = [url for url, _ in new_batch]
            overlap = set(urls) & set(new_urls)
            
            if overlap:
                logger.error(f"❌ 发现重复页面: {len(overlap)} 个")
                for url in list(overlap)[:3]:
                    logger.error(f"   重复: {url[:80]}...")
            else:
                logger.info("✅ 没有重复页面，标记功能正常")
        else:
            logger.info("✅ 没有更多待处理页面，可能所有页面都已标记")
        
        # 测试4：统计信息
        logger.info("=" * 60)
        logger.info("测试4：统计信息")
        
        # 查询总数和已处理数
        total_result = await db_client.fetch_one("""
            SELECT COUNT(*) as count FROM pages
            WHERE content IS NOT NULL AND content != ''
            AND (url = 'https://developer.apple.com/documentation'
                 OR url LIKE 'https://developer.apple.com/documentation/%')
        """)
        
        processed_result = await db_client.fetch_one("""
            SELECT COUNT(*) as count FROM pages
            WHERE processed_at IS NOT NULL
            AND content IS NOT NULL AND content != ''
            AND (url = 'https://developer.apple.com/documentation'
                 OR url LIKE 'https://developer.apple.com/documentation/%')
        """)
        
        unprocessed_result = await db_client.fetch_one("""
            SELECT COUNT(*) as count FROM pages
            WHERE processed_at IS NULL
            AND content IS NOT NULL AND content != ''
            AND (url = 'https://developer.apple.com/documentation'
                 OR url LIKE 'https://developer.apple.com/documentation/%')
        """)
        
        total = total_result['count']
        processed = processed_result['count']
        unprocessed = unprocessed_result['count']
        
        logger.info(f"📊 Apple文档统计:")
        logger.info(f"   总数: {total}")
        logger.info(f"   已处理: {processed}")
        logger.info(f"   未处理: {unprocessed}")
        logger.info(f"   处理进度: {(processed/total*100):.2f}%")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        
    finally:
        await db_client.close()
        logger.info("🔒 数据库连接已关闭")


async def main():
    """主函数"""
    logger.info("🚀 开始测试批次级别标记修复...")
    await test_batch_marking()
    logger.info("🎉 测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
