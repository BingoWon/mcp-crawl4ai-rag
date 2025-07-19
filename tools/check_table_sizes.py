#!/usr/bin/env python3
"""
数据库表存储空间查询工具
查询pages和chunks表在硬盘中占据的存储空间
"""

import sys
import asyncio
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from database import get_database_client
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def check_table_sizes():
    """查询数据库表的存储空间使用情况"""
    try:
        # 连接数据库
        db_client = await get_database_client()
        
        logger.info("🔍 查询数据库表存储空间...")
        
        # 查询表大小的SQL
        table_size_query = """
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
            pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
            pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename IN ('pages', 'chunks')
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """
        
        # 执行查询
        results = await db_client.fetch_all(table_size_query)
        
        if not results:
            logger.info("❌ 未找到pages或chunks表")
            return
        
        print("\n" + "="*80)
        print("📊 数据库表存储空间统计")
        print("="*80)
        
        total_size_bytes = 0
        
        for row in results:
            schema = row['schemaname']
            table = row['tablename']
            total_size = row['size']
            size_bytes = row['size_bytes']
            table_size = row['table_size']
            index_size = row['index_size']
            
            total_size_bytes += size_bytes
            
            print(f"\n📋 表名: {schema}.{table}")
            print(f"   总大小: {total_size}")
            print(f"   表数据: {table_size}")
            print(f"   索引大小: {index_size}")
            print(f"   字节数: {size_bytes:,}")
        
        # 查询记录数量
        print(f"\n📈 记录数量统计:")
        
        for table_name in ['pages', 'chunks']:
            try:
                count_result = await db_client.fetch_one(f"SELECT COUNT(*) as count FROM {table_name}")
                count = count_result['count'] if count_result else 0
                print(f"   {table_name}: {count:,} 条记录")
            except Exception as e:
                print(f"   {table_name}: 查询失败 - {e}")
        
        # 总计
        total_size_mb = total_size_bytes / (1024 * 1024)
        total_size_gb = total_size_bytes / (1024 * 1024 * 1024)
        
        print(f"\n🎯 总存储空间:")
        print(f"   总计: {total_size_bytes:,} 字节")
        print(f"   总计: {total_size_mb:.2f} MB")
        print(f"   总计: {total_size_gb:.3f} GB")
        
        # 查询数据库整体信息
        db_size_query = """
        SELECT 
            pg_database.datname,
            pg_size_pretty(pg_database_size(pg_database.datname)) AS size
        FROM pg_database 
        WHERE pg_database.datname = current_database();
        """
        
        db_result = await db_client.fetch_one(db_size_query)
        if db_result:
            print(f"\n🗄️  整个数据库大小: {db_result['size']}")
        
        print("="*80)
        
    except Exception as e:
        logger.error(f"❌ 查询失败: {e}")
        raise

async def main():
    """主函数"""
    try:
        await check_table_sizes()
    except KeyboardInterrupt:
        logger.info("查询被用户中断")
    except Exception as e:
        logger.error(f"查询错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
