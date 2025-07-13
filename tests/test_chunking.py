"""
Test Chunking Module
测试分块模块

Tests for the independent chunking functionality.
独立分块功能的测试。
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chunking import SmartChunker, BreakPointType


def test_basic_chunking():
    """测试Apple文档双井号分块功能"""
    print("🧪 测试Apple文档双井号分块功能...")

    chunker = SmartChunker()
    text = """# Playing immersive media with RealityKit
Create an immersive video playback experience with RealityKit.

## Overview
This sample shows how to build an immersive video playback experience for visionOS.

## Choose a playback approach
When it comes to providing immersive video playback on visionOS, there are a few different approaches.

## Configure video player
VideoPlayerComponent relies on three pairs of properties to play immersive media."""

    chunks = chunker.chunk_text_simple(text)
    print(f"分块结果: {len(chunks)} 个块")
    for i, chunk in enumerate(chunks):
        print(f"  块 {i+1}: {len(chunk)} 字符")
        print(f"    开头: {chunk[:50]}...")

    assert len(chunks) == 2, "应该生成2个块（Choose a playback approach + Configure video player）"
    print("✅ Apple文档分块测试通过\n")


def test_detailed_chunking():
    """测试详细分块信息"""
    print("🧪 测试详细分块信息...")

    chunker = SmartChunker()
    text = """# Apple Documentation
Main title content.

## Overview
Overview content here.

## First Section
First section content.

## Second Section
Second section content."""

    chunk_infos = chunker.chunk_text(text)
    print(f"详细分块结果: {len(chunk_infos)} 个块")

    for chunk_info in chunk_infos:
        print(f"  块 {chunk_info.chunk_index + 1}:")
        print(f"    长度: {len(chunk_info.content)} 字符")
        print(f"    分割类型: {chunk_info.break_type.value}")
        print(f"    内容预览: {chunk_info.content}...")

    assert len(chunk_infos) == 2, "应该生成2个块"
    assert all(chunk.break_type == BreakPointType.MARKDOWN_HEADER for chunk in chunk_infos), "所有块都应该是双井号分割"
    print("✅ 详细分块测试通过\n")


def test_double_hash_splitting():
    """测试双井号分割逻辑"""
    print("🧪 测试双井号分割逻辑...")

    chunker = SmartChunker()

    # 测试忽略三井号
    text_with_triple = """# Main Title
Content here.

## Overview
Overview content.

## Section One
Content one.

### Subsection (should be ignored)
Subsection content.

## Section Two
Content two."""

    chunks = chunker.chunk_text(text_with_triple)
    print(f"包含三井号的文本分块: {len(chunks)} 个块")

    # 应该只在##处分割，忽略###
    assert len(chunks) == 2, "应该只有2个块（Section One + Section Two）"

    # 检查第一个块是否包含三井号内容
    first_chunk = chunks[0].content
    assert "### Subsection" in first_chunk, "第一个块应该包含三井号内容"

    print("✅ 双井号分割测试通过\n")


def test_break_point_type():
    """测试分割点类型"""
    print("🧪 测试分割点类型...")

    # 测试BreakPointType枚举
    assert BreakPointType.MARKDOWN_HEADER.value == "markdown_header"
    print(f"分割类型: {BreakPointType.MARKDOWN_HEADER.value}")

    print("✅ 分割点类型测试通过\n")


def test_edge_cases():
    """测试边界情况"""
    print("🧪 测试边界情况...")

    chunker = SmartChunker()

    # 空文本
    empty_chunks = chunker.chunk_text("")
    assert len(empty_chunks) == 0, "空文本应该返回空列表"

    # 没有双井号的文本
    no_hash_text = "这是一段没有双井号的文本"
    no_hash_chunks = chunker.chunk_text(no_hash_text)
    assert len(no_hash_chunks) == 0, "没有双井号的文本应该返回空列表"

    # 只有大标题没有Overview的文本
    only_title_text = "# Main Title\nSome content here."
    only_title_chunks = chunker.chunk_text(only_title_text)
    assert len(only_title_chunks) == 0, "只有大标题没有双井号章节应该返回空列表"

    print("✅ 边界情况测试通过\n")


def main():
    """运行所有测试"""
    print("🚀 开始测试 Chunking 模块")
    print("=" * 50)
    
    try:
        test_basic_chunking()
        test_detailed_chunking()
        test_double_hash_splitting()
        test_break_point_type()
        test_edge_cases()
        
        print("🎉 所有测试通过！")
        print("✅ Chunking 模块工作正常")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
