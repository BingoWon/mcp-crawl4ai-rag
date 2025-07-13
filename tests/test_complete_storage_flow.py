#!/usr/bin/env python3
"""
测试完整的存储流程：pages表 + chunks表
"""

import asyncio
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler.core import IndependentCrawler
from database.client import PostgreSQLClient


async def test_complete_storage_flow():
    """测试完整的存储流程"""
    print("🧪 测试完整的存储流程...")
    
    test_url = "https://test-complete-flow.example.com/doc"
    test_markdown = """# Complete Flow Test
This is a test document for complete storage flow.

## Overview
This document tests the complete storage flow from page to chunks.

## Section 1
Content for section 1 with some details.

## Section 2
Content for section 2 with more information."""

    # 清理测试数据
    async with PostgreSQLClient() as client:
        await client.execute_query("DELETE FROM chunks WHERE url = $1", test_url)
        await client.execute_query("DELETE FROM pages WHERE url = $1", test_url)
        print("✅ 测试数据已清理")

    async with IndependentCrawler() as crawler:
        # 测试单页面处理
        result = await crawler._process_and_store_content(test_url, test_markdown)
        
        print(f"爬虫处理结果: {result}")
        assert result["success"], "爬虫处理应该成功"
        
        # 验证pages表中的数据
        async with PostgreSQLClient() as client:
            pages_data = await client.execute_query("""
                SELECT id, url, content, created_at, updated_at FROM pages 
                WHERE url = $1
            """, test_url)
            
            print(f"\n📋 pages表中的记录数: {len(pages_data)}")
            for page in pages_data:
                print(f"  页面: {page['url']}")
                print(f"    内容长度: {len(page['content'])} 字符")
                print(f"    创建时间: {page['created_at']}")
                print(f"    更新时间: {page['updated_at']}")
            
            assert len(pages_data) == 1, "应该有1个page记录"
            assert pages_data[0]['content'] == test_markdown, "页面内容应该正确"
            
            # 验证chunks表中的数据
            chunks_data = await client.execute_query("""
                SELECT id, url, content, embedding FROM chunks 
                WHERE url = $1
                ORDER BY created_at
            """, test_url)
            
            print(f"\n📋 chunks表中的记录数: {len(chunks_data)}")
            for i, chunk in enumerate(chunks_data):
                print(f"  Chunk {i}: {chunk['url']}")
                print(f"    内容长度: {len(chunk['content'])} 字符")
                print(f"    有embedding: {'是' if chunk['embedding'] else '否'}")
            
            assert len(chunks_data) >= 1, "应该至少有1个chunk记录"
            assert all(chunk['embedding'] for chunk in chunks_data), "所有chunk都应该有embedding"
    
    print("✅ 完整存储流程测试通过\n")


async def test_page_update_flow():
    """测试页面更新流程"""
    print("🧪 测试页面更新流程...")
    
    test_url = "https://test-update-flow.example.com/doc"
    original_content = """# Original Content
This is the original content."""
    
    updated_content = """# Updated Content
This is the updated content with more information."""

    async with IndependentCrawler() as crawler:
        # 第一次存储
        await crawler._process_and_store_content(test_url, original_content)
        
        # 第二次存储（更新）
        await crawler._process_and_store_content(test_url, updated_content)
        
        # 验证pages表中只有一条记录，但内容已更新
        async with PostgreSQLClient() as client:
            pages_data = await client.execute_query("""
                SELECT id, url, content, created_at, updated_at FROM pages 
                WHERE url = $1
            """, test_url)
            
            print(f"pages表中的记录数: {len(pages_data)}")
            assert len(pages_data) == 1, "应该只有1个page记录（去重）"
            assert pages_data[0]['content'] == updated_content, "内容应该已更新"
            assert pages_data[0]['updated_at'] > pages_data[0]['created_at'], "更新时间应该大于创建时间"
            
            print(f"  页面: {pages_data[0]['url']}")
            print(f"    内容: 已更新为新内容")
            print(f"    创建时间: {pages_data[0]['created_at']}")
            print(f"    更新时间: {pages_data[0]['updated_at']}")
    
    print("✅ 页面更新流程测试通过\n")


async def test_batch_storage_flow():
    """测试批量存储流程"""
    print("🧪 测试批量存储流程...")
    
    # 模拟批量爬取结果
    crawl_results = [
        {
            'url': 'https://test-batch.example.com/page1',
            'markdown': '# Page 1\n## Overview\nContent for page 1.\n## Section 1\nMore content.'
        },
        {
            'url': 'https://test-batch.example.com/page2',
            'markdown': '# Page 2\n## Overview\nContent for page 2.\n## Section 1\nMore content.'
        }
    ]

    # 清理测试数据
    async with PostgreSQLClient() as client:
        for result in crawl_results:
            await client.execute_query("DELETE FROM chunks WHERE url = $1", result['url'])
            await client.execute_query("DELETE FROM pages WHERE url = $1", result['url'])

    async with IndependentCrawler() as crawler:
        # 测试批量处理
        result = await crawler._process_and_store_batch(crawl_results, "test_batch")
        
        print(f"批量处理结果: {result}")
        assert result["success"], "批量处理应该成功"
        
        # 验证pages表
        async with PostgreSQLClient() as client:
            pages_data = await client.execute_query("""
                SELECT url, content FROM pages 
                WHERE url LIKE 'https://test-batch.example.com/%'
                ORDER BY url
            """)
            
            print(f"\npages表中的记录数: {len(pages_data)}")
            assert len(pages_data) == 2, "应该有2个page记录"
            
            # 验证chunks表
            chunks_data = await client.execute_query("""
                SELECT url, content FROM chunks 
                WHERE url LIKE 'https://test-batch.example.com/%'
                ORDER BY url
            """)
            
            print(f"chunks表中的记录数: {len(chunks_data)}")
            assert len(chunks_data) >= 2, "应该至少有2个chunk记录"
    
    print("✅ 批量存储流程测试通过\n")


async def main():
    """运行所有完整存储流程测试"""
    print("🚀 开始完整存储流程测试")
    print("=" * 50)
    
    try:
        await test_complete_storage_flow()
        await test_page_update_flow()
        await test_batch_storage_flow()
        
        print("🎉 所有完整存储流程测试通过！")
        print("✅ pages表和chunks表的完整存储机制工作正常")
        
    except Exception as e:
        print(f"❌ 完整存储流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
