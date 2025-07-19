#!/usr/bin/env python3
"""
查询特定URL的所有字段值
在pages表中查找指定URL对应的所有字段数据
"""

import sys
import asyncio
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from database import get_database_client
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def query_url_data(target_url: str):
    """查询指定URL在pages表中的所有字段值"""
    try:
        # 连接数据库
        db_client = await get_database_client()
        
        logger.info(f"🔍 查询URL: {target_url}")
        
        # 查询pages表中的所有字段
        query = """
        SELECT 
            id,
            url,
            crawl_count,
            process_count,
            created_at,
            last_crawled_at,
            content
        FROM pages 
        WHERE url = $1
        """
        
        # 执行查询
        result = await db_client.fetch_one(query, target_url)
        
        if not result:
            print(f"\n❌ 未找到URL: {target_url}")
            print("该URL在pages表中不存在")
            return
        
        print("\n" + "="*80)
        print("📋 Pages表查询结果")
        print("="*80)
        
        # 格式化输出所有字段
        print(f"🆔 ID: {result['id']}")
        print(f"🔗 URL: {result['url']}")
        print(f"🔄 爬取次数 (crawl_count): {result['crawl_count']}")
        print(f"⚙️  处理次数 (process_count): {result['process_count']}")
        print(f"📅 创建时间 (created_at): {result['created_at']}")
        print(f"🕒 最后爬取时间 (last_crawled_at): {result['last_crawled_at']}")
        
        # 内容字段特殊处理
        content = result['content']
        content_length = len(content)
        
        print(f"\n📄 内容 (content):")
        print(f"   长度: {content_length:,} 字符")
        
        if content_length > 0:
            # 显示内容预览（前500字符）
            preview = content[:500]
            print(f"   预览: {preview}")
            if content_length > 500:
                print(f"   ... (还有 {content_length - 500:,} 字符)")
        else:
            print("   内容为空")
        
        # 查询相关的chunks数据
        chunks_query = """
        SELECT 
            id,
            content,
            created_at
        FROM chunks 
        WHERE url = $1
        ORDER BY created_at ASC
        """
        
        chunks_results = await db_client.fetch_all(chunks_query, target_url)
        
        print(f"\n📦 相关Chunks数据:")
        print(f"   Chunks数量: {len(chunks_results)}")
        
        if chunks_results:
            for i, chunk in enumerate(chunks_results, 1):
                chunk_content = chunk['content']
                chunk_length = len(chunk_content)
                chunk_preview = chunk_content[:100]
                
                print(f"\n   Chunk #{i}:")
                print(f"     ID: {chunk['id']}")
                print(f"     长度: {chunk_length:,} 字符")
                print(f"     创建时间: {chunk['created_at']}")
                print(f"     内容预览: {chunk_preview}")
                if chunk_length > 100:
                    print(f"     ... (还有 {chunk_length - 100:,} 字符)")
        
        print("="*80)
        
    except Exception as e:
        logger.error(f"❌ 查询失败: {e}")
        raise

async def main():
    """主函数"""
    # 目标URL - 可以修改这里来查询不同的URL
    target_url = "https://developer.apple.com/documentation/metal/mtlcounterset/counters"
    
    # 如果命令行提供了URL参数，使用命令行参数
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    
    try:
        await query_url_data(target_url)
    except KeyboardInterrupt:
        logger.info("查询被用户中断")
    except Exception as e:
        logger.error(f"查询错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
