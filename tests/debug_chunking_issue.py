#!/usr/bin/env python3
"""
调试"No content to store after chunking"问题
分析Apple内容提取器输出的内容格式
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler.apple_content_extractor import AppleContentExtractor
from chunking import SmartChunker
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def debug_chunking_issue():
    """调试分块问题"""
    print("🔍 调试分块问题...")
    
    # 测试URL
    test_urls = [
        "https://developer.apple.com/documentation/samplecode",
        "https://developer.apple.com/documentation/swiftui",
        "https://developer.apple.com/documentation/accounts/acaccountstore"
    ]
    
    chunker = SmartChunker()
    
    for url in test_urls:
        print(f"\n{'='*80}")
        print(f"测试URL: {url}")
        print('='*80)
        
        try:
            # 使用Apple内容提取器获取内容
            async with AppleContentExtractor() as extractor:
                clean_content = await extractor.extract_clean_content(url)
            
            print(f"📄 提取的内容长度: {len(clean_content) if clean_content else 0} 字符")
            
            if not clean_content:
                print("❌ 内容提取失败，clean_content为空")
                continue
            
            # 显示内容的前500字符
            print(f"📝 内容预览 (前500字符):")
            print("-" * 50)
            print(clean_content[:500])
            print("-" * 50)
            
            # 分析内容结构
            lines = clean_content.split('\n')
            print(f"📊 内容分析:")
            print(f"  总行数: {len(lines)}")
            
            # 查找标题结构
            h1_lines = [line for line in lines if line.startswith('# ')]
            h2_lines = [line for line in lines if line.startswith('## ')]
            overview_lines = [line for line in lines if line.strip() == '## Overview']
            
            print(f"  # 标题: {len(h1_lines)} 个")
            for h1 in h1_lines[:3]:  # 只显示前3个
                print(f"    - {h1}")
            
            print(f"  ## 标题: {len(h2_lines)} 个")
            for h2 in h2_lines[:5]:  # 只显示前5个
                print(f"    - {h2}")
            
            print(f"  ## Overview: {len(overview_lines)} 个")
            for overview in overview_lines:
                print(f"    - {overview}")
            
            # 尝试分块
            print(f"\n🔧 尝试分块...")
            chunks = chunker.chunk_text_simple(clean_content)
            
            print(f"📦 分块结果: {len(chunks)} 个chunks")
            
            if not chunks:
                print("❌ 分块失败！分析原因:")
                
                # 详细分析为什么分块失败
                print("\n🔍 详细分析:")
                
                # 检查_extract_first_part
                first_part = chunker._extract_first_part(clean_content)
                print(f"  第一部分长度: {len(first_part)} 字符")
                if first_part:
                    print(f"  第一部分预览: {first_part[:200]}...")
                else:
                    print("  ❌ 第一部分为空")
                
                # 检查_split_sections_after_overview
                sections = chunker._split_sections_after_overview(clean_content)
                print(f"  章节数量: {len(sections)}")
                for i, section in enumerate(sections[:3]):  # 只显示前3个
                    print(f"    章节 {i+1}: {len(section)} 字符")
                    print(f"      开头: {section[:100]}...")
                
                # 分析为什么没有找到Overview
                if not overview_lines:
                    print("\n❌ 未找到'## Overview'章节")
                    print("   可能的原因:")
                    print("   1. 内容格式不符合预期")
                    print("   2. Overview章节名称不同")
                    print("   3. 内容被过度清理")
                    
                    # 查找可能的Overview变体
                    possible_overview = [line for line in lines if 'overview' in line.lower()]
                    if possible_overview:
                        print(f"   发现可能的Overview变体:")
                        for variant in possible_overview[:3]:
                            print(f"     - {variant}")
            else:
                print("✅ 分块成功！")
                for i, chunk in enumerate(chunks[:2]):  # 只显示前2个
                    print(f"  Chunk {i+1}: {len(chunk)} 字符")
                    print(f"    开头: {chunk[:100]}...")
        
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()


async def test_chunker_with_sample_content():
    """使用示例内容测试分块器"""
    print(f"\n{'='*80}")
    print("🧪 使用示例内容测试分块器")
    print('='*80)
    
    # 创建符合预期格式的示例内容
    sample_content = """# Sample Documentation
This is a sample documentation page.

## Overview
This is the overview section that explains what this documentation is about.

## Getting Started
This section explains how to get started.

## Advanced Topics
This section covers advanced topics.

## Troubleshooting
This section helps with troubleshooting."""
    
    chunker = SmartChunker()
    chunks = chunker.chunk_text_simple(sample_content)
    
    print(f"📦 示例内容分块结果: {len(chunks)} 个chunks")
    
    if chunks:
        print("✅ 示例内容分块成功！")
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i+1}: {len(chunk)} 字符")
            print(f"    内容: {chunk}")
            print()
    else:
        print("❌ 示例内容分块失败！")


async def main():
    """主函数"""
    print("🚀 开始调试分块问题")
    
    await test_chunker_with_sample_content()
    await debug_chunking_issue()
    
    print("\n🎉 调试完成！")


if __name__ == "__main__":
    asyncio.run(main())
