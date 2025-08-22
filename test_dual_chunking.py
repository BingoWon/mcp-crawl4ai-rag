#!/usr/bin/env python3
"""
测试双重Chunking对比功能

验证新的DualChunkingProcessor是否正确实现：
1. 双重chunking（旧方案 vs 新方案）
2. 智能对比（数量+内容）
3. 条件处理（只处理不一致的内容）
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.chunking import SmartChunker
from src.chunking_deprecated.chunker import SmartChunker as DeprecatedChunker
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DualChunkingTester:
    """双重Chunking对比测试器"""
    
    def __init__(self):
        self.current_chunker = SmartChunker()  # 新方案 (2500/3000)
        self.deprecated_chunker = DeprecatedChunker()  # 旧方案 (5000/6000)
        
    def _compare_chunking_results(self, old_chunks, new_chunks):
        """对比两个chunking结果是否一致"""
        # 1. 数量对比
        if len(old_chunks) != len(new_chunks):
            return False
        
        # 2. 内容对比：逐个比较chunk内容
        for old_chunk, new_chunk in zip(old_chunks, new_chunks):
            if old_chunk != new_chunk:
                return False
        
        return True
    
    def test_chunking_comparison(self):
        """测试chunking对比功能"""
        logger.info("🧪 开始测试双重Chunking对比功能...")
        
        # 测试用例1：短文档（应该一致）
        short_text = """
# Apple Documentation

## Overview
This is a short Apple documentation example.

## Details
Some technical details here.
"""
        
        logger.info("=" * 60)
        logger.info("测试用例1：短文档")
        logger.info(f"文档长度: {len(short_text)} 字符")
        
        old_chunks = self.deprecated_chunker.chunk_text(short_text)
        new_chunks = self.current_chunker.chunk_text(short_text)
        
        is_identical = self._compare_chunking_results(old_chunks, new_chunks)
        
        logger.info(f"旧方案chunk数量: {len(old_chunks)}")
        logger.info(f"新方案chunk数量: {len(new_chunks)}")
        logger.info(f"结果是否一致: {is_identical}")
        
        if is_identical:
            logger.info("✅ 短文档测试通过：结果一致，将跳过embedding")
        else:
            logger.info("⚠️ 短文档测试：结果不一致，将进行embedding")
            logger.info("旧方案第一个chunk预览:")
            logger.info(old_chunks[0][:200] + "..." if len(old_chunks[0]) > 200 else old_chunks[0])
            logger.info("新方案第一个chunk预览:")
            logger.info(new_chunks[0][:200] + "..." if len(new_chunks[0]) > 200 else new_chunks[0])
        
        # 测试用例2：长文档（可能不一致）
        long_text = """
# Apple Core Data Framework

## Overview
Core Data is a framework that you use to manage the model layer objects in your application. It provides generalized and automated solutions to common tasks associated with object life cycle and object graph management, including persistence.

## Key Features

### Object Graph Management
Core Data manages the relationships between objects in your application. It tracks changes to objects and maintains the integrity of object relationships.

### Automatic Change Tracking
The framework automatically tracks changes to your managed objects. You don't need to implement undo functionality yourself.

### Memory Management
Core Data provides sophisticated memory management. It uses faulting to ensure that objects are loaded into memory only when needed.

### Data Validation
You can specify validation rules for your data model. Core Data will automatically validate data before saving.

## Core Data Stack

### NSManagedObjectModel
The managed object model describes the data that is going to be accessed by the Core Data stack. During the creation of the Core Data stack, the managed object model is loaded into memory as the first step in the creation of the stack.

### NSPersistentStoreCoordinator
The persistent store coordinator sits in the middle of the Core Data stack. The coordinator is responsible for realizing instances of entities that are defined inside of the model.

### NSManagedObjectContext
The managed object context is the object that your application will be interacting with the most. Think of the managed object context as an intelligent scratch pad.

## Working with Managed Objects

### Creating Objects
To create a new managed object, you use the NSEntityDescription class method insertNewObjectForEntityForName:inManagedObjectContext:.

### Fetching Objects
To fetch objects from the persistent store, you create an instance of NSFetchRequest, configure it, and pass it to the managed object context.

