#!/usr/bin/env python3
"""
删除确认的测试数据

只删除Swift文档URL中确认的测试内容
"""

import asyncio
import sys
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


async def delete_test_data():
    """删除确认的测试数据"""
    logger.info("🗑️ 开始删除确认的测试数据...")
    
    # 初始化数据库连接
    db_client = create_database_client()
    await db_client.initialize()
    
    try:
        # 确认要删除的数据
        test_id = "37759e1c-6d06-4a90-8bcb-66a50b75d75f"
        test_url = "https://developer.apple.com/documentation/swift"
        
        logger.info("=" * 80)
        logger.info("步骤1：确认要删除的测试数据")
        
        # 查询确认数据存在
        result = await db_client.fetch_one("""
            SELECT id, url, content, LENGTH(content) as content_length
            FROM chunks
            WHERE id = $1
        """, test_id)
        
        if not result:
            logger.warning(f"⚠️ 未找到ID为 {test_id} 的记录")
            return
        
        logger.info(f"📋 找到要删除的记录:")
        logger.info(f"   ID: {result['id']}")
        logger.info(f"   URL: {result['url']}")
        logger.info(f"   内容长度: {result['content_length']}")
        logger.info(f"   内容预览: {result['content'][:100]}...")
        
        # 确认这是测试数据
        if "Test content for database update" not in result['content']:
            logger.error("❌ 这不是预期的测试数据，停止删除操作")
            return
        
        if result['url'] != test_url:
            logger.error("❌ URL不匹配，停止删除操作")
            return
        
        logger.info("✅ 确认这是需要删除的测试数据")
        
        # 步骤2：执行删除
        logger.info("=" * 80)
        logger.info("步骤2：执行删除操作")
        
        delete_result = await db_client.execute_command("""
            DELETE FROM chunks WHERE id = $1
        """, test_id)
        
        logger.info(f"🗑️ 删除操作结果: {delete_result}")
        
        # 步骤3：验证删除结果
        logger.info("=" * 80)
        logger.info("步骤3：验证删除结果")
        
        # 确认记录已被删除
        verify_result = await db_client.fetch_one("""
            SELECT id FROM chunks WHERE id = $1
        """, test_id)
        
        if verify_result:
            logger.error("❌ 删除失败，记录仍然存在")
        else:
            logger.info("✅ 删除成功，记录已不存在")
        
        # 检查Swift URL是否还有其他chunks
        swift_results = await db_client.fetch_all("""
            SELECT id, LENGTH(content) as content_length
            FROM chunks
            WHERE url = $1
        """, test_url)
        
        logger.info(f"📊 Swift URL剩余chunks数量: {len(swift_results)}")
        
        if swift_results:
            logger.info("📋 Swift URL剩余的chunks:")
            for i, row in enumerate(swift_results):
                logger.info(f"   {i+1}. ID: {row['id']}, 长度: {row['content_length']}")
        else:
            logger.info("✅ Swift URL已无任何chunks")
        
        # 步骤4：统计信息
        logger.info("=" * 80)
        logger.info("步骤4：更新后的统计信息")
        
        total_result = await db_client.fetch_one("SELECT COUNT(*) as count FROM chunks")
        total_chunks = total_result['count']
        logger.info(f"📊 删除后chunks表总记录数: {total_chunks}")
        
        # 检查是否还有其他测试数据
        test_check = await db_client.fetch_all("""
            SELECT id, url, LENGTH(content) as content_length
            FROM chunks
            WHERE LOWER(content) LIKE '%test content for database update%'
        """)
        
        if test_check:
            logger.warning(f"⚠️ 仍有 {len(test_check)} 个记录包含类似的测试内容")
            for row in test_check:
                logger.warning(f"   ID: {row['id']}, URL: {row['url']}, 长度: {row['content_length']}")
        else:
            logger.info("✅ 未发现其他类似的测试数据")
        
    except Exception as e:
        logger.error(f"❌ 删除过程中出错: {e}")
        
    finally:
        await db_client.close()
        logger.info("🔒 数据库连接已关闭")


async def main():
    """主函数"""
    logger.info("🚀 开始删除确认的测试数据...")
    await delete_test_data()
    logger.info("🎉 删除操作完成！")


if __name__ == "__main__":
    asyncio.run(main())
