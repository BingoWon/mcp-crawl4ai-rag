#!/usr/bin/env python3
"""
删除YouTube Chunks记录脚本

安全删除chunks表中所有以 https://www.youtube.com/watch?v= 开头的URL记录
"""

import asyncio
import sys
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


class YouTubeChunksDeleter:
    """YouTube Chunks删除器"""
    
    def __init__(self):
        self.db_client = None
    
    async def initialize(self):
        """初始化数据库连接"""
        try:
            self.db_client = DatabaseClient()
            await self.db_client.initialize()
        except Exception as e:
            logger.error(f"❌ 数据库连接初始化失败: {e}")
            raise
    
    async def count_youtube_chunks(self) -> dict:
        """统计即将删除的YouTube chunks记录"""
        query = """
            SELECT 
                COUNT(*) as total_chunks,
                COUNT(DISTINCT url) as unique_urls,
                MIN(created_at) as earliest_created,
                MAX(created_at) as latest_created
            FROM chunks 
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
        """
        
        result = await self.db_client.fetch_one(query)
        return dict(result)
    

    
    async def delete_youtube_chunks(self) -> int:
        """删除YouTube chunks记录"""
        delete_query = """
            DELETE FROM chunks 
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
        """
        
        result = await self.db_client.execute_command(delete_query)
        
        # 解析删除的记录数
        # PostgreSQL返回格式: "DELETE n" 其中n是删除的行数
        if result and result.startswith("DELETE "):
            return int(result.split()[1])
        return 0
    
    async def run_deletion(self):
        """执行删除操作"""
        try:
            await self.initialize()

            # 1. 统计即将删除的记录
            stats = await self.count_youtube_chunks()

            if stats['total_chunks'] == 0:
                return

            # 2. 确认删除操作
            confirmation = input(f"确认删除 {stats['total_chunks']:,} 条YouTube chunks记录吗？输入 'DELETE' 来确认: ")

            if confirmation != 'DELETE':
                return

            # 3. 执行删除
            await self.delete_youtube_chunks()
            
        except Exception as e:
            logger.error(f"❌ 删除过程中发生错误: {e}")
            raise
        finally:
            if self.db_client:
                await self.db_client.close()


async def main():
    """主函数"""
    deleter = YouTubeChunksDeleter()
    await deleter.run_deletion()


if __name__ == "__main__":
    asyncio.run(main())
