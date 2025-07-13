"""
Debug Markdown Recognition
调试 Markdown 识别

Debug why ### headers are still being recognized.
调试为什么仍然识别 ### 标题。
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chunking import SmartChunker
from chunking.strategy import BreakPointType


def debug_markdown_recognition():
    """调试 Markdown 识别"""
    print("🔍 调试 Markdown 识别...")
    
    text = """## 主要章节
这是主要内容。

### 子章节（应该被忽略）
这是子章节内容。

## 另一个主要章节
更多主要内容。"""
    
    print(f"测试文本:")
    print(repr(text))
    print()
    
    chunker = SmartChunker()  # Apple文档双井号分割
    chunks = chunker.chunk_text(text)
    
    print(f"生成块数: {len(chunks)}")
    print()
    
    for i, chunk in enumerate(chunks):
        print(f"块 {i+1} ({chunk.break_type.value}):")
        print(f"  位置: {chunk.start_pos}-{chunk.end_pos}")
        print(f"  长度: {len(chunk.content)} 字符")
        print(f"  内容: {repr(chunk.content)}")
        print()
        
        # 检查是否包含 ### 并且被标记为 MARKDOWN_HEADER
        if chunk.break_type == BreakPointType.MARKDOWN_HEADER and '###' in chunk.content:
            print(f"  ❌ 错误：包含 ### 但被标记为 MARKDOWN_HEADER")
        elif chunk.break_type == BreakPointType.MARKDOWN_HEADER and '## ' in chunk.content:
            print(f"  ✅ 正确：包含 ## 并被标记为 MARKDOWN_HEADER")


def debug_large_text():
    """调试大文本"""
    print("🔍 调试大文本...")
    
    text = """## 第一章
这是第一章的内容。

### 子章节（应该被忽略）
子章节内容。

## 第二章
这是第二章的内容。""" * 3
    
    print(f"大文本长度: {len(text)} 字符")
    
    chunker = SmartChunker()
    chunks = chunker.chunk_text(text)
    
    print(f"生成块数: {len(chunks)}")
    
    markdown_header_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"块 {i+1} ({chunk.break_type.value}): {len(chunk.content)} 字符")
        
        if chunk.break_type == BreakPointType.MARKDOWN_HEADER:
            markdown_header_chunks.append(chunk)
            print(f"  内容开头: {repr(chunk.content[:30])}...")
            
            # 检查分割点
            if chunk.content.startswith('## '):
                print(f"  ✅ 正确：在 ## 标题处分割")
            elif '### ' in chunk.content:
                print(f"  ❌ 错误：包含 ### 标题")
    
    print(f"\nMarkdown 标题块总数: {len(markdown_header_chunks)}")


def main():
    """运行调试"""
    print("🚀 开始调试 Markdown 识别")
    print("=" * 50)
    
    debug_markdown_recognition()
    print()
    
    debug_large_text()


if __name__ == "__main__":
    main()
