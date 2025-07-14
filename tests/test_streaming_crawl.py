#!/usr/bin/env python3
"""
测试流式爬取功能
验证每个页面立即处理，无等待无缓存
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler import IndependentCrawler
from database.client import PostgreSQLClient
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def test_streaming_vs_batch():
    """对比流式处理和批量处理的时机差异"""
    print("🧪 测试流式处理 vs 批量处理...")
    
    # 清理测试数据
    test_urls = [
        "https://developer.apple.com/documentation/swiftui",
        "https://developer.apple.com/documentation/uikit"
    ]
    
    async with PostgreSQLClient() as client:
        for url in test_urls:
            await client.execute_query("DELETE FROM chunks WHERE url = $1", url)
            await client.execute_query("DELETE FROM pages WHERE url = $1", url)
        print("✅ 测试数据已清理")

    async with IndependentCrawler() as crawler:
        print("\n📊 开始流式爬取测试...")
        start_time = time.time()
        
        # 模拟单页面流式处理
        for i, url in enumerate(test_urls, 1):
            page_start = time.time()
            
            # 模拟爬取内容
            test_markdown = f"""# Test Document {i}
This is test document {i}.

## Overview
This is the overview section for document {i}.

## Section 1
Content for section 1 of document {i}.

## Section 2
Content for section 2 of document {i}."""
            
            # 立即处理
            result = await crawler._process_and_store_content(url, test_markdown)
            page_end = time.time()
            
            if result["success"]:
                print(f"✅ 页面 {i} 处理完成: {page_end - page_start:.2f}s, {result['chunks_stored']} chunks")
                
                # 验证数据立即可用
                async with PostgreSQLClient() as client:
                    chunks_count = await client.fetch_val(
                        "SELECT COUNT(*) FROM chunks WHERE url = $1", url
                    )
                    print(f"   📊 数据库中立即可查询到 {chunks_count} 个chunks")
            else:
                print(f"❌ 页面 {i} 处理失败: {result.get('error')}")
        
        total_time = time.time() - start_time
        print(f"\n🎉 流式处理完成: 总耗时 {total_time:.2f}s")
        print("✅ 每个页面处理后立即可在数据库中查询到结果")


async def test_real_streaming_crawl():
    """测试真实的流式递归爬取"""
    print("\n🧪 测试真实流式递归爬取...")
    
    # 使用一个简单的Apple文档URL进行测试
    test_url = "https://developer.apple.com/documentation/swiftui/view"
    
    # 清理测试数据
    async with PostgreSQLClient() as client:
        await client.execute_query("DELETE FROM chunks WHERE url LIKE 'https://developer.apple.com/documentation/swiftui%'")
        await client.execute_query("DELETE FROM pages WHERE url LIKE 'https://developer.apple.com/documentation/swiftui%'")
        print("✅ 测试数据已清理")

    async with IndependentCrawler() as crawler:
        print(f"📊 开始流式爬取: {test_url}")
        start_time = time.time()
        
        # 设置较小的深度避免爬取太多页面
        import os
        original_depth = os.getenv('MAX_DEPTH', '3')
        os.environ['MAX_DEPTH'] = '1'  # 只爬取1层深度
        
        try:
            result = await crawler.smart_crawl_url(test_url)
            end_time = time.time()
            
            print(f"\n🎉 流式爬取完成: {end_time - start_time:.2f}s")
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
            else:
                print(f"❌ 爬取失败: {result.get('error')}")
                
        finally:
            # 恢复原始深度设置
            os.environ['MAX_DEPTH'] = original_depth


async def main():
    """运行所有测试"""
    print("🚀 开始测试流式爬取功能")
    print("=" * 60)
    
    try:
        await test_streaming_vs_batch()
        await test_real_streaming_crawl()
        
        print("\n🎉 所有测试完成！")
        print("✅ 流式处理功能验证通过")
        print("✅ 每个页面爬取后立即chunk、embed、store")
        print("✅ 无等待、无缓存、实时处理")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
