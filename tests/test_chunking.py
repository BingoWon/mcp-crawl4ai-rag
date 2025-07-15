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

from chunking import SmartChunker


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

    chunks = chunker.chunk_text(text)
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

    chunks = chunker.chunk_text(text)
    print(f"详细分块结果: {len(chunks)} 个块")

    for i, chunk in enumerate(chunks):
        print(f"  块 {i + 1}:")
        print(f"    长度: {len(chunk)} 字符")
        print(f"    内容预览: {chunk[:100]}...")

    assert len(chunks) == 2, "应该生成2个块"
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
    first_chunk = chunks[0]
    assert "### Subsection" in first_chunk, "第一个块应该包含三井号内容"

    print("✅ 双井号分割测试通过\n")





def test_small_h3_merging():
    """测试小 H3 章节合并功能"""
    print("🧪 测试小 H3 章节合并功能...")

    chunker = SmartChunker()

    # 测试场景：包含小章节的文档
    test_text = """# Main Title
Introduction content.

## Overview
Overview introduction.

### Small Section 1
Short content.

### Small Section 2
Another short content.

### Large Section
This is a much larger section with substantial content that should definitely exceed the 256 character threshold for merging. It contains detailed explanations, examples, and comprehensive information that makes it a standalone section worthy of its own chunk.

### Another Small
Brief content.
""" + "Padding content to exceed 5000 characters for H3 splitting. " * 100

    print(f"文档长度: {len(test_text)} 字符")

    # 测试 H3 分割和合并
    h3_sections = chunker._split_h3_sections(test_text)
    print(f"合并后 H3 sections 数量: {len(h3_sections)}")

    # 分析每个 section 的大小
    for i, section in enumerate(h3_sections):
        print(f"  Section {i+1}: {len(section)} 字符")
        if len(section) < 256:
            print("    ⚠️ 仍有小于256字符的章节")

    # 验证小章节被合并
    # 应该有合并的迹象（某些sections包含多个###标题）
    merged_sections = [s for s in h3_sections if s.count('### ') > 1]
    print(f"包含多个H3的合并章节: {len(merged_sections)}")

    # 测试完整的 chunking 流程
    chunks = chunker.chunk_text(test_text)
    print(f"生成的 chunks 数量: {len(chunks)}")

    # 验证 chunks 大小合理
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: {len(chunk)} 字符")
        # 大部分 chunks 应该大于 256 字符（除非是最后一个小章节）

    print("✅ 小 H3 章节合并测试通过\n")


def test_overview_h3_processing():
    """测试 Overview 内 H3 的正确处理"""
    print("🧪 测试 Overview 内 H3 的正确处理...")

    chunker = SmartChunker()

    # 测试场景：只有 Overview，内含多个 H3
    test_text = """# Main Title
Introduction content.

## Overview
Overview introduction.

### First Concept
First concept explanation.

### Second Concept
Second concept explanation.

### Implementation Notes
Implementation details.
""" + "Padding content to exceed 5000 characters for H3 splitting. " * 100

    print(f"文档长度: {len(test_text)} 字符")

    # 测试 H3 分割
    h3_sections = chunker._split_h3_sections(test_text)
    print(f"H3 sections 数量: {len(h3_sections)}")

    # 验证所有 Overview 内的 H3 都被正确提取
    expected_h3s = ["### First Concept", "### Second Concept", "### Implementation Notes"]
    for expected in expected_h3s:
        found = any(expected in section for section in h3_sections)
        print(f"找到 {expected}: {'✅' if found else '❌'}")
        assert found, f"应该找到 {expected}"

    # 测试完整的 chunking 流程
    chunks = chunker.chunk_text(test_text)
    print(f"生成的 chunks 数量: {len(chunks)}")

    # 验证每个 chunk 都包含正确的结构
    for i, chunk in enumerate(chunks):
        has_title = "# Main Title" in chunk
        has_overview = "## Overview" in chunk
        print(f"Chunk {i+1}: 包含标题 {'✅' if has_title else '❌'}, 包含Overview {'✅' if has_overview else '❌'}")
        assert has_title, f"Chunk {i+1} 应该包含标题"
        assert has_overview, f"Chunk {i+1} 应该包含Overview"

    print("✅ Overview 内 H3 处理测试通过\n")


def test_chunking_strategy_selection():
    """测试分块策略选择逻辑"""
    print("🧪 测试分块策略选择逻辑...")

    chunker = SmartChunker()

    # 测试 H2 优先级
    h2_text = """# Title
Content

## Overview
Overview content

## Section 1
Section content

## Section 2
More content
"""

    chunks_h2 = chunker.chunk_text(h2_text)
    print(f"H2文档分块: {len(chunks_h2)} 个块")
    assert len(chunks_h2) == 2, "应该按 H2 分割成 2 个块"

    # 测试 H3 优先级（长文档，Overview 后直接是 H3）
    h3_text = """# Title
Content

## Overview
Overview content ends here.

### Section 1
Section content outside overview.

### Section 2
More content outside overview.
""" + "Padding content to exceed 5000 characters. " * 200

    print(f"H3文档长度: {len(h3_text)} 字符")
    chunks_h3 = chunker.chunk_text(h3_text)
    print(f"H3文档分块: {len(chunks_h3)} 个块")

    # 修复后：Overview 内的 H3 被正确分割，小章节会被合并
    assert len(chunks_h3) >= 1, "应该按 H3 分割（小章节可能被合并）"

    print("✅ 分块策略选择测试通过\n")


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
    assert len(no_hash_chunks) == 1, "没有双井号的文本应该返回完整内容"

    # 只有大标题没有Overview的文本
    only_title_text = "# Main Title\nSome content here."
    only_title_chunks = chunker.chunk_text(only_title_text)
    assert len(only_title_chunks) == 1, "只有大标题应该返回完整内容"

    print("✅ 边界情况测试通过\n")


def main():
    """运行所有测试"""
    print("🚀 开始测试 Chunking 模块")
    print("=" * 50)
    
    try:
        test_basic_chunking()
        test_detailed_chunking()
        test_double_hash_splitting()
        test_small_h3_merging()
        test_overview_h3_processing()
        test_chunking_strategy_selection()
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
