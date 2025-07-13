#!/usr/bin/env python3
"""
测试修复后的爬虫集成功能
"""

import asyncio
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler.core import IndependentCrawler
from database.client import PostgreSQLClient


async def test_single_page_chunking():
    """测试单页面分块存储"""
    print("🧪 测试单页面分块存储...")
    
    # 模拟markdown内容
    test_markdown = """# Apple Documentation Test
This is the main title content.

## Overview
This is the overview section with important information.

## First Section
This is the first section with detailed content about the topic.

## Second Section
This is the second section with more specific information."""

    async with IndependentCrawler() as crawler:
        # 直接调用内部方法测试
        result = await crawler._process_and_store_content(
            "https://test.example.com/doc", 
            test_markdown
        )
        
        print(f"处理结果: {result}")
        assert result["success"], "单页面处理应该成功"
        assert result["chunks_stored"] == 2, "应该存储2个chunks"
        
        # 验证数据库中的数据
        async with PostgreSQLClient() as client:
            
            # 查询存储的chunks
            stored_data = await client.execute_query("""
                SELECT id, url, content FROM crawled_pages
                WHERE url = 'https://test.example.com/doc'
                ORDER BY created_at
            """)
            
            print(f"存储的chunks数量: {len(stored_data)}")
            for i, data in enumerate(stored_data):
                print(f"  Chunk {i}: {data['url']}")
                print(f"    UUID: {data['id']}")
                print(f"    内容长度: {len(data['content'])} 字符")
                print(f"    内容预览: {data['content'][:50]}...")

            assert len(stored_data) == 2, "数据库中应该有2个chunk记录"
            assert all(data['url'] == 'https://test.example.com/doc' for data in stored_data), "所有记录应该使用原始URL"
            assert all(data['id'] for data in stored_data), "所有记录应该有UUID"
    
    print("✅ 单页面分块存储测试通过\n")


async def test_batch_processing():
    """测试批量处理功能"""
    print("🧪 测试批量处理功能...")
    
    # 模拟批量爬取结果
    crawl_results = [
        {
            "url": "https://test.example.com/page1",
            "markdown": """# Page 1 Title
Content for page 1.

## Overview
Overview for page 1.

## Section A
Section A content."""
        },
        {
            "url": "https://test.example.com/page2", 
            "markdown": """# Page 2 Title
Content for page 2.

## Overview
Overview for page 2.

## Section B
Section B content.

## Section C
Section C content."""
        }
    ]
    
    async with IndependentCrawler() as crawler:
        # 测试批量处理
        result = await crawler._process_and_store_batch(crawl_results, "test_batch")
        
        print(f"批量处理结果: {result}")
        assert result["success"], "批量处理应该成功"
        assert result["total_pages"] == 2, "应该处理2个页面"
        assert result["total_chunks"] == 3, "应该生成3个chunks (page1: 1个, page2: 2个)"
        
        # 验证数据库中的数据
        async with PostgreSQLClient() as client:
            stored_data = await client.execute_query("""
                SELECT id, url, content FROM crawled_pages
                WHERE url LIKE 'https://test.example.com/page%'
                ORDER BY url, created_at
            """)
            
            print(f"批量存储的chunks数量: {len(stored_data)}")
            page1_chunks = [d for d in stored_data if 'page1' in d['url']]
            page2_chunks = [d for d in stored_data if 'page2' in d['url']]

            print(f"  Page1 chunks: {len(page1_chunks)}")
            print(f"  Page2 chunks: {len(page2_chunks)}")

            assert len(page1_chunks) == 1, "Page1应该有1个chunk"
            assert len(page2_chunks) == 2, "Page2应该有2个chunks"

            # 验证使用原始URL和UUID
            for data in stored_data:
                assert '#chunk' not in data['url'], f"URL不应该包含#chunk: {data['url']}"
                assert data['id'], f"记录应该有UUID: {data}"
    
    print("✅ 批量处理功能测试通过\n")


async def test_embedding_generation():
    """测试embedding生成"""
    print("🧪 测试embedding生成...")
    
    async with PostgreSQLClient() as client:
        # 查询所有存储的数据
        stored_data = await client.execute_query("""
            SELECT id, url, embedding FROM crawled_pages
            WHERE url LIKE 'https://test.example.com/%'
            AND embedding IS NOT NULL
        """)
        
        print(f"有embedding的记录数量: {len(stored_data)}")
        
        for data in stored_data:
            # 验证embedding不为空且维度正确
            embedding_str = data['embedding']
            assert embedding_str, "Embedding不应该为空"
            
            # 解析embedding字符串为列表
            import ast
            embedding = ast.literal_eval(embedding_str)
            assert len(embedding) == 2560, f"Embedding维度应该是2560，实际是{len(embedding)}"
            
            print(f"  {data['url']} (UUID: {str(data['id'])[:8]}...): embedding维度 {len(embedding)}")

            # 验证使用原始URL和UUID
            assert '#chunk' not in data['url'], f"URL不应该包含#chunk: {data['url']}"
            assert data['id'], f"记录应该有UUID: {data}"
    
    print("✅ Embedding生成测试通过\n")


async def main():
    """运行所有集成测试"""
    print("🚀 开始爬虫集成测试")
    print("=" * 50)
    
    try:
        await test_single_page_chunking()
        await test_batch_processing() 
        await test_embedding_generation()
        
        print("🎉 所有集成测试通过！")
        print("✅ 修复后的爬虫功能工作正常")
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
