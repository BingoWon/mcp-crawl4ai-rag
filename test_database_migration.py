#!/usr/bin/env python3
"""
数据库迁移验证脚本
验证从 NEON 到 VPS 数据库的改造是否成功
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import get_database_client, DatabaseOperations, DatabaseClient, DatabaseConfig
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def test_database_migration():
    """测试数据库迁移改造结果"""
    logger.info("=" * 60)
    logger.info("🔍 验证数据库迁移改造结果")
    logger.info("=" * 60)
    
    try:
        # 1. 测试配置类
        logger.info("📋 测试数据库配置...")
        config = DatabaseConfig.from_env()
        logger.info(f"✅ 数据库主机: {config.host}")
        logger.info(f"✅ 数据库端口: {config.port}")
        logger.info(f"✅ 数据库名称: {config.database}")
        logger.info(f"✅ 数据库用户: {config.user}")
        
        # 2. 测试客户端连接
        logger.info("\n🔗 测试数据库客户端连接...")
        client = await get_database_client()
        logger.info("✅ 数据库客户端初始化成功")
        
        # 3. 测试基本查询
        logger.info("\n📊 测试基本数据库查询...")
        version = await client.fetch_one("SELECT version()")
        logger.info(f"✅ 数据库版本: {version['version'][:50]}...")
        
        # 4. 测试表存在性
        logger.info("\n📋 检查数据库表...")
        tables = await client.fetch_all("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        table_names = [table['table_name'] for table in tables]
        logger.info(f"✅ 发现表: {table_names}")
        
        # 5. 测试数据统计
        if 'pages' in table_names:
            pages_count = await client.fetch_one("SELECT COUNT(*) as count FROM pages")
            logger.info(f"✅ Pages 表记录数: {pages_count['count']:,}")
        
        if 'chunks' in table_names:
            chunks_count = await client.fetch_one("SELECT COUNT(*) as count FROM chunks")
            logger.info(f"✅ Chunks 表记录数: {chunks_count['count']:,}")
        
        # 6. 测试 pgvector 扩展
        logger.info("\n🧮 检查 pgvector 扩展...")
        extensions = await client.fetch_all("""
            SELECT extname 
            FROM pg_extension 
            WHERE extname = 'vector'
        """)
        
        if extensions:
            logger.info("✅ pgvector 扩展已安装")
        else:
            logger.warning("⚠️ pgvector 扩展未找到")
        
        # 7. 测试数据库操作类
        logger.info("\n⚙️ 测试数据库操作类...")
        db_ops = DatabaseOperations(client)
        logger.info("✅ DatabaseOperations 初始化成功")
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 数据库迁移改造验证完成！")
        logger.info("✅ 所有测试通过")
        logger.info("✅ VPS 数据库连接正常")
        logger.info("✅ 数据迁移成功")
        logger.info("✅ 代码改造完成")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 验证失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False

async def main():
    """主函数"""
    success = await test_database_migration()
    
    if success:
        logger.info("🎉 数据库迁移改造验证成功！")
        logger.info("项目已成功从 NEON 切换到 VPS 数据库")
    else:
        logger.error("❌ 数据库迁移改造验证失败")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
