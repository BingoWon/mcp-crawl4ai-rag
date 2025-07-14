#!/usr/bin/env python3
"""
苹果芯片MPS内存验证测试
专为Apple Silicon优化的内存监控测试
"""

import os
import sys
import asyncio
import torch

# 添加src到路径
sys.path.append('src')

from utils.logger import setup_logger

logger = setup_logger(__name__)


def get_mps_memory_usage() -> float:
    """获取苹果芯片MPS内存使用情况"""
    return torch.mps.current_allocated_memory() / 1024**3


def monitor_mps_memory(stage: str):
    """监控并显示MPS内存使用"""
    memory = get_mps_memory_usage()
    print(f"📊 {stage}: MPS内存 {memory:.2f}GB")
    return memory


async def test_apple_silicon_crawler():
    """测试苹果芯片专用crawler使用场景"""
    print("🍎 测试苹果芯片专用crawler使用场景...")
    
    # 初始内存
    initial_memory = monitor_mps_memory("初始状态")
    
    try:
        # 导入crawler（这可能触发embedding模型加载）
        from crawler.core import IndependentCrawler
        after_import = monitor_mps_memory("导入crawler后")
        
        # 创建crawler实例
        async with IndependentCrawler() as crawler:
            after_init = monitor_mps_memory("crawler初始化后")
            
            # 模拟真实的内容处理（这会触发embedding）
            test_content = """
            # SwiftUI Documentation
            
            SwiftUI is a modern way to declare user interfaces for any Apple platform.
            
            ## Overview
            
            SwiftUI provides views, controls, and layout structures for declaring your app's user interface.
            """
            
            print("📝 开始处理内容...")
            result = await crawler._process_and_store_content(
                "https://developer.apple.com/documentation/swiftui",
                test_content
            )
            after_processing = monitor_mps_memory("内容处理后")
            
            # 再次处理内容（测试模型复用）
            print("📝 再次处理内容...")
            result2 = await crawler._process_and_store_content(
                "https://developer.apple.com/documentation/swiftui/view",
                test_content + "\n\nAdditional content for second processing."
            )
            after_second = monitor_mps_memory("第二次处理后")
            
            print(f"✅ 第一次处理结果: {result.get('success', False)}")
            print(f"✅ 第二次处理结果: {result2.get('success', False)}")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    final_memory = monitor_mps_memory("测试完成")
    
    return {
        "initial": initial_memory,
        "after_import": after_import,
        "after_init": after_init,
        "after_processing": after_processing,
        "after_second": after_second,
        "final": final_memory,
        "total_increase": final_memory - initial_memory,
        "second_processing_increase": after_second - after_processing
    }


async def test_apple_silicon_embedding():
    """测试苹果芯片专用embedding"""
    print("🍎 测试苹果芯片专用embedding...")
    
    initial_memory = monitor_mps_memory("初始状态")
    
    try:
        from embedding import create_embedding
        
        # 第一次调用
        print("🔤 第一次embedding调用...")
        create_embedding("First embedding test")
        after_first = monitor_mps_memory("第一次调用后")
        
        # 第二次调用
        print("🔤 第二次embedding调用...")
        create_embedding("Second embedding test")
        after_second = monitor_mps_memory("第二次调用后")
        
        # 第三次调用
        print("🔤 第三次embedding调用...")
        create_embedding("Third embedding test")
        after_third = monitor_mps_memory("第三次调用后")
        
        print("✅ Embedding测试完成")
        
    except Exception as e:
        print(f"❌ Embedding测试失败: {e}")
        return None
    
    final_memory = monitor_mps_memory("测试完成")
    
    return {
        "initial": initial_memory,
        "after_first": after_first,
        "after_second": after_second,
        "after_third": after_third,
        "final": final_memory,
        "total_increase": final_memory - initial_memory
    }


async def main():
    """苹果芯片专用主测试函数"""
    print("🍎 苹果芯片MPS内存验证测试")
    print("=" * 60)
    print("📋 测试说明：")
    print("- 专为Apple Silicon MPS优化")
    print("- 监控MPS内存使用变化")
    print("- 验证embedding和crawler性能")
    print("=" * 60)
    
    try:
        # 测试1: 苹果芯片crawler使用
        crawler_result = await test_apple_silicon_crawler()
        
        # 测试2: 苹果芯片embedding
        embedding_result = await test_apple_silicon_embedding()
        
        # 结果分析
        print("\n" + "=" * 60)
        print("📈 测试结果分析:")
        
        if crawler_result:
            print(f"🚀 Crawler测试: 内存增长 {crawler_result['total_increase']:.2f}GB")
        
        if embedding_result:
            print(f"🔤 Embedding测试: 内存增长 {embedding_result['total_increase']:.2f}GB")
        
        # 总体内存使用评估
        total_memory = 0
        if crawler_result:
            total_memory = max(total_memory, crawler_result['final'])
        if embedding_result:
            total_memory = max(total_memory, embedding_result['final'])
        
        print(f"\n📈 峰值MPS内存使用: {total_memory:.2f}GB")
        
        if total_memory > 30:
            print("⚠️ 注意：MPS内存使用较高，需要关注")
        else:
            print("✅ MPS内存使用在合理范围内")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
