#!/usr/bin/env python3
"""
测试无限爬取逻辑 - 短时间运行验证
"""

import asyncio
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.client import PostgreSQLClient
from crawler.core import IndependentCrawler


async def test_short_infinite_crawl():
    """测试短时间的无限爬取"""
    print("🧪 测试无限爬取逻辑（5次循环后停止）")
    
    # 清空数据库
    async with PostgreSQLClient() as client:
        await client.execute_command("DELETE FROM chunks")
        await client.execute_command("DELETE FROM pages")
        print("数据库已清空")
    
    # 开始爬取
    async with IndependentCrawler() as crawler:
        # 修改爬取方法以支持限制次数
        start_url = "https://developer.apple.com/documentation/"
        
        if not start_url.startswith(crawler.APPLE_DOCS_URL_PREFIX):
            print("❌ URL不支持")
            return

        # Insert start URL if not exists
        await crawler.db_operations.insert_url_if_not_exists(start_url)
        print(f"开始无限爬取: {start_url}")

        crawl_count = 0
        max_crawls = 3  # 限制爬取次数用于测试
        
        while crawl_count < max_crawls:
            try:
                # Get next URL and content to crawl (minimum crawl_count)
                result = await crawler.db_operations.get_next_crawl_url()
                if not result:
                    print("没有URL可爬取")
                    break

                next_url, existing_content = result
                crawl_count += 1
                print(f"\n=== 爬取 #{crawl_count}: {next_url} ===")

                # Crawl and process the URL
                await crawler._crawl_and_process_url(next_url, bool(existing_content))
                
                # 显示当前状态
                async with PostgreSQLClient() as client:
                    pages_count = await client.fetch_val("SELECT COUNT(*) FROM pages")
                    chunks_count = await client.fetch_val("SELECT COUNT(*) FROM chunks")
                    print(f"当前状态: {pages_count} 页面, {chunks_count} 块")
                    
                    # 显示爬取次数分布
                    crawl_stats = await client.execute_query("""
                        SELECT crawl_count, COUNT(*) as count 
                        FROM pages 
                        GROUP BY crawl_count 
                        ORDER BY crawl_count
                    """)
                    print("爬取次数分布:", dict((row['crawl_count'], row['count']) for row in crawl_stats))

            except Exception as e:
                print(f"爬取错误: {e}")
                break
        
        print(f"\n✅ 测试完成，共爬取 {crawl_count} 次")


async def main():
    """主测试函数"""
    print("🚀 开始测试无限爬取逻辑")
    print("=" * 50)
    
    try:
        await test_short_infinite_crawl()
        
        # 显示最终统计
        async with PostgreSQLClient() as client:
            print("\n📊 最终统计:")
            pages = await client.execute_query("""
                SELECT url, crawl_count, 
                       LENGTH(content) as content_length,
                       created_at, updated_at
                FROM pages 
                ORDER BY crawl_count DESC, created_at
            """)
            
            for page in pages:
                print(f"  {page['url']}")
                print(f"    爬取次数: {page['crawl_count']}")
                print(f"    内容长度: {page['content_length']} 字符")
                print(f"    创建: {page['created_at']}")
                print(f"    更新: {page['updated_at']}")
                print()
        
        print("🎉 测试完成!")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
