#!/usr/bin/env python3
"""
YouTube记录统计脚本

统计数据库中pages和chunks表中所有以 https://www.youtube.com/watch?v= 开头的URL记录数量
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
env_path = project_root / '.env'
load_dotenv(env_path)

from src.database.client import DatabaseClient
from src.utils.logger import setup_logger

# 设置logger
logger = setup_logger(__name__)


class YouTubeRecordCounter:
    """YouTube记录统计器"""
    
    def __init__(self):
        self.db_client = None
    
    async def initialize(self):
        """初始化数据库连接"""
        try:
            self.db_client = DatabaseClient()
            await self.db_client.initialize()
            logger.info("✅ 数据库连接初始化成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接初始化失败: {e}")
            raise
    
    async def count_pages_records(self) -> int:
        """统计pages表中YouTube URL记录数量"""
        query = """
            SELECT COUNT(*) as count
            FROM pages 
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
        """
        
        result = await self.db_client.fetch_one(query)
        return result['count']
    
    async def count_chunks_records(self) -> int:
        """统计chunks表中YouTube URL记录数量"""
        query = """
            SELECT COUNT(*) as count
            FROM chunks 
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
        """
        
        result = await self.db_client.fetch_one(query)
        return result['count']
    
    async def get_detailed_stats(self) -> dict:
        """获取详细统计信息"""
        # Pages表详细统计
        pages_query = """
            SELECT 
                COUNT(*) as total_pages,
                COUNT(CASE WHEN content IS NOT NULL AND content != '' THEN 1 END) as pages_with_content,
                COUNT(CASE WHEN content IS NULL OR content = '' THEN 1 END) as pages_without_content,
                AVG(LENGTH(content)) as avg_content_length
            FROM pages 
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
        """
        
        # Chunks表详细统计
        chunks_query = """
            SELECT 
                COUNT(*) as total_chunks,
                COUNT(DISTINCT url) as unique_urls,
                AVG(LENGTH(content)) as avg_chunk_length,
                MIN(LENGTH(content)) as min_chunk_length,
                MAX(LENGTH(content)) as max_chunk_length
            FROM chunks 
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
        """
        
        pages_stats = await self.db_client.fetch_one(pages_query)
        chunks_stats = await self.db_client.fetch_one(chunks_query)
        
        return {
            'pages': dict(pages_stats),
            'chunks': dict(chunks_stats)
        }
    
    async def run_count(self):
        """执行统计并显示结果"""
        try:
            await self.initialize()
            
            print("=" * 60)
            print("📊 YouTube记录统计")
            print("=" * 60)
            
            # 基础计数
            pages_count = await self.count_pages_records()
            chunks_count = await self.count_chunks_records()
            
            print(f"\n📋 基础统计:")
            print(f"   Pages表中YouTube URL记录数: {pages_count:,}")
            print(f"   Chunks表中YouTube URL记录数: {chunks_count:,}")
            
            # 详细统计
            detailed_stats = await self.get_detailed_stats()
            
            print(f"\n📈 Pages表详细统计:")
            pages_stats = detailed_stats['pages']
            print(f"   总记录数: {pages_stats['total_pages']:,}")
            print(f"   有内容的记录: {pages_stats['pages_with_content']:,}")
            print(f"   无内容的记录: {pages_stats['pages_without_content']:,}")
            if pages_stats['avg_content_length']:
                print(f"   平均内容长度: {pages_stats['avg_content_length']:.0f} 字符")
            
            print(f"\n📈 Chunks表详细统计:")
            chunks_stats = detailed_stats['chunks']
            print(f"   总chunk数: {chunks_stats['total_chunks']:,}")
            print(f"   唯一URL数: {chunks_stats['unique_urls']:,}")
            if chunks_stats['total_chunks'] > 0:
                print(f"   平均chunk长度: {chunks_stats['avg_chunk_length']:.0f} 字符")
                print(f"   最小chunk长度: {chunks_stats['min_chunk_length']:,} 字符")
                print(f"   最大chunk长度: {chunks_stats['max_chunk_length']:,} 字符")
                print(f"   平均每URL的chunks数: {chunks_stats['total_chunks'] / chunks_stats['unique_urls']:.1f}")
            
            # 处理状态分析
            if pages_count > 0:
                processed_percentage = (chunks_stats['unique_urls'] / pages_count) * 100 if chunks_stats['unique_urls'] else 0
                print(f"\n🎯 处理状态分析:")
                print(f"   已处理的URL数: {chunks_stats['unique_urls']:,}")
                print(f"   未处理的URL数: {pages_count - chunks_stats['unique_urls']:,}")
                print(f"   处理完成率: {processed_percentage:.1f}%")
            
            print("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ 统计过程中发生错误: {e}")
            raise
        finally:
            if self.db_client:
                await self.db_client.close()
                logger.info("✅ 数据库连接已关闭")


async def main():
    """主函数"""
    counter = YouTubeRecordCounter()
    await counter.run_count()


if __name__ == "__main__":
    asyncio.run(main())
