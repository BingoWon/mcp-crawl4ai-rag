#!/usr/bin/env python3
"""
YouTube字幕数据导入数据库脚本

功能：
- 读取所有YouTube字幕JSON文件
- 转换为pages表格式
- 批量导入到PostgreSQL数据库

数据格式：
- URL: https://www.youtube.com/watch?v={video_id}
- content: 完整JSON字符串
- created_at: NOW()
- processed_at: NULL
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple

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


class YouTubeDataImporter:
    """YouTube字幕数据导入器"""
    
    def __init__(self, subtitles_dir: str = "subtitles"):
        self.subtitles_dir = Path(subtitles_dir)
        self.db_client = None
        
    async def initialize(self):
        """初始化数据库连接"""
        logger.info("🔗 初始化数据库连接...")
        self.db_client = create_database_client()
        await self.db_client.initialize()
        logger.info("✅ 数据库连接成功")
        
    async def load_json_files(self) -> List[Tuple[str, Dict]]:
        """加载所有JSON文件"""
        logger.info(f"📂 扫描字幕目录: {self.subtitles_dir}")
        
        json_files = list(self.subtitles_dir.glob("*.json"))
        logger.info(f"📊 找到 {len(json_files)} 个JSON文件")
        
        data_list = []
        failed_files = []
        
        for json_file in json_files:
            try:
                # 从文件名提取video_id
                video_id = json_file.stem
                
                # 读取JSON内容
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                data_list.append((video_id, json_data))
                
            except Exception as e:
                logger.error(f"❌ 读取文件失败 {json_file}: {e}")
                failed_files.append(str(json_file))
        
        logger.info(f"✅ 成功加载 {len(data_list)} 个文件")
        if failed_files:
            logger.warning(f"⚠️ 失败文件数: {len(failed_files)}")
            
        return data_list
    
    def prepare_database_records(self, data_list: List[Tuple[str, Dict]]) -> List[Tuple[str, str, str]]:
        """准备数据库插入记录"""
        logger.info("🔄 准备数据库记录...")

        records = []
        for video_id, json_data in data_list:
            # 构造YouTube URL
            url = f"https://www.youtube.com/watch?v={video_id}"

            # 将JSON数据转换为字符串
            content = json.dumps(json_data, ensure_ascii=False, indent=2)

            # 提取title字段
            title = json_data.get("context", "")

            records.append((url, content, title))

        logger.info(f"✅ 准备了 {len(records)} 条记录")
        return records
    
    async def check_existing_urls(self, urls: List[str]) -> List[str]:
        """检查已存在的URL"""
        logger.info("🔍 检查数据库中已存在的URL...")
        
        if not urls:
            return []
        
        # 查询已存在的URL
        placeholders = ','.join([f'${i+1}' for i in range(len(urls))])
        query = f"""
            SELECT url FROM pages 
            WHERE url IN ({placeholders})
        """
        
        existing_records = await self.db_client.fetch_all(query, *urls)
        existing_urls = [record['url'] for record in existing_records]
        
        logger.info(f"📊 已存在URL数量: {len(existing_urls)}")
        return existing_urls
    
    async def insert_records(self, records: List[Tuple[str, str]], 
                           handle_duplicates: str = "skip") -> Dict[str, int]:
        """插入记录到数据库"""
        logger.info(f"💾 开始插入 {len(records)} 条记录...")
        logger.info(f"🔧 重复处理策略: {handle_duplicates}")
        
        urls = [record[0] for record in records]
        existing_urls = await self.check_existing_urls(urls)
        
        stats = {
            "total": len(records),
            "existing": len(existing_urls),
            "inserted": 0,
            "updated": 0,
            "failed": 0
        }
        
        if handle_duplicates == "skip":
            # 跳过已存在的记录
            new_records = [
                record for record in records 
                if record[0] not in existing_urls
            ]
            
            if new_records:
                try:
                    await self.db_client.execute_many("""
                        INSERT INTO pages (url, content, title, created_at)
                        VALUES ($1, $2, $3, NOW())
                    """, new_records)
                    
                    stats["inserted"] = len(new_records)
                    logger.info(f"✅ 成功插入 {len(new_records)} 条新记录")
                    
                except Exception as e:
                    logger.error(f"❌ 插入失败: {e}")
                    stats["failed"] = len(new_records)
            else:
                logger.info("ℹ️ 所有记录都已存在，跳过插入")
                
        elif handle_duplicates == "update":
            # 更新已存在的记录
            existing_records = [
                record for record in records 
                if record[0] in existing_urls
            ]
            new_records = [
                record for record in records 
                if record[0] not in existing_urls
            ]
            
            # 插入新记录
            if new_records:
                try:
                    await self.db_client.execute_many("""
                        INSERT INTO pages (url, content, title, created_at)
                        VALUES ($1, $2, $3, NOW())
                    """, new_records)
                    stats["inserted"] = len(new_records)
                    logger.info(f"✅ 成功插入 {len(new_records)} 条新记录")
                except Exception as e:
                    logger.error(f"❌ 插入新记录失败: {e}")
                    stats["failed"] += len(new_records)
            
            # 更新已存在的记录
            if existing_records:
                try:
                    await self.db_client.execute_many("""
                        UPDATE pages
                        SET content = $2, title = $3, updated_at = NOW()
                        WHERE url = $1
                    """, existing_records)
                    stats["updated"] = len(existing_records)
                    logger.info(f"✅ 成功更新 {len(existing_records)} 条已存在记录")
                except Exception as e:
                    logger.error(f"❌ 更新记录失败: {e}")
                    stats["failed"] += len(existing_records)
        
        return stats
    
    async def verify_import(self, sample_urls: List[str] = None) -> Dict[str, any]:
        """验证导入结果"""
        logger.info("🔍 验证导入结果...")
        
        # 统计YouTube URL数量
        youtube_count = await self.db_client.fetch_val("""
            SELECT COUNT(*) FROM pages 
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
        """)
        
        # 获取样本数据
        sample_data = await self.db_client.fetch_all("""
            SELECT url, LENGTH(content) as content_length, created_at
            FROM pages
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        verification = {
            "youtube_urls_count": youtube_count,
            "sample_data": sample_data
        }
        
        logger.info(f"📊 YouTube URL总数: {youtube_count}")
        logger.info("📝 样本数据:")
        for sample in sample_data:
            logger.info(f"  - {sample['url']}: {sample['content_length']}字符, {sample['created_at']}")
        
        return verification
    
    async def run_import(self, handle_duplicates: str = "skip") -> Dict[str, any]:
        """运行完整导入流程"""
        try:
            await self.initialize()
            
            # 加载JSON文件
            data_list = await self.load_json_files()
            if not data_list:
                logger.error("❌ 没有找到有效的JSON文件")
                return {"success": False, "error": "No valid JSON files found"}
            
            # 准备数据库记录
            records = self.prepare_database_records(data_list)
            
            # 插入记录
            stats = await self.insert_records(records, handle_duplicates)
            
            # 验证结果
            verification = await self.verify_import()
            
            logger.info("🎉 导入完成！")
            
            return {
                "success": True,
                "stats": stats,
                "verification": verification
            }
            
        except Exception as e:
            logger.error(f"❌ 导入过程中出现错误: {e}")
            return {"success": False, "error": str(e)}
            
        finally:
            if self.db_client:
                await self.db_client.close()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube字幕数据导入数据库")
    parser.add_argument("--duplicates", choices=["skip", "update"], default="skip",
                       help="重复URL处理策略: skip(跳过) 或 update(更新)")
    parser.add_argument("--subtitles-dir", default="subtitles",
                       help="字幕文件目录")
    
    args = parser.parse_args()
    
    logger.info("🚀 开始YouTube字幕数据导入...")
    logger.info(f"📂 字幕目录: {args.subtitles_dir}")
    logger.info(f"🔧 重复处理: {args.duplicates}")
    
    importer = YouTubeDataImporter(args.subtitles_dir)
    result = await importer.run_import(args.duplicates)
    
    if result["success"]:
        stats = result["stats"]
        logger.info("=" * 50)
        logger.info("📊 导入统计:")
        logger.info(f"   总记录数: {stats['total']}")
        logger.info(f"   已存在: {stats['existing']}")
        logger.info(f"   新插入: {stats['inserted']}")
        logger.info(f"   更新: {stats['updated']}")
        logger.info(f"   失败: {stats['failed']}")
        logger.info(f"   成功率: {((stats['inserted'] + stats['updated']) / stats['total'] * 100):.1f}%")
        
        verification = result["verification"]
        logger.info(f"📈 数据库中YouTube URL总数: {verification['youtube_urls_count']}")
        
    else:
        logger.error(f"❌ 导入失败: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
