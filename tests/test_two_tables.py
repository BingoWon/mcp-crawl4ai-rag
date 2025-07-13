#!/usr/bin/env python3
"""
测试正确的两表架构功能
"""

import asyncio
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler.core import IndependentCrawler
from database.client import PostgreSQLClient


async def test_two_tables_structure():
    """测试两表结构"""
    print("🧪 测试两表结构...")
    
    async with PostgreSQLClient() as client:
        # 检查表是否存在
        tables = await client.execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        table_names = [t['table_name'] for t in tables]
        print(f"数据库中的表: {table_names}")
        
        assert 'chunks' in table_names, "应该有chunks表"
        assert 'pages' in table_names, "应该有pages表"
        assert len(table_names) == 2, f"应该只有2个表，实际有{len(table_names)}个"
        
        # 检查chunks表结构
        chunks_columns = await client.execute_query("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'chunks' AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        chunks_fields = [c['column_name'] for c in chunks_columns]
        print(f"chunks表字段: {chunks_fields}")
        
        assert 'embedding' in chunks_fields, "chunks表应该有embedding字段"
        
        # 检查pages表结构
        pages_columns = await client.execute_query("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'pages' AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        pages_fields = [c['column_name'] for c in pages_columns]
        print(f"pages表字段: {pages_fields}")

        expected_pages_fields = ['id', 'url', 'content', 'created_at', 'updated_at']
        assert 'embedding' not in pages_fields, "pages表不应该有embedding字段"
        assert 'title' not in pages_fields, "pages表不应该有title字段"
        assert 'total_chunks' not in pages_fields, "pages表不应该有total_chunks字段"
        assert all(field in pages_fields for field in expected_pages_fields), f"pages表应该包含{expected_pages_fields}"
    
    print("✅ 两表结构测试通过\n")


async def test_chunks_functionality():
    """测试chunks表功能"""
    print("🧪 测试chunks表功能...")
    
    # 模拟markdown内容
    test_markdown = """# Test Document
This is a test document.

## Overview
This is the overview section.

## Section 1
Content for section 1."""

    async with IndependentCrawler() as crawler:
        # 清理测试数据
        async with PostgreSQLClient() as client:
            await client.execute_query("DELETE FROM chunks WHERE url = 'https://test-two-tables.example.com/doc'")
        
        # 测试爬虫功能
        result = await crawler._process_and_store_content(
            "https://test-two-tables.example.com/doc", 
            test_markdown
        )
        
        print(f"爬虫处理结果: {result}")
        assert result["success"], "爬虫处理应该成功"
        
        # 验证chunks表中的数据
        async with PostgreSQLClient() as client:
            chunks_data = await client.execute_query("""
                SELECT id, url, content, embedding FROM chunks 
                WHERE url = 'https://test-two-tables.example.com/doc'
                ORDER BY created_at
            """)
            
            print(f"chunks表中的记录数: {len(chunks_data)}")
            for i, chunk in enumerate(chunks_data):
                print(f"  Chunk {i}: {chunk['url']}")
                print(f"    内容长度: {len(chunk['content'])} 字符")
                print(f"    有embedding: {'是' if chunk['embedding'] else '否'}")
            
            assert len(chunks_data) >= 1, "应该至少有1个chunk记录"
            assert all(chunk['embedding'] for chunk in chunks_data), "所有chunk都应该有embedding"
    
    print("✅ chunks表功能测试通过\n")


async def test_pages_functionality():
    """测试pages表功能"""
    print("🧪 测试pages表功能...")
    
    async with PostgreSQLClient() as client:
        # 清理测试数据
        await client.execute_query("DELETE FROM pages WHERE url = 'https://test-two-tables.example.com/page'")
        
        # 插入测试页面数据
        await client.execute_query("""
            INSERT INTO pages (url, content)
            VALUES ($1, $2)
        """, 'https://test-two-tables.example.com/page', 'Test page content')

        # 查询页面数据
        pages_data = await client.execute_query("""
            SELECT id, url, content FROM pages
            WHERE url = 'https://test-two-tables.example.com/page'
        """)

        print(f"pages表中的记录数: {len(pages_data)}")
        for page in pages_data:
            print(f"  页面: {page['url']}")
            print(f"    内容: {page['content']}")

        assert len(pages_data) == 1, "应该有1个page记录"
        assert pages_data[0]['content'] == 'Test page content', "内容应该正确"
    
    print("✅ pages表功能测试通过\n")


async def main():
    """运行所有两表架构测试"""
    print("🚀 开始两表架构测试")
    print("=" * 50)
    
    try:
        await test_two_tables_structure()
        await test_chunks_functionality()
        await test_pages_functionality()
        
        print("🎉 所有两表架构测试通过！")
        print("✅ chunks表（包含embedding）和pages表（不含embedding）功能正常")
        
    except Exception as e:
        print(f"❌ 两表架构测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
