#!/usr/bin/env python3
"""
临时脚本：查询特定URL在数据库中的数据
查询pages和chunks表中的内容并输出到txt文件
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.client import PostgreSQLClient


async def query_page_content(client: PostgreSQLClient, url: str):
    """查询pages表中的内容"""
    result = await client.fetch_one("""
        SELECT url, content, crawl_count, created_at, last_crawled_at
        FROM pages
        WHERE url = $1
    """, url)
    return result


async def query_chunks_content(client: PostgreSQLClient, url: str):
    """查询chunks表中的内容"""
    results = await client.fetch_all("""
        SELECT id, url, content, created_at
        FROM chunks
        WHERE url = $1
        ORDER BY created_at ASC
    """, url)
    return results


def save_to_file(url: str, page_data: dict, chunks_data: list):
    """保存查询结果到txt文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"url_data_query_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=== URL数据查询结果 ===\n")
        f.write(f"URL: {url}\n")
        f.write(f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Pages表数据
        f.write("=== PAGES表数据 ===\n")
        if page_data:
            content_length = len(page_data['content']) if page_data['content'] else 0
            f.write(f"内容长度: {content_length} 字符\n")
            f.write(f"爬取次数: {page_data['crawl_count']}\n")
            f.write(f"创建时间: {page_data['created_at']}\n")
            f.write(f"更新时间: {page_data['updated_at']}\n\n")
            
            f.write("内容:\n")
            f.write("-" * 50 + "\n")
            f.write(page_data['content'] or "无内容")
            f.write("\n" + "-" * 50 + "\n\n")
        else:
            f.write("未找到页面数据\n\n")
        
        # Chunks表数据
        f.write("=== CHUNKS表数据 ===\n")
        if chunks_data:
            total_chunks = len(chunks_data)
            avg_length = sum(len(chunk['content']) for chunk in chunks_data) / total_chunks
            f.write(f"总块数: {total_chunks}\n")
            f.write(f"平均长度: {avg_length:.0f} 字符\n\n")
            
            for i, chunk in enumerate(chunks_data, 1):
                f.write(f"块 {i}:\n")
                f.write(f"ID: {chunk['id']}\n")
                f.write(f"长度: {len(chunk['content'])} 字符\n")
                f.write(f"创建时间: {chunk['created_at']}\n")
                f.write("内容:\n")
                f.write("-" * 30 + "\n")
                f.write(chunk['content'])
                f.write("\n" + "-" * 30 + "\n\n")
        else:
            f.write("未找到块数据\n\n")
    
    print(f"查询结果已保存到: {filename}")
    return filename


async def main():
    """主函数"""
    url = "https://developer.apple.com/documentation/swiftui/applying-liquid-glass-to-custom-views"
    
    print(f"正在查询URL: {url}")
    
    try:
        async with PostgreSQLClient() as client:
            # 查询pages表
            print("查询pages表...")
            page_data = await query_page_content(client, url)
            
            # 查询chunks表
            print("查询chunks表...")
            chunks_data = await query_chunks_content(client, url)
            
            # 输出到文件
            print("保存结果到文件...")
            filename = save_to_file(url, page_data, chunks_data)
            
            # 输出摘要
            print("\n=== 查询摘要 ===")
            if page_data:
                content_length = len(page_data['content']) if page_data['content'] else 0
                print(f"Pages表: 找到数据，内容长度 {content_length} 字符")
            else:
                print("Pages表: 未找到数据")
            
            if chunks_data:
                print(f"Chunks表: 找到 {len(chunks_data)} 个块")
            else:
                print("Chunks表: 未找到数据")
                
    except Exception as e:
        print(f"查询失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
