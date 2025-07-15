#!/usr/bin/env python3
"""
测试 _build_chunk_content 三部分组合逻辑的潜在冲突
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chunking import SmartChunker


def test_three_parts_extraction():
    """测试三部分提取的边界和内容"""
    print("🔍 测试三部分提取逻辑...")
    
    chunker = SmartChunker()
    
    # 构造测试文档：Overview 有明确结束，外部有 H3，且文档足够长触发 H3 分割
    test_text = """# Main Title
This is the introduction content before any sections.

## Overview
This is the overview section that explains the main concepts.

### Key Concept in Overview
This concept is explained in the overview.

### Another Concept in Overview
Another important concept in overview.

## Implementation Details
This section comes after overview and contains implementation details.

### H3 Outside Overview
This is content outside the overview section.
It should be treated as a separate section.

### Another H3 Outside
More content outside overview.

Some final content to make the document longer.
""" + "Additional content to make it longer than 5000 characters. " * 100

    print(f"文档长度: {len(test_text)} 字符")
    
    # 分别测试三个提取方法
    title_part = chunker._extract_title_part(test_text)
    overview_h2 = chunker._extract_overview_for_h2(test_text)
    overview_h3 = chunker._extract_overview_for_h3(test_text)
    h3_sections = chunker._split_h3_sections(test_text)
    
    print(f"\n📋 三部分提取结果:")
    print(f"Title part 长度: {len(title_part)} 字符")
    print(f"Title part 内容: {repr(title_part[:100])}...")

    print(f"\nOverview H2 长度: {len(overview_h2)} 字符")
    print(f"Overview H2 内容: {repr(overview_h2[:200])}...")

    print(f"\nOverview H3 长度: {len(overview_h3)} 字符")
    print(f"Overview H3 内容: {repr(overview_h3[:200])}...")

    print(f"\nH3 sections 数量: {len(h3_sections)}")
    for i, section in enumerate(h3_sections):
        print(f"  Section {i+1}: {len(section)} 字符")
        print(f"    开头: {repr(section[:50])}...")

    # 检查是否存在内容重叠
    print(f"\n🔍 检查内容重叠:")

    # 检查 Overview 是否包含 H3 内容
    overview_h2_has_h3 = "### Key Concept in Overview" in overview_h2
    overview_h3_has_h3 = "### Key Concept in Overview" in overview_h3
    print(f"Overview H2 包含内部 H3: {'✅' if overview_h2_has_h3 else '❌'}")
    print(f"Overview H3 包含内部 H3: {'✅' if overview_h3_has_h3 else '❌'}")

    # 检查 H3 sections 是否包含 Overview 外的内容
    h3_outside_found = any("### H3 Outside Overview" in section for section in h3_sections)
    print(f"H3 sections 包含外部 H3: {'✅' if h3_outside_found else '❌'}")

    print(f"重构成功: 两种 Overview 提取方式已实现 ✅")

    # 调试：检查为什么 H3 sections 为空
    if len(h3_sections) == 0:
        print(f"\n🔍 调试 H3 sections 为空的原因:")
        lines = test_text.split('\n')
        h3_lines = [i for i, line in enumerate(lines) if line.startswith('### ')]
        print(f"文档中的 ### 行号: {h3_lines}")

        overview_start = None
        overview_end = None
        for i, line in enumerate(lines):
            if line.strip() == '## Overview':
                overview_start = i
            elif overview_start is not None and line.startswith('## '):
                overview_end = i
                break

        if overview_start is not None and overview_end is None:
            overview_end = len(lines)

        print(f"Overview 范围: {overview_start} - {overview_end}")

        for h3_line in h3_lines:
            in_overview = overview_start is not None and overview_start <= h3_line < (overview_end or len(lines))
            print(f"  行 {h3_line}: {lines[h3_line][:50]}... ({'在 Overview 内' if in_overview else '在 Overview 外'})")

    return title_part, overview_h2, h3_sections


def test_h2_splitting_logic():
    """测试 H2 分割逻辑"""
    print("\n🔧 测试 H2 分割逻辑...")

    chunker = SmartChunker()

    # 测试 H2 分割
    test_text = """# Main Title
Introduction content.

## Overview
Overview content.

## Implementation Details
Implementation content.

## Conclusion
Conclusion content.
"""

    h2_sections = chunker._split_h2_sections(test_text)
    print(f"H2 sections 数量: {len(h2_sections)}")

    for i, section in enumerate(h2_sections):
        print(f"  Section {i+1}: {len(section)} 字符")
        print(f"    开头: {repr(section[:50])}...")


def test_chunk_building_logic():
    """测试 chunk 构建逻辑"""
    print("\n🔧 测试 chunk 构建逻辑...")

    chunker = SmartChunker()

    # 使用测试文档：确保触发 H3 分割逻辑
    test_text = """# Main Title
Introduction content.

## Overview
Overview content with detailed explanations.

### Overview H3
Content in overview section.

### Another Overview H3
More content in overview section.

## Implementation Details
This section comes after overview.

### Outside H3
This content is outside the overview section.

### Another Outside H3
More content outside overview section.
""" + "Padding content to exceed 5000 characters. " * 200

    print(f"测试文档长度: {len(test_text)} 字符")

    # 测试各个组件
    h2_sections = chunker._split_h2_sections(test_text)
    h3_sections = chunker._split_h3_sections(test_text)

    print(f"H2 sections: {len(h2_sections)}")
    print(f"H3 sections: {len(h3_sections)}")

    # 执行完整的 chunking 流程
    chunks = chunker.chunk_text(test_text)

    print(f"生成的 chunks 数量: {len(chunks)}")

    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        print(f"  长度: {len(chunk)} 字符")

        # 分析 chunk 内容结构
        has_title = "# Main Title" in chunk
        has_overview = "## Overview" in chunk
        has_impl_details = "## Implementation Details" in chunk
        has_overview_h3 = "### Overview H3" in chunk
        has_outside_h3 = "### Outside H3" in chunk

        print(f"  包含主标题: {'✅' if has_title else '❌'}")
        print(f"  包含 Overview: {'✅' if has_overview else '❌'}")
        print(f"  包含 Implementation Details: {'✅' if has_impl_details else '❌'}")
        print(f"  包含 Overview 内 H3: {'✅' if has_overview_h3 else '❌'}")
        print(f"  包含外部 H3: {'✅' if has_outside_h3 else '❌'}")

        # 检查是否存在逻辑问题
        if has_overview and has_overview_h3 and has_outside_h3:
            print(f"  ⚠️ 潜在问题：同时包含 Overview 和外部 H3，可能存在内容重复")


def main():
    """运行所有测试"""
    print("🚀 开始测试三部分组合逻辑冲突")
    print("=" * 60)
    
    try:
        test_three_parts_extraction()
        test_h2_splitting_logic()
        test_chunk_building_logic()

        print("\n🎉 测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
