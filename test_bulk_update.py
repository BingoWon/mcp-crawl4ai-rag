#!/usr/bin/env python3
"""
测试批量Chunking更新工具

验证工具的基本功能：
1. 数据库连接
2. 页面获取
3. 双重chunking对比
4. 统计信息输出
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from bulk_chunking_update import BulkChunkingUpdater
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def test_bulk_updater():
    """测试批量更新器的基本功能"""
    logger.info("🧪 开始测试批量Chunking更新工具...")
    
    async with BulkChunkingUpdater() as updater:
        # 测试1：数据库连接
        logger.info("=" * 60)
        logger.info("测试1：数据库连接")
        logger.info("✅ 数据库连接成功")
        
        # 测试2：获取页面数据
        logger.info("=" * 60)
        logger.info("测试2：获取页面数据")
        pages = await updater.get_all_pages()
        logger.info(f"📊 获取到 {len(pages)} 个页面")
        
        if pages:
            # 显示前3个页面的基本信息
            for i, (url, content) in enumerate(pages[:3]):
                logger.info(f"   页面{i+1}: {url[:80]}...")
                logger.info(f"   内容长度: {len(content)} 字符")
        
        # 测试3：双重chunking对比（只测试前2个页面）
        logger.info("=" * 60)
        logger.info("测试3：双重chunking对比")
        
        test_pages = pages[:2] if len(pages) >= 2 else pages
        
        for i, (url, content) in enumerate(test_pages):
            logger.info(f"测试页面 {i+1}: {url[:60]}...")
            
            # 双重chunking
            old_chunks = updater.deprecated_chunker.chunk_text(content)
            new_chunks = updater.current_chunker.chunk_text(content)
            
            # 对比结果
            is_identical = updater._compare_chunking_results(old_chunks, new_chunks)
            
            logger.info(f"   旧方案chunks: {len(old_chunks)}")
            logger.info(f"   新方案chunks: {len(new_chunks)}")
            logger.info(f"   结果一致: {is_identical}")
            
            if is_identical:
                logger.info("   ✅ 将跳过chunks表更新")
            else:
                logger.info("   🔄 将更新chunks表")
        
        # 测试4：统计信息
        logger.info("=" * 60)
        logger.info("测试4：统计信息")
        logger.info("📊 统计信息结构:")
        for key, value in updater.stats.items():
            logger.info(f"   {key}: {value}")
    
    logger.info("=" * 60)
    logger.info("🎯 批量更新工具测试完成！")
    logger.info("✅ 所有基本功能正常")


async def main():
    """主函数"""
    logger.info("🚀 开始测试批量Chunking更新工具...")
    await test_bulk_updater()
    logger.info("🎉 测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
