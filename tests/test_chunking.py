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

from chunking import SmartChunker, ChunkingStrategy
from chunking.strategy import BreakPointType


def test_basic_chunking():
    """测试基本分块功能"""
    print("🧪 测试基本分块功能...")
    
    chunker = SmartChunker(chunk_size=50)
    text = "这是第一段。\n\n这是第二段。它有多个句子。\n这是第三行。"
    
    chunks = chunker.chunk_text_simple(text)
    print(f"输入文本: {repr(text)}")
    print(f"分块结果: {len(chunks)} 个块")
    for i, chunk in enumerate(chunks):
        print(f"  块 {i+1}: {repr(chunk)}")
    
    assert len(chunks) > 0, "应该生成至少一个块"
    print("✅ 基本分块测试通过\n")


def test_detailed_chunking():
    """测试详细分块信息"""
    print("🧪 测试详细分块信息...")
    
    chunker = SmartChunker(chunk_size=30)
    text = "段落一。\n\n段落二。\n单行。句子结尾! 另一句?"
    
    chunk_infos = chunker.chunk_text(text)
    print(f"输入文本: {repr(text)}")
    print(f"详细分块结果: {len(chunk_infos)} 个块")
    
    for chunk_info in chunk_infos:
        print(f"  块 {chunk_info.chunk_index + 1}:")
        print(f"    内容: {repr(chunk_info.content)}")
        print(f"    位置: {chunk_info.start_pos}-{chunk_info.end_pos}")
        print(f"    分割类型: {chunk_info.break_type.value}")
    
    assert len(chunk_infos) > 0, "应该生成至少一个块"
    print("✅ 详细分块测试通过\n")


def test_break_point_priorities():
    """测试分割点优先级"""
    print("🧪 测试分割点优先级...")
    
    chunker = SmartChunker(chunk_size=20)
    
    # 测试段落分隔符优先级
    text1 = "短文本。\n\n新段落开始"
    chunks1 = chunker.chunk_text(text1)
    if chunks1:
        print(f"段落分隔符测试: {chunks1[0].break_type.value}")
        assert chunks1[0].break_type == BreakPointType.PARAGRAPH
    
    # 测试换行符优先级
    text2 = "第一行内容\n第二行内容继续"
    chunks2 = chunker.chunk_text(text2)
    if chunks2:
        print(f"换行符测试: {chunks2[0].break_type.value}")
        # 可能是换行符或强制分割，取决于具体长度
    
    # 测试句子结尾优先级
    text3 = "这是一个句子. 这是另一个句子继续"
    chunks3 = chunker.chunk_text(text3)
    if chunks3:
        print(f"句子结尾测试: {chunks3[0].break_type.value}")
    
    print("✅ 分割点优先级测试通过\n")


def test_strategy_info():
    """测试策略信息"""
    print("🧪 测试策略信息...")
    
    strategy_info = ChunkingStrategy.get_strategy_info()
    print(f"策略标题: {strategy_info['title']}")
    print(f"策略描述: {strategy_info['description']}")
    print(f"优先级数量: {len(strategy_info['priorities'])}")
    
    colors = ChunkingStrategy.get_break_point_colors()
    print(f"颜色配置: {len(colors)} 种类型")
    for break_type, color in colors.items():
        print(f"  {break_type.value}: {color}")
    
    assert "title" in strategy_info
    assert "priorities" in strategy_info
    assert len(colors) == 4  # 四种分割类型
    print("✅ 策略信息测试通过\n")


def test_edge_cases():
    """测试边界情况"""
    print("🧪 测试边界情况...")
    
    chunker = SmartChunker(chunk_size=100)
    
    # 空文本
    empty_chunks = chunker.chunk_text("")
    assert len(empty_chunks) == 0, "空文本应该返回空列表"
    
    # 非常短的文本
    short_text = "短"
    short_chunks = chunker.chunk_text(short_text)
    assert len(short_chunks) == 1, "短文本应该返回一个块"
    assert short_chunks[0].content == "短"
    
    # 只有空白字符的文本
    whitespace_text = "   \n\n   "
    whitespace_chunks = chunker.chunk_text(whitespace_text)
    # 应该被 strip() 处理，可能为空
    
    print("✅ 边界情况测试通过\n")


def main():
    """运行所有测试"""
    print("🚀 开始测试 Chunking 模块")
    print("=" * 50)
    
    try:
        test_basic_chunking()
        test_detailed_chunking()
        test_break_point_priorities()
        test_strategy_info()
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
