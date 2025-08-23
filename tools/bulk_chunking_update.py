#!/usr/bin/env python3
"""
批量Chunking更新工具

功能：
- 对全部pages表进行chunking更新处理
- 使用双重chunking对比机制（旧方案 vs 新方案）
- 只有结果不一致时才删除chunks表旧数据并重新存储
- 结果一致时完全跳过，不操作chunks表

核心逻辑：
1. 获取所有pages表记录
2. 对每个page进行双重chunking
3. 对比结果是否一致
4. 只有不一致时才更新chunks表
5. 显示详细的处理进度和统计信息
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.database import create_database_client, DatabaseOperations
from src.chunking import SmartChunker
from src.chunking_deprecated.chunker import SmartChunker as DeprecatedChunker
from src.embedding import get_embedder
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BulkChunkingUpdater:
    """批量Chunking更新器"""

    def __init__(self):
        # 超参数配置
        self.batch_size = int(os.getenv("BULK_UPDATE_BATCH_SIZE", "500"))

        # 核心组件
        self.db_client = None
        self.db_operations = None
        self.current_chunker = SmartChunker()  # 新方案 (2500/3000)
        self.deprecated_chunker = DeprecatedChunker()  # 旧方案 (5000/6000)

        # 统计信息
        self.stats = {
            "total_pages": 0,
            "processed_pages": 0,
            "identical_results": 0,
            "different_results": 0,
            "chunks_updated": 0,
            "chunks_skipped": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        await self.cleanup()

    async def initialize(self):
        """初始化数据库连接"""
        logger.info(f"🔗 初始化批量Chunking更新器 | 批次大小: {self.batch_size}")
        self.db_client = create_database_client()
        await self.db_client.initialize()
        self.db_operations = DatabaseOperations(self.db_client)
        logger.info("✅ 数据库连接成功")

    async def cleanup(self):
        """清理资源"""
        if self.db_client:
            await self.db_client.close()
            logger.info("🔒 数据库连接已关闭")

    def _compare_chunking_results(self, old_chunks: List[str], new_chunks: List[str]) -> bool:
        """对比两个chunking结果是否一致"""
        # 1. 数量对比
        if len(old_chunks) != len(new_chunks):
            return False
        
        # 2. 内容对比：逐个比较chunk内容
        for old_chunk, new_chunk in zip(old_chunks, new_chunks):
            if old_chunk != new_chunk:
                return False
        
        return True

    async def get_total_apple_pages_count(self) -> int:
        """获取Apple文档总数（用于进度计算）"""
        result = await self.db_client.fetch_one("""
            SELECT COUNT(*) as count FROM pages
            WHERE content IS NOT NULL
            AND content != ''
            AND (url = 'https://developer.apple.com/documentation'
                 OR url LIKE 'https://developer.apple.com/documentation/%')
        """)
        return result['count']

    async def process_single_page(self, url: str, content: str) -> Dict[str, Any]:
        """处理单个页面的chunking更新"""
        try:
            # 双重chunking
            old_chunks = self.deprecated_chunker.chunk_text(content)
            new_chunks = self.current_chunker.chunk_text(content)
            
            # 智能对比
            is_identical = self._compare_chunking_results(old_chunks, new_chunks)
            
            result = {
                "url": url,
                "old_chunk_count": len(old_chunks),
                "new_chunk_count": len(new_chunks),
                "is_identical": is_identical,
                "chunks_processed": 0,
                "error": None
            }
            
            if is_identical:
                # 结果一致，跳过chunks表操作
                self.stats["identical_results"] += 1
                self.stats["chunks_skipped"] += len(new_chunks)
                logger.debug(f"✅ {url}: 结果一致，跳过更新")
            else:
                # 结果不一致，需要更新chunks表
                self.stats["different_results"] += 1
                
                # 删除旧chunks
                await self.db_operations.delete_chunks_batch([url])
                
                # 生成新chunks的embedding并存储
                chunks_data = await self._process_chunks_with_embedding(url, new_chunks)
                
                if chunks_data:
                    await self.db_operations.insert_chunks(chunks_data)
                    result["chunks_processed"] = len(chunks_data)
                    self.stats["chunks_updated"] += len(chunks_data)
                    logger.debug(f"🔄 {url}: 更新了 {len(chunks_data)} 个chunks")
                
                # 注意：不在这里标记为已处理，而是在批次级别统一标记
            
            return result
            
        except Exception as e:
            self.stats["errors"] += 1
            error_msg = f"处理页面失败: {e}"
            logger.error(f"❌ {url}: {error_msg}")
            return {
                "url": url,
                "old_chunk_count": 0,
                "new_chunk_count": 0,
                "is_identical": False,
                "chunks_processed": 0,
                "error": error_msg
            }

    async def _process_chunks_with_embedding(self, url: str, chunks: List[str]) -> List[Dict[str, Any]]:
        """为chunks生成embedding并准备存储数据"""
        valid_chunks = [chunk for chunk in chunks if chunk.strip()]

        if not valid_chunks:
            return []

        # 生成embeddings（只使用API）
        embeddings = await self._generate_embeddings(valid_chunks)

        # 准备存储数据
        chunks_data = []
        for i, embedding in enumerate(embeddings):
            if embedding is not None:  # 成功的embedding
                chunks_data.append({
                    "url": url,
                    "content": valid_chunks[i],
                    "embedding": str(embedding)
                })

        return chunks_data

    async def _generate_embeddings(self, chunks: List[str]) -> List[Any]:
        """生成embeddings（只使用API批量处理）"""
        embedder = get_embedder()

        # 只使用API embedding，批量处理
        try:
            return await embedder.encode_batch_concurrent(chunks)
        except Exception as e:
            logger.warning(f"批量embedding失败，改为逐个处理: {e}")
            # 降级为逐个处理
            embeddings = []
            for chunk in chunks:
                try:
                    embedding = await embedder.encode_batch_concurrent([chunk])
                    embeddings.append(embedding[0] if embedding else None)
                except Exception as chunk_e:
                    logger.error(f"单个chunk embedding失败: {chunk_e}")
                    embeddings.append(None)
            return embeddings

    async def run_bulk_update(self):
        """执行批量更新"""
        logger.info("🚀 开始批量Chunking更新...")
        self.stats["start_time"] = time.time()

        # 获取Apple文档总数（用于进度计算）
        total_count = await self.get_total_apple_pages_count()
        self.stats["total_pages"] = total_count

        if total_count == 0:
            logger.warning("⚠️ 没有找到Apple文档")
            return

        logger.info(f"📊 开始分批处理，总计 {total_count} 个Apple文档，批次大小: {self.batch_size}")
        logger.info("💡 注意：只有chunking结果不一致的页面才会被处理")
        logger.info("=" * 80)

        # 分批处理：使用现有的get_process_urls_batch()方法（方案B）
        processed_count = 0
        while True:
            # 获取一批待处理的页面
            batch = await self.db_operations.get_process_urls_batch(self.batch_size)
            if not batch:
                break  # 没有更多数据

            batch_results = []
            batch_urls = [url for url, _ in batch]

            try:
                # 并发处理当前批次
                tasks = [self.process_single_page(url, content) for url, content in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # 更新统计
                for result in batch_results:
                    if isinstance(result, Exception):
                        self.stats["errors"] += 1
                        logger.error(f"❌ 批次处理异常: {result}")
                    else:
                        self.stats["processed_pages"] += 1

                # 🔥 关键修复：批次级别标记为已处理（无论是否有错误）
                await self.db_operations.mark_pages_processed(batch_urls)

            except Exception as e:
                # 批次级别的错误处理
                self.stats["errors"] += len(batch)
                logger.error(f"❌ 整个批次处理失败: {e}")

                # 即使批次失败，也要标记为已处理，避免重复处理
                await self.db_operations.mark_pages_processed(batch_urls)

            processed_count += len(batch)

            # 显示进度和统计（整合为一行）
            progress = (processed_count / total_count * 100) if total_count > 0 else 0
            processed = self.stats["processed_pages"]
            identical = self.stats["identical_results"]
            identical_pct = (identical / processed * 100) if processed > 0 else 0
            logger.info(f"📈 进度: {progress:.1f}% ({processed_count}/{total_count}) | 一致: {identical} ({identical_pct:.1f}%) | 错误: {self.stats['errors']}")
        
        self.stats["end_time"] = time.time()
        self._log_final_stats()

    def _log_final_stats(self):
        """显示最终统计信息"""
        duration = self.stats["end_time"] - self.stats["start_time"]
        total = self.stats["total_pages"]
        processed = self.stats["processed_pages"]
        identical = self.stats["identical_results"]
        different = self.stats["different_results"]
        updated = self.stats["chunks_updated"]
        skipped = self.stats["chunks_skipped"]
        errors = self.stats["errors"]
        
        logger.info("=" * 80)
        logger.info("🎯 批量Chunking更新完成！")
        logger.info("=" * 80)
        logger.info(f"⏱️  总耗时: {duration:.2f} 秒")
        logger.info(f"📄 总页面数: {total}")
        logger.info(f"✅ 成功处理: {processed}")
        logger.info(f"❌ 处理失败: {errors}")
        logger.info("")
        logger.info("📊 Chunking对比结果:")
        logger.info(f"   🟢 结果一致: {identical} ({(identical/processed*100):.1f}%)")
        logger.info(f"   🟡 结果不同: {different} ({(different/processed*100):.1f}%)")
        logger.info("")
        logger.info("💾 Chunks表操作:")
        logger.info(f"   🔄 更新chunks: {updated}")
        logger.info(f"   ⏭️  跳过chunks: {skipped}")
        logger.info(f"   💰 节省embedding: {skipped} ({(skipped/(updated+skipped)*100):.1f}%)")
        logger.info("=" * 80)


async def main():
    """主函数"""
    logger.info("🎯 批量Chunking更新工具")
    logger.info("功能: 对全部pages表进行智能chunking更新")
    logger.info("策略: 只有结果不一致时才更新chunks表")
    logger.info("")
    
    async with BulkChunkingUpdater() as updater:
        await updater.run_bulk_update()
    
    logger.info("🎉 批量更新任务完成！")


if __name__ == "__main__":
    asyncio.run(main())
