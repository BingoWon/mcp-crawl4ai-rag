#!/usr/bin/env python3
"""
一次性重置processed_at字段

执行一次性的重置操作，将所有Apple文档的processed_at字段设为NULL
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

from src.database import create_database_client, DatabaseOperations
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def reset_processed_at():
    """执行一次性重置操作"""
    logger.info("🔄 开始一次性重置Apple文档的processed_at字段...")
    
    # 初始化数据库连接
    db_client = create_database_client()
    await db_client.initialize()
    db_operations = DatabaseOperations(db_client)
    
    try:
        # 执行重置
        reset_count = await db_operations.reset_apple_pages_for_bulk_update()
        
        logger.info(f"✅ 重置完成！共重置了 {reset_count} 个Apple文档的processed_at字段")
        logger.info("📊 现在可以运行批量更新工具进行chunking更新")
        
    except Exception as e:
        logger.error(f"❌ 重置失败: {e}")
        
    finally:
        await db_client.close()
        logger.info("🔒 数据库连接已关闭")


async def main():
    """主函数"""
    logger.info("🚀 执行一次性processed_at字段重置...")
    await reset_processed_at()
    logger.info("🎉 重置操作完成！")


if __name__ == "__main__":
    asyncio.run(main())
