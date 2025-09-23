#!/usr/bin/env python3
"""
YouTube标题更新脚本

功能：
- 从pages表获取所有YouTube记录的URL和content
- 从content字段的JSON数据中提取title (context字段)
- 更新pages表中对应记录的title字段
- 打印所有YouTube视频标题

专用脚本：只处理title字段更新，不做其他操作
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional

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


class YouTubeTitleUpdater:
    """YouTube标题更新器 - 专用于title字段更新"""
    
    def __init__(self):
        self.db_client = None
        self.processed_count = 0
        self.failed_count = 0
        self.titles_list = []
    
    async def initialize(self):
        """初始化数据库连接"""
        logger.info("🔗 初始化数据库连接...")
        self.db_client = create_database_client()
        await self.db_client.initialize()
        logger.info("✅ 数据库连接成功")
    
    async def get_all_youtube_records(self) -> List[Tuple[str, str]]:
        """
        获取所有YouTube记录的URL和content
        
        Returns:
            List of (url, content) tuples
        """
        logger.info("📊 获取所有YouTube记录...")
        
        query = """
            SELECT url, content
            FROM pages
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
            AND content IS NOT NULL
            AND content != ''
            ORDER BY url
        """
        
        records = await self.db_client.fetch_all(query)
        logger.info(f"✅ 获取到 {len(records)} 条YouTube记录")
        
        return [(record['url'], record['content']) for record in records]
    
    def extract_title_from_content(self, content: str) -> Optional[str]:
        """
        从content的JSON数据中提取title
        
        Args:
            content: JSON字符串内容
            
        Returns:
            提取的title，失败返回None
        """
        try:
            video_data = json.loads(content)
            title = video_data.get("context", "")
            return title if title else None
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 提取title失败: {e}")
            return None
    
    async def update_single_title(self, url: str, title: str) -> bool:
        """
        更新单个记录的title字段
        
        Args:
            url: YouTube URL
            title: 提取的标题
            
        Returns:
            更新是否成功
        """
        try:
            query = """
                UPDATE pages
                SET title = $1, updated_at = NOW()
                WHERE url = $2
            """
            
            await self.db_client.execute_command(query, title, url)
            return True
            
        except Exception as e:
            logger.error(f"❌ 更新title失败 {url}: {e}")
            return False
    
    async def process_all_records(self):
        """处理所有YouTube记录，提取并更新title"""
        logger.info("🚀 开始处理所有YouTube记录...")
        
        # 获取所有记录
        records = await self.get_all_youtube_records()
        
        if not records:
            logger.info("ℹ️ 没有找到YouTube记录")
            return
        
        total_records = len(records)
        logger.info(f"📊 开始处理 {total_records} 条记录")
        
        print("\n" + "=" * 80)
        print("📋 所有YouTube视频标题:")
        print("=" * 80)
        
        for i, (url, content) in enumerate(records, 1):
            logger.info(f"📹 处理进度: {i}/{total_records}")
            
            # 提取title
            title = self.extract_title_from_content(content)
            
            if title:
                # 打印标题
                print(f"{i:3d}. {title}")
                self.titles_list.append(title)
                
                # 更新数据库
                success = await self.update_single_title(url, title)
                
                if success:
                    self.processed_count += 1
                    logger.info(f"✅ 更新成功: {title[:50]}...")
                else:
                    self.failed_count += 1
                    logger.error(f"❌ 更新失败: {url}")
            else:
                self.failed_count += 1
                logger.error(f"❌ 无法提取title: {url}")
        
        # 打印统计结果
        self._print_summary()
    
    def _print_summary(self):
        """打印处理统计摘要"""
        print("\n" + "=" * 80)
        print("📊 处理统计摘要")
        print("=" * 80)
        
        total_processed = self.processed_count + self.failed_count
        success_rate = (self.processed_count / total_processed * 100) if total_processed > 0 else 0
        
        print(f"📈 处理结果:")
        print(f"   总记录数: {total_processed}")
        print(f"   成功更新: {self.processed_count}")
        print(f"   更新失败: {self.failed_count}")
        print(f"   成功率: {success_rate:.1f}%")
        
        print(f"\n📋 标题统计:")
        print(f"   提取标题数: {len(self.titles_list)}")
        
        if self.titles_list:
            avg_length = sum(len(title) for title in self.titles_list) / len(self.titles_list)
            print(f"   平均标题长度: {avg_length:.1f} 字符")
            print(f"   最长标题: {max(self.titles_list, key=len)[:100]}...")
            print(f"   最短标题: {min(self.titles_list, key=len)}")
        
        print("\n🎉 YouTube标题更新完成！")
    
    async def cleanup(self):
        """清理资源"""
        if self.db_client:
            await self.db_client.close()
            logger.info("🔒 数据库连接已关闭")


async def main():
    """主函数"""
    updater = YouTubeTitleUpdater()
    
    try:
        await updater.initialize()
        await updater.process_all_records()
        
    except Exception as e:
        logger.error(f"❌ 处理过程中出现错误: {e}")
        
    finally:
        await updater.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
