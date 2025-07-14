#!/usr/bin/env python3
"""
真实内存问题验证测试
展示优化前后的真实差异，不使用任何强制重载
"""

import os
import sys
import asyncio
import torch
import time
from typing import Dict, Any

# 添加src到路径
sys.path.append('src')

from utils.logger import setup_logger

logger = setup_logger(__name__)


def get_gpu_memory_usage() -> Dict[str, float]:
    """获取GPU内存使用情况"""
    if torch.cuda.is_available():
        return {
            "allocated_gb": torch.cuda.memory_allocated() / 1024**3,
            "reserved_gb": torch.cuda.memory_reserved() / 1024**3,
        }
    elif torch.backends.mps.is_available():
        return {
            "allocated_gb": torch.mps.current_allocated_memory() / 1024**3,
            "reserved_gb": 0.0,
        }
    else:
        return {"allocated_gb": 0.0, "reserved_gb": 0.0}


def monitor_memory(stage: str):
    """监控并显示内存使用"""
    memory = get_gpu_memory_usage()
    print(f"📊 {stage}: GPU内存 {memory['allocated_gb']:.2f}GB")
    return memory['allocated_gb']


async def test_real_crawler_usage():
    """测试真实的crawler使用场景"""
    print("🚀 测试真实crawler使用场景...")
    
    # 初始内存
    initial_memory = monitor_memory("初始状态")
    
    try:
        # 导入crawler（这可能触发embedding模型加载）
        from crawler.core import IndependentCrawler
        after_import = monitor_memory("导入crawler后")
        
        # 创建crawler实例
        async with IndependentCrawler() as crawler:
            after_init = monitor_memory("crawler初始化后")
            
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
            after_processing = monitor_memory("内容处理后")
            
            # 再次处理内容（测试模型复用）
            print("📝 再次处理内容...")
            result2 = await crawler._process_and_store_content(
                "https://developer.apple.com/documentation/swiftui/view",
                test_content + "\n\nAdditional content for second processing."
            )
            after_second = monitor_memory("第二次处理后")
            
            print(f"✅ 第一次处理结果: {result.get('success', False)}")
            print(f"✅ 第二次处理结果: {result2.get('success', False)}")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    final_memory = monitor_memory("测试完成")
    
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


async def test_multiple_crawler_instances():
    """测试多个crawler实例（可能触发多进程问题）"""
    print("\n🔄 测试多个crawler实例...")
    
    initial_memory = monitor_memory("多实例测试初始")
    
    try:
        from crawler.core import IndependentCrawler
        
        # 第一个实例
        print("📱 创建第一个crawler实例...")
        async with IndependentCrawler() as crawler1:
            after_first = monitor_memory("第一个实例创建后")
            
            # 第二个实例
            print("📱 创建第二个crawler实例...")
            async with IndependentCrawler() as crawler2:
                after_second = monitor_memory("第二个实例创建后")
                
                # 同时使用两个实例
                test_content = "Test content for multiple instances"
                
                result1 = await crawler1._process_and_store_content(
                    "https://test1.example.com", test_content
                )
                after_use1 = monitor_memory("使用实例1后")
                
                result2 = await crawler2._process_and_store_content(
                    "https://test2.example.com", test_content
                )
                after_use2 = monitor_memory("使用实例2后")
                
                print(f"✅ 实例1处理结果: {result1.get('success', False)}")
                print(f"✅ 实例2处理结果: {result2.get('success', False)}")
        
    except Exception as e:
        print(f"❌ 多实例测试出现错误: {e}")
        return None
    
    final_memory = monitor_memory("多实例测试完成")
    
    return {
        "initial": initial_memory,
        "after_first": after_first,
        "after_second": after_second,
        "after_use1": after_use1,
        "after_use2": after_use2,
        "final": final_memory,
        "total_increase": final_memory - initial_memory
    }


