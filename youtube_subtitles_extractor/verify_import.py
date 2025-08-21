#!/usr/bin/env python3
"""
验证YouTube数据导入结果
"""

import asyncio
import json
import sys
from pathlib import Path

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


async def verify_data():
    """验证导入的数据"""
    client = create_database_client()
    await client.initialize()
    
    try:
        # 查看YouTube数据统计
        logger.info('=== YouTube数据统计 ===')
        stats = await client.fetch_one('''
            SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN content IS NOT NULL AND content != '' THEN 1 END) as with_content,
                COUNT(CASE WHEN processed_at IS NULL THEN 1 END) as unprocessed,
                AVG(LENGTH(content)) as avg_content_length
            FROM pages 
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
        ''')
        
        logger.info(f'总YouTube记录: {stats["total_count"]}')
        logger.info(f'有内容记录: {stats["with_content"]}')
        logger.info(f'未处理记录: {stats["unprocessed"]}')
        logger.info(f'平均内容长度: {stats["avg_content_length"]:.0f}字符')
        
        # 查看样本数据
        logger.info('\n=== 样本数据 ===')
        samples = await client.fetch_all('''
            SELECT url, LENGTH(content) as content_length, 
                   LEFT(content, 100) as content_preview
            FROM pages 
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
            ORDER BY LENGTH(content) DESC
            LIMIT 3
        ''')
        
        for i, sample in enumerate(samples, 1):
            logger.info(f'{i}. {sample["url"]}')
            logger.info(f'   长度: {sample["content_length"]}字符')
            logger.info(f'   预览: {sample["content_preview"]}...')
        
        # 验证JSON格式
        logger.info('\n=== JSON格式验证 ===')
        json_sample = await client.fetch_one('''
            SELECT content FROM pages 
            WHERE url LIKE 'https://www.youtube.com/watch?v=%'
            LIMIT 1
        ''')
        
        try:
            parsed = json.loads(json_sample['content'])
            logger.info('✅ JSON格式正确')
            logger.info(f'包含字段: {list(parsed.keys())}')
            if 'context' in parsed:
                logger.info(f'context: {parsed["context"]}')
            if 'content' in parsed:
                logger.info(f'content长度: {len(parsed["content"])}字符')
        except Exception as e:
            logger.error(f'❌ JSON格式错误: {e}')
        
        # 总体数据库统计
        logger.info('\n=== 总体数据库统计 ===')
        total_stats = await client.fetch_one('''
            SELECT 
                COUNT(*) as total_pages,
                COUNT(CASE WHEN url LIKE 'https://www.youtube.com/watch?v=%' THEN 1 END) as youtube_pages,
                COUNT(CASE WHEN url LIKE 'https://developer.apple.com/%' THEN 1 END) as apple_pages
            FROM pages
        ''')
        
        logger.info(f'总页面数: {total_stats["total_pages"]}')
        logger.info(f'YouTube页面: {total_stats["youtube_pages"]}')
        logger.info(f'Apple页面: {total_stats["apple_pages"]}')
        
        return {
            "success": True,
            "youtube_count": stats["total_count"],
            "total_pages": total_stats["total_pages"]
        }
        
    except Exception as e:
        logger.error(f"❌ 验证过程中出现错误: {e}")
        return {"success": False, "error": str(e)}
        
    finally:
        await client.close()


async def main():
    """主函数"""
    logger.info("🔍 开始验证YouTube数据导入结果...")
    
    result = await verify_data()
    
    if result["success"]:
        logger.info("✅ 验证完成！")
        logger.info(f"📊 YouTube数据: {result['youtube_count']}条")
        logger.info(f"📈 总页面数: {result['total_pages']}条")
    else:
        logger.error(f"❌ 验证失败: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
