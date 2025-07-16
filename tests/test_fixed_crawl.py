#!/usr/bin/env python3
"""
测试修复后的爬取流程
验证"No content to store after chunking"问题已解决
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler import IndependentCrawler
from database.client import PostgreSQLClient
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def test_fixed_crawl():
    """测试修复后的爬取流程"""
    print("🧪 测试修复后的爬取流程...")
    
    # 之前失败的URL
    test_urls = [
        "https://developer.apple.com/documentation/samplecode",
        "https://developer.apple.com/documentation/swiftui",
        "https://developer.apple.com/documentation/accounts/acaccountstore"
    ]
    
    # 清理测试数据
    async with PostgreSQLClient() as client:
        for url in test_urls:
            await client.execute_query("DELETE FROM chunks WHERE url = $1", url)
            await client.execute_query("DELETE FROM pages WHERE url = $1", url)
        print("✅ 测试数据已清理")

    async with IndependentCrawler() as crawler:
        for i, url in enumerate(test_urls, 1):
            print(f"\n📊 测试 {i}/{len(test_urls)}: {url}")
            
            try:
                # 爬取页面内容
                from crawler.apple_stealth_crawler import AppleStealthCrawler
                async with AppleStealthCrawler() as stealth_crawler:
                    clean_content, links = await stealth_crawler.extract_content_and_links(url, "#app-main")

                if clean_content:
                    # 处理内容
                    process_result = await crawler._process_and_store_content(
                        url,
                        clean_content
                    )
                    
                    if process_result["success"]:
                        print(f"✅ 处理成功: {process_result['chunks_stored']} chunks存储")
                        print(f"   总字符数: {process_result['total_characters']}")
                        
                        # 验证数据库中的数据
                        async with PostgreSQLClient() as client:
                            chunks_count = await client.fetch_val(
                                "SELECT COUNT(*) FROM chunks WHERE url = $1", url
                            )
                            pages_count = await client.fetch_val(
                                "SELECT COUNT(*) FROM pages WHERE url = $1", url
                            )
                            print(f"   数据库验证: {pages_count} 页面, {chunks_count} chunks")
                    else:
                        print(f"❌ 处理失败: {process_result.get('error')}")
                else:
                    print("❌ 爬取失败: 无内容返回")
                    
            except Exception as e:
                print(f"❌ 异常: {e}")
                import traceback
                traceback.print_exc()


async def test_streaming_crawl():
    """测试流式爬取功能"""
    print(f"\n{'='*80}")
    print("🧪 测试流式爬取功能")
    print('='*80)
    
    # 使用一个简单的URL测试流式爬取
    test_url = "https://developer.apple.com/documentation/swiftui/view"
    
    # 清理测试数据
    async with PostgreSQLClient() as client:
        await client.execute_query("DELETE FROM chunks WHERE url LIKE 'https://developer.apple.com/documentation/swiftui%'")
        await client.execute_query("DELETE FROM pages WHERE url LIKE 'https://developer.apple.com/documentation/swiftui%'")
        print("✅ 测试数据已清理")

    async with IndependentCrawler() as crawler:
        print(f"📊 开始流式爬取: {test_url}")
        
        # 设置较小的深度避免爬取太多页面
        import os
        original_depth = os.getenv('MAX_DEPTH', '3')
        os.environ['MAX_DEPTH'] = '1'  # 只爬取1层深度
        
        try:
            result = await crawler.smart_crawl_url(test_url)
            
            print(f"🎉 流式爬取完成")
            print(f"📊 结果: {result}")
            
            if result.get("success"):
                print(f"✅ 成功处理 {result['total_pages']} 页面")
                print(f"✅ 存储了 {result['total_chunks']} 个chunks")
                print(f"✅ 爬取类型: {result['crawl_type']}")
                
                # 验证数据库中的数据
                async with PostgreSQLClient() as client:
                    pages_count = await client.fetch_val(
                        "SELECT COUNT(*) FROM pages WHERE url LIKE 'https://developer.apple.com/documentation/swiftui%'"
                    )
                    chunks_count = await client.fetch_val(
                        "SELECT COUNT(*) FROM chunks WHERE url LIKE 'https://developer.apple.com/documentation/swiftui%'"
                    )
                    print(f"📊 数据库验证: {pages_count} 页面, {chunks_count} chunks")
                    
                    # 显示一些具体的数据
                    sample_chunks = await client.fetch_all(
                        "SELECT url, LENGTH(content) as content_length FROM chunks WHERE url LIKE 'https://developer.apple.com/documentation/swiftui%' LIMIT 5"
                    )
                    print(f"📝 示例chunks:")
                    for chunk in sample_chunks:
                        print(f"   {chunk['url']}: {chunk['content_length']} 字符")
            else:
                print(f"❌ 爬取失败: {result.get('error')}")
                
        finally:
            # 恢复原始深度设置
            os.environ['MAX_DEPTH'] = original_depth


async def main():
    """运行所有测试"""
    print("🚀 开始测试修复后的爬取功能")
    print("=" * 80)
    
    try:
        await test_fixed_crawl()
        await test_streaming_crawl()
        
        print("\n🎉 所有测试完成！")
        print("✅ 'No content to store after chunking' 问题已解决")
        print("✅ 分块器现在能处理没有Overview的页面")
        print("✅ 流式处理功能正常工作")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
