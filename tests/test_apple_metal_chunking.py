#!/usr/bin/env python3
"""
测试指定 Apple Metal 文档的 chunking 效果
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler.core import IndependentCrawler
from chunking import SmartChunker


async def test_apple_metal_chunking():
    """测试 Apple Metal 文档的 chunking"""
    url = "https://developer.apple.com/documentation/xcode/preparing-dates-numbers-with-formatters"
    
    print(f"🚀 开始测试 Apple Metal 文档 chunking")
    print(f"URL: {url}")
    print("=" * 80)
    
    try:
        # 初始化组件
        print("📦 初始化组件...")
        crawler = IndependentCrawler()
        chunker = SmartChunker()
        
        # 爬取页面
        print("🕷️ 爬取页面内容...")
        async with crawler:
            crawl_results = await crawler.crawl_apple_documentation(url)

        if not crawl_results:
            print("❌ 爬取失败或内容为空")
            return False

        # 获取第一个结果的内容
        crawl_result = crawl_results[0]
        print(f"🔍 调试：crawl_result keys: {list(crawl_result.keys())}")

        # 尝试不同的键名
        clean_content = (crawl_result.get('content', '') or
                        crawl_result.get('clean_content', '') or
                        crawl_result.get('text', '') or
                        crawl_result.get('markdown', ''))

        if not clean_content:
            print("❌ 爬取内容为空")
            print(f"🔍 调试：crawl_result 内容: {crawl_result}")
            return False

        print(f"✅ 爬取成功，内容长度: {len(clean_content)} 字符")
        
        print(f"✅ 内容获取完成，内容长度: {len(clean_content)} 字符")
        
        # 执行 chunking
        print("✂️ 执行 chunking...")
        chunks = chunker.chunk_text(clean_content)
        
        print(f"✅ Chunking 完成，生成 {len(chunks)} 个 chunks")
        
        # 分析结果
        print("\n📊 Chunking 结果分析:")
        print(f"总 chunks 数量: {len(chunks)}")
        
        total_chars = sum(len(chunk) for chunk in chunks)
        avg_chars = total_chars / len(chunks) if chunks else 0
        
        print(f"总字符数: {total_chars}")
        print(f"平均每个 chunk: {avg_chars:.0f} 字符")
        
        # 保存结果到文件
        output_file = Path(__file__).parent / "apple_metal_chunking_result.txt"
        
        print(f"\n💾 保存结果到: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Apple Metal 文档 Chunking 测试结果\n")
            f.write(f"URL: {url}\n")
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"内容长度: {len(clean_content)} 字符\n")
            f.write(f"生成 chunks 数量: {len(chunks)}\n")
            f.write(f"总字符数: {total_chars}\n")
            f.write(f"平均每个 chunk: {avg_chars:.0f} 字符\n")
            f.write("\n" + "=" * 80 + "\n")
            f.write("完整内容:\n")
            f.write("=" * 80 + "\n")
            f.write(clean_content)
            f.write("\n\n" + "=" * 80 + "\n")
            f.write("Chunking 结果:\n")
            f.write("=" * 80 + "\n\n")
            
            for i, chunk in enumerate(chunks, 1):
                f.write(f"=== Chunk {i} ===\n")
                f.write(f"长度: {len(chunk)} 字符\n")
                f.write(f"内容:\n{chunk}\n\n")
                f.write("-" * 40 + "\n\n")
        
        print(f"✅ 结果已保存到: {output_file}")
        
        # 显示每个 chunk 的简要信息
        print(f"\n📋 各 Chunk 详情:")
        for i, chunk in enumerate(chunks, 1):
            lines = chunk.split('\n')
            first_line = next((line.strip() for line in lines if line.strip()), "")
            print(f"  Chunk {i}: {len(chunk)} 字符 - {first_line[:60]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    success = await test_apple_metal_chunking()
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
