#!/usr/bin/env python3
"""
测试苹果芯片内存监控功能
验证 log_gpu_memory 方法在苹果芯片上的正确性
"""

import os
import sys
import torch
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler.core import IndependentCrawler
from utils.logger import setup_logger

logger = setup_logger(__name__)


def test_mps_memory():
    """测试苹果芯片MPS内存功能"""
    print("🍎 测试苹果芯片MPS内存功能...")

    allocated = torch.mps.current_allocated_memory() / 1024**3
    print(f"📊 当前MPS内存使用: {allocated:.2f}GB")

    return allocated


def test_crawler_mps_logging():
    """测试爬虫MPS内存日志功能"""
    print("\n🚀 测试爬虫MPS内存日志功能...")

    try:
        # 创建爬虫实例
        crawler = IndependentCrawler()

        # 测试MPS内存日志方法
        print("📊 测试MPS内存监控...")
        crawler.log_mps_memory("测试开始")

        # 创建测试张量使用MPS内存
        test_tensor = torch.randn(1000, 1000, device="mps")
        crawler.log_mps_memory("创建测试张量后")

        # 清理张量
        del test_tensor
        crawler.log_mps_memory("清理后")

        print("✅ MPS内存监控功能正常工作")
        return True

    except Exception as e:
        print(f"❌ MPS内存监控测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """苹果芯片专用测试函数"""
    print("🍎 苹果芯片MPS内存监控测试")
    print("=" * 50)

    # 1. 测试MPS内存
    initial_memory = test_mps_memory()

    # 2. 测试爬虫MPS内存日志功能
    success = test_crawler_mps_logging()

    print("\n" + "=" * 50)
    print(f"📊 初始MPS内存: {initial_memory:.2f}GB")
    print(f"✅ 测试结果: {'成功' if success else '失败'}")
    print("🍎 苹果芯片 MPS 内存监控专用版本")


if __name__ == "__main__":
    main()
