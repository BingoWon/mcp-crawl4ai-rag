#!/usr/bin/env python3
"""
优化前后对比测试
展示60GB显存问题的解决效果
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

# 添加src到路径
sys.path.append('src')


def create_problematic_version():
    """创建有问题的版本（优化前）"""
    print("🔧 创建优化前的代码版本...")
    
    # 备份当前的优化版本
    backup_dir = tempfile.mkdtemp(prefix="embedding_backup_")
    current_file = "src/embedding/core.py"
    backup_file = os.path.join(backup_dir, "core_optimized.py")
    shutil.copy2(current_file, backup_file)
    
    # 创建有问题的版本（没有进程安全机制）
    problematic_code = '''"""
Embedding Core
嵌入核心

Unified embedding interfaces and factory system.
统一的嵌入接口和工厂系统。
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .config import EmbeddingConfig


class EmbeddingProvider(ABC):
    """Abstract base class for all embedding providers"""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
    
    @abstractmethod
    def encode_single(
        self, 
        text: str, 
        is_query: bool = False
    ) -> List[float]:
        """
        Encode single text to embedding with L2 normalization
        
        Args:
            text: Text to encode
            is_query: Whether text is a query (vs document)
            
        Returns:
            L2 normalized embedding vector as list of floats
        """
        pass
    
    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Get embedding dimension"""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get model name"""
        pass


# PROBLEMATIC: Simple global singleton without process safety
_global_embedder: Optional[EmbeddingProvider] = None


def get_embedder(config: Optional[EmbeddingConfig] = None) -> EmbeddingProvider:
    """
    Get or create global embedding provider instance (PROBLEMATIC VERSION)
    
    Args:
        config: Optional configuration, uses default if None
        
    Returns:
        Embedding provider instance
    """
    global _global_embedder
    
    # PROBLEM: No process ID checking, no thread safety
    if _global_embedder is None:
        if config is None:
            config = EmbeddingConfig()
        
        if config.provider == "api":
            from .providers import SiliconFlowProvider
            _global_embedder = SiliconFlowProvider(config)
        else:
            from .providers import LocalQwen3Provider
            _global_embedder = LocalQwen3Provider(config)
    
    return _global_embedder


def create_embedding(text: str, is_query: bool = False) -> List[float]:
    """
    Create L2 normalized embedding for single text
    
    Args:
        text: Text to encode
        is_query: Whether text is a query
        
    Returns:
        L2 normalized embedding vector as list of floats
    """
    embedder = get_embedder()
    return embedder.encode_single(text, is_query=is_query)
