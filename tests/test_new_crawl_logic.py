#!/usr/bin/env python3
"""
测试新的数据库驱动爬取逻辑
"""

import asyncio
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.client import PostgreSQLClient
from database.operations import DatabaseOperations
from crawler.core import IndependentCrawler


async def test_database_operations():
    """测试新的数据库操作方法"""
    print("🧪 测试数据库操作方法")
    
    async with PostgreSQLClient() as client:
        db_ops = DatabaseOperations(client)
        
        # 测试插入URL
        test_url = "https://developer.apple.com/documentation/test"
        inserted = await db_ops.insert_url_if_not_exists(test_url)
        print(f"插入新URL: {inserted}")
        
        # 再次插入相同URL（应该返回False）
        inserted_again = await db_ops.insert_url_if_not_exists(test_url)
        print(f"重复插入URL: {inserted_again}")
        
        # 获取下一个爬取URL
        next_url = await db_ops.get_next_crawl_url()
        print(f"下一个爬取URL: {next_url}")
        
        # 更新页面内容
        await db_ops.update_page_after_crawl(test_url, "测试内容")
        print("更新页面内容完成")
        
        # 再次获取下一个URL（crawl_count应该增加了）
        next_url_after = await db_ops.get_next_crawl_url()
        print(f"更新后的下一个URL: {next_url_after}")
        
        # 查看pages表数据
        pages = await client.execute_query("SELECT url, crawl_count, content FROM pages")
        print(f"Pages表数据: {pages}")


async def test_crawler_initialization():
    """测试爬虫初始化"""
    print("\n🧪 测试爬虫初始化")
    
    try:
        async with IndependentCrawler() as crawler:
            print("✅ 爬虫初始化成功")
            
            # 测试URL清洗
            test_urls = [
                "https://developer.apple.com/documentation/test#section",
                "https://developer.apple.com/documentation/test/",
                "https://developer.apple.com/documentation/test"
            ]
            
            for url in test_urls:
                clean_url = crawler.clean_and_normalize_url(url)
                print(f"原URL: {url} -> 清洗后: {clean_url}")
                
    except Exception as e:
        print(f"❌ 爬虫初始化失败: {e}")


async def test_link_storage():
    """测试链接存储逻辑"""
    print("\n🧪 测试链接存储逻辑")
    
    async with IndependentCrawler() as crawler:
        test_links = [
            "https://developer.apple.com/documentation/foundation",
            "https://developer.apple.com/documentation/uikit",
            "https://example.com/not-apple",  # 应该被过滤
            "https://developer.apple.com/documentation/foundation#overview"  # 应该被清洗
        ]
        
        await crawler._store_discovered_links(test_links)
        print("链接存储完成")
        
        # 查看存储的链接
        async with PostgreSQLClient() as client:
            pages = await client.execute_query("SELECT url, crawl_count FROM pages ORDER BY created_at")
            print("存储的页面:")
            for page in pages:
                print(f"  {page['url']} (crawl_count: {page['crawl_count']})")


async def main():
    """主测试函数"""
    print("🚀 开始测试新的爬取逻辑")
    print("=" * 50)
    
    try:
        await test_database_operations()
        await test_crawler_initialization()
        await test_link_storage()
        
        print("\n🎉 所有测试完成!")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