def test_direct_embedding_calls():
    """测试直接的embedding调用"""
    print("\n🧠 测试直接embedding调用...")
    
    initial_memory = monitor_memory("直接调用测试初始")
    
    try:
        from embedding import create_embedding
        
        # 第一次调用
        print("🔤 第一次embedding调用...")
        embedding1 = create_embedding("First embedding test")
        after_first = monitor_memory("第一次调用后")
        
        # 第二次调用
        print("🔤 第二次embedding调用...")
        embedding2 = create_embedding("Second embedding test")
        after_second = monitor_memory("第二次调用后")
        
        # 第三次调用
        print("🔤 第三次embedding调用...")
        embedding3 = create_embedding("Third embedding test")
        after_third = monitor_memory("第三次调用后")
        
        print(f"✅ Embedding维度: {len(embedding1)}")
        print(f"✅ 三次调用都成功完成")
        
    except Exception as e:
        print(f"❌ 直接调用测试出现错误: {e}")
        return None
    
    final_memory = monitor_memory("直接调用测试完成")
    
    return {
        "initial": initial_memory,
        "after_first": after_first,
        "after_second": after_second,
        "after_third": after_third,
        "final": final_memory,
        "total_increase": final_memory - initial_memory,
        "second_call_increase": after_second - after_first,
        "third_call_increase": after_third - after_second
    }


async def main():
    """主测试函数"""
    print("🎯 真实内存问题验证测试")
    print("=" * 60)
    print("📋 测试说明：")
    print("- 不使用任何强制重载")
    print("- 模拟真实使用场景")
    print("- 监控内存使用变化")
    print("=" * 60)
    
    # 检查环境变量
    tokenizers_setting = os.environ.get("TOKENIZERS_PARALLELISM", "未设置")
    print(f"🔧 TOKENIZERS_PARALLELISM = {tokenizers_setting}")
    
    try:
        # 测试1: 真实crawler使用
        crawler_result = await test_real_crawler_usage()
        
        # 测试2: 多个crawler实例
        multi_result = await test_multiple_crawler_instances()
        
        # 测试3: 直接embedding调用
        direct_result = test_direct_embedding_calls()
        
        print("\n" + "=" * 60)
        print("📊 测试结果汇总:")
        
        if crawler_result:
            print(f"🚀 Crawler测试:")
            print(f"   总内存增加: {crawler_result['total_increase']:.2f}GB")
            print(f"   第二次处理增加: {crawler_result['second_processing_increase']:.2f}GB")
        
        if multi_result:
            print(f"🔄 多实例测试:")
            print(f"   总内存增加: {multi_result['total_increase']:.2f}GB")
        
        if direct_result:
            print(f"🧠 直接调用测试:")
            print(f"   总内存增加: {direct_result['total_increase']:.2f}GB")
            print(f"   第二次调用增加: {direct_result['second_call_increase']:.2f}GB")
            print(f"   第三次调用增加: {direct_result['third_call_increase']:.2f}GB")
        
        # 评估结果
        print("\n🔍 结果评估:")
        
        if direct_result and direct_result['second_call_increase'] < 1.0:
            print("✅ 模型复用正常：第二次调用没有显著内存增加")
        elif direct_result:
            print(f"❌ 可能存在问题：第二次调用增加了 {direct_result['second_call_increase']:.2f}GB")
        
        if crawler_result and crawler_result['second_processing_increase'] < 1.0:
            print("✅ Crawler复用正常：重复处理没有显著内存增加")
        elif crawler_result:
            print(f"❌ Crawler可能有问题：重复处理增加了 {crawler_result['second_processing_increase']:.2f}GB")
        
        # 总体内存使用评估
        total_memory = 0
        if direct_result:
            total_memory = max(total_memory, direct_result['final'])
        if crawler_result:
            total_memory = max(total_memory, crawler_result['final'])
        if multi_result:
            total_memory = max(total_memory, multi_result['final'])
        
        print(f"\n📈 峰值GPU内存使用: {total_memory:.2f}GB")
        
        if total_memory > 50:
            print("🚨 警告：内存使用超过50GB，可能存在问题")
        elif total_memory > 30:
            print("⚠️ 注意：内存使用较高，需要关注")
        else:
            print("✅ 内存使用在合理范围内")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