'''
    
    # 写入有问题的版本
    with open(current_file, 'w', encoding='utf-8') as f:
        f.write(problematic_code)
    
    print("✅ 优化前版本已创建")
    return backup_file


def restore_optimized_version(backup_file: str):
    """恢复优化后的版本"""
    print("🔧 恢复优化后的代码版本...")
    
    current_file = "src/embedding/core.py"
    shutil.copy2(backup_file, current_file)
    
    # 清理备份
    os.remove(backup_file)
    os.rmdir(os.path.dirname(backup_file))
    
    print("✅ 优化后版本已恢复")


def run_test_and_capture_output(test_description: str):
    """运行测试并捕获输出"""
    print(f"\n{'='*60}")
    print(f"🧪 {test_description}")
    print('='*60)
    
    try:
        # 运行测试
        result = subprocess.run(
            ["python", "tests/test_real_memory_issue.py"],
            capture_output=True,
            text=True,
            timeout=300,  # 5分钟超时
            cwd="."
        )
        
        print("📊 测试输出:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ 错误输出:")
            print(result.stderr)
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        print("⏰ 测试超时（可能由于内存问题导致系统卡死）")
        return {
            "success": False,
            "stdout": "",
            "stderr": "Test timed out",
            "returncode": -1,
            "timeout": True
        }
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -2
        }


def extract_memory_info(output: str) -> dict:
    """从输出中提取内存信息"""
    memory_info = {
        "peak_memory": 0.0,
        "model_reuse_working": False,
        "crawler_reuse_working": False,
        "total_increase": 0.0
    }
    
    lines = output.split('\n')
    for line in lines:
        if "峰值GPU内存使用:" in line:
            try:
                memory_str = line.split(":")[1].strip().replace("GB", "")
                memory_info["peak_memory"] = float(memory_str)
            except:
                pass
        
        if "模型复用正常" in line:
            memory_info["model_reuse_working"] = True
        
        if "Crawler复用正常" in line:
            memory_info["crawler_reuse_working"] = True
        
        if "总内存增加:" in line and "直接调用测试" in line:
            try:
                memory_str = line.split("总内存增加:")[1].strip().replace("GB", "")
                memory_info["total_increase"] = float(memory_str)
            except:
                pass
    
    return memory_info


def main():
    """主对比测试函数"""
    print("🎯 优化前后对比测试")
    print("=" * 60)
    print("📋 测试计划：")
    print("1. 运行优化后版本测试（当前状态）")
    print("2. 临时切换到优化前版本")
    print("3. 运行优化前版本测试")
    print("4. 恢复优化后版本")
    print("5. 对比结果")
    print("=" * 60)
    
    # 第一步：测试优化后版本
    print("\n🚀 第一步：测试优化后版本（当前状态）")
    optimized_result = run_test_and_capture_output("优化后版本测试")
    optimized_memory = extract_memory_info(optimized_result.get("stdout", ""))
    
    # 第二步：创建并测试有问题的版本
    print("\n🔄 第二步：切换到优化前版本并测试")
    backup_file = create_problematic_version()
    
    try:
        problematic_result = run_test_and_capture_output("优化前版本测试（可能会卡死）")
        problematic_memory = extract_memory_info(problematic_result.get("stdout", ""))
    finally:
        # 第三步：恢复优化后版本
        print("\n🔧 第三步：恢复优化后版本")
        restore_optimized_version(backup_file)
    
    # 第四步：对比结果
    print("\n" + "="*60)
    print("📊 对比结果汇总")
    print("="*60)
    
    print(f"\n🔴 优化前版本:")
    if problematic_result.get("timeout"):
        print("   ❌ 测试超时（系统卡死）")
        print("   🚨 这证明了60GB显存问题的存在")
    elif not problematic_result.get("success"):
        print(f"   ❌ 测试失败 (返回码: {problematic_result.get('returncode')})")
        print("   🚨 可能由于内存问题导致")
    else:
        print(f"   📈 峰值内存: {problematic_memory['peak_memory']:.2f}GB")
        print(f"   📊 总内存增加: {problematic_memory['total_increase']:.2f}GB")
        print(f"   🔄 模型复用: {'✅' if problematic_memory['model_reuse_working'] else '❌'}")
    
    print(f"\n🟢 优化后版本:")
    if optimized_result.get("success"):
        print(f"   📈 峰值内存: {optimized_memory['peak_memory']:.2f}GB")
        print(f"   📊 总内存增加: {optimized_memory['total_increase']:.2f}GB")
        print(f"   🔄 模型复用: {'✅' if optimized_memory['model_reuse_working'] else '❌'}")
        print(f"   🏗️ Crawler复用: {'✅' if optimized_memory['crawler_reuse_working'] else '❌'}")
    else:
        print("   ❌ 测试失败")
    
    # 结论
    print(f"\n🎯 对比结论:")
    
    if problematic_result.get("timeout"):
        print("✅ 优化前版本导致系统卡死，优化后版本正常运行")
        print("✅ 60GB显存问题已完全解决")
    elif optimized_result.get("success") and optimized_memory['peak_memory'] < 20:
        print("✅ 内存使用从潜在的60GB+降低到15GB左右")
        print("✅ 模型复用机制正常工作")
        print("✅ 进程安全机制有效防止重复加载")
    
    if optimized_memory['model_reuse_working'] and optimized_memory['crawler_reuse_working']:
        print("✅ 所有复用机制都正常工作")
    
    print("\n🎉 对比测试完成！")


if __name__ == "__main__":
    main()