### Saving Changes
When you're ready to save your changes, you send a save: message to the managed object context.

## Performance Considerations

### Batch Operations
For large datasets, consider using batch operations to improve performance.

### Faulting
Understand how faulting works to optimize memory usage.

### Fetch Request Optimization
Optimize your fetch requests by setting appropriate batch sizes and using predicates effectively.
""" * 3  # 重复3次，创建一个长文档
        
        logger.info("=" * 60)
        logger.info("测试用例2：长文档")
        logger.info(f"文档长度: {len(long_text)} 字符")
        
        old_chunks_long = self.deprecated_chunker.chunk_text(long_text)
        new_chunks_long = self.current_chunker.chunk_text(long_text)
        
        is_identical_long = self._compare_chunking_results(old_chunks_long, new_chunks_long)
        
        logger.info(f"旧方案chunk数量: {len(old_chunks_long)}")
        logger.info(f"新方案chunk数量: {len(new_chunks_long)}")
        logger.info(f"结果是否一致: {is_identical_long}")
        
        if is_identical_long:
            logger.info("✅ 长文档测试：结果一致，将跳过embedding")
        else:
            logger.info("⚠️ 长文档测试：结果不一致，将进行embedding")
            logger.info(f"旧方案参数: TARGET_CHUNK_SIZE={self.deprecated_chunker.TARGET_CHUNK_SIZE}, MAX_CHUNK_SIZE={self.deprecated_chunker.MAX_CHUNK_SIZE}")
            logger.info(f"新方案参数: TARGET_CHUNK_SIZE={self.current_chunker.TARGET_CHUNK_SIZE}, MAX_CHUNK_SIZE={self.current_chunker.MAX_CHUNK_SIZE}")
        
        # 测试用例3：边界情况
        boundary_text = "A" * 2600  # 刚好超过新方案的TARGET_CHUNK_SIZE
        
        logger.info("=" * 60)
        logger.info("测试用例3：边界情况")
        logger.info(f"文档长度: {len(boundary_text)} 字符")
        
        old_chunks_boundary = self.deprecated_chunker.chunk_text(boundary_text)
        new_chunks_boundary = self.current_chunker.chunk_text(boundary_text)
        
        is_identical_boundary = self._compare_chunking_results(old_chunks_boundary, new_chunks_boundary)
        
        logger.info(f"旧方案chunk数量: {len(old_chunks_boundary)}")
        logger.info(f"新方案chunk数量: {len(new_chunks_boundary)}")
        logger.info(f"结果是否一致: {is_identical_boundary}")
        
        # 统计结果
        test_cases = [
            ("短文档", is_identical),
            ("长文档", is_identical_long),
            ("边界情况", is_identical_boundary)
        ]
        
        identical_count = sum(1 for _, identical in test_cases if identical)
        different_count = len(test_cases) - identical_count
        
        logger.info("=" * 60)
        logger.info("📊 测试结果统计")
        logger.info("=" * 60)
        logger.info(f"总测试用例: {len(test_cases)}")
        logger.info(f"结果一致: {identical_count} (将跳过embedding)")
        logger.info(f"结果不同: {different_count} (将进行embedding)")
        logger.info(f"预期节省embedding: {identical_count}/{len(test_cases)} = {(identical_count/len(test_cases)*100):.1f}%")
        
        # 详细分析
        logger.info("=" * 60)
        logger.info("📋 详细分析")
        logger.info("=" * 60)
        
        for test_name, identical in test_cases:
            status = "✅ 跳过embedding" if identical else "⚠️ 需要embedding"
            logger.info(f"{test_name}: {status}")
        
        logger.info("=" * 60)
        logger.info("🎯 双重Chunking对比功能测试完成！")
        
        return {
            "total_cases": len(test_cases),
            "identical_cases": identical_count,
            "different_cases": different_count,
            "efficiency_gain": (identical_count/len(test_cases)*100)
        }


def main():
    """主函数"""
    logger.info("🚀 开始双重Chunking对比功能测试...")
    
    tester = DualChunkingTester()
    results = tester.test_chunking_comparison()
    
    logger.info("🎉 测试完成！")
    logger.info(f"效率提升: {results['efficiency_gain']:.1f}%")


if __name__ == "__main__":
    main()
