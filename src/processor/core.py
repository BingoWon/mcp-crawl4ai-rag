"""
Processor - 智能批量Embedding处理器

三层参数设计 + 动态API限制处理

核心特性：
- 三个独立并发进程：内容供应、块处理、批管理
- 动态二分法：自适应API限制，单chunk过大时跳过
- 智能流量控制：buffer限制防止内存溢出
- 批量存储：删除+插入优化

环境变量：
- PROCESSOR_CONTENT_FETCH_SIZE: 主参数，其他自动计算 (默认50)
"""

import sys
import os
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import create_database_client, DatabaseOperations
from chunking import SmartChunker
from embedding import create_embedding, get_embedder
from embedding.providers import SiliconFlowProvider
from utils.logger import setup_logger

logger = setup_logger(__name__)


class Processor:
    """跨URL批量Embedding处理器"""

    # 系统常量
    BUFFER_CHECK_INTERVAL = 1.0
    NO_CONTENT_SLEEP_INTERVAL = 3
    MIN_CHUNK_LENGTH = 64

    def __init__(self):
        # 三层参数设计：主参数 + 自动计算
        self.content_fetch_size = int(os.getenv("PROCESSOR_CONTENT_FETCH_SIZE", "50"))
        self.chunk_buffer_limit = max(4, self.content_fetch_size // 2)
        self.chunk_batch_size = max(2, self.chunk_buffer_limit // 2)

        # 核心组件
        self.db_client = None
        self.db_operations = None
        self.chunker = SmartChunker()

        # 缓冲池
        self.content_buffer: List[Tuple[str, str]] = []
        self.chunk_buffer: List[Dict[str, Any]] = []

        logger.info(f"Processor: content_fetch={self.content_fetch_size}, "
                   f"buffer_limit={self.chunk_buffer_limit}, batch={self.chunk_batch_size}")

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        await self.cleanup()

    async def initialize(self) -> None:
        """Initialize database connections"""
        logger.info("Initializing processor")
        self.db_client = create_database_client()
        await self.db_client.initialize()
        self.db_operations = DatabaseOperations(self.db_client)

    async def cleanup(self) -> None:
        """Clean up resources - 处理剩余chunks"""
        # 处理剩余的chunks
        if self.chunk_buffer:
            logger.info(f"Processing remaining {len(self.chunk_buffer)} chunks before cleanup")
            await self._execute_unified_batch()

        if self.db_client:
            await self.db_client.close()
            logger.info("Database client closed")

    async def start_processing(self) -> None:
        """启动并发处理器池 - 全局最优解"""
        logger.info("Starting processor pool")
        await self._run_processor_pool()

    async def _run_processor_pool(self) -> None:
        """处理器池架构 - 三个独立并发进程"""
        try:
            # 启动三个独立进程
            content_supplier = asyncio.create_task(self._content_supplier())
            chunk_processor = asyncio.create_task(self._chunk_processor())
            batch_manager = asyncio.create_task(self._batch_manager())

            logger.info("Processor pool started: 3 concurrent processes")

            # 所有进程并发运行
            await asyncio.gather(content_supplier, chunk_processor, batch_manager)

        except KeyboardInterrupt:
            logger.info("Processor pool interrupted by user")
        except Exception as e:
            logger.error(f"Processor pool error: {e}")
            raise

    async def _content_supplier(self) -> None:
        """内容供应器 - 独立进程，50%阈值触发补充"""
        while True:
            try:
                # 50%阈值策略：低于50%才请求下一批
                if len(self.content_buffer) < self.content_fetch_size // 2:
                    batch_results = await self.db_operations.get_process_urls_batch(self.content_fetch_size)
                    if batch_results:
                        self.content_buffer.extend(batch_results)
                        logger.debug(f"Content supplier: added {len(batch_results)} items")

                await asyncio.sleep(self.BUFFER_CHECK_INTERVAL)

            except Exception as e:
                logger.error(f"Content supplier error: {e}")
                await asyncio.sleep(self.NO_CONTENT_SLEEP_INTERVAL)

    async def _chunk_processor(self) -> None:
        """块处理器 - 独立进程，流量控制 + 连续处理"""
        while True:
            try:
                # 流量控制：超过buffer限制时等待
                if len(self.chunk_buffer) > self.chunk_buffer_limit:
                    await asyncio.sleep(0.1)
                    continue

                if self.content_buffer:
                    url, content = self.content_buffer.pop(0)

                    if content.strip():
                        chunks = self.chunker.chunk_text(content)
                        valid_chunks = [
                            chunk for chunk in chunks
                            if chunk.strip() and len(chunk) >= self.MIN_CHUNK_LENGTH
                        ]

                        for chunk in valid_chunks:
                            self.chunk_buffer.append({"url": url, "content": chunk})

                        if valid_chunks:
                            logger.debug(f"Chunk processor: processed {len(valid_chunks)} chunks")

                    # 有内容时继续处理，不sleep
                    continue
                else:
                    # 无内容时才sleep
                    await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Chunk processor error: {e}")
                await asyncio.sleep(self.NO_CONTENT_SLEEP_INTERVAL)

    async def _batch_manager(self) -> None:
        """批处理管理器 - 独立进程，固定1秒间隔检测"""
        while True:
            try:
                if len(self.chunk_buffer) >= self.chunk_batch_size:
                    await self._execute_unified_batch()

                # 固定1秒间隔检测
                await asyncio.sleep(1.0)

            except Exception as e:
                logger.error(f"Batch manager error: {e}")
                await asyncio.sleep(self.NO_CONTENT_SLEEP_INTERVAL)

    async def _execute_unified_batch(self) -> None:
        """执行统一批处理：动态二分法处理API限制"""
        if not self.chunk_buffer:
            return

        start_time = time.perf_counter()

        # 动态二分法处理所有chunks
        all_embeddings = await self._adaptive_embedding_batch(self.chunk_buffer)

        # 准备存储数据（跳过失败的chunks）
        valid_data = []
        for i, embedding in enumerate(all_embeddings):
            if embedding is not None:  # 成功的embedding
                valid_data.append({
                    "url": self.chunk_buffer[i]["url"],
                    "content": self.chunk_buffer[i]["content"],
                    "embedding": str(embedding)
                })

        if valid_data:
            # 批量删除和插入
            urls_to_process = list(set(item["url"] for item in valid_data))
            await self.db_operations.delete_chunks_batch(urls_to_process)
            await self.db_operations.insert_chunks(valid_data)

            # 标记页面为已处理
            await self.db_operations.mark_pages_processed(urls_to_process)

        # 统计和清理
        processing_time = time.perf_counter() - start_time
        skipped_count = len(self.chunk_buffer) - len(valid_data)
        logger.info(f"📊 Batch completed: {len(valid_data)} processed, {skipped_count} skipped, {processing_time:.2f}s")

        self.chunk_buffer.clear()

    async def _adaptive_embedding_batch(self, chunk_items: List[Dict[str, Any]]) -> List[Any]:
        """动态二分法批量embedding - 自适应API限制"""
        if not chunk_items:
            return []

        embedder = get_embedder()
        if not isinstance(embedder, SiliconFlowProvider):
            # 本地embedding，逐个处理
            return [create_embedding(item["content"]) for item in chunk_items]

        # API embedding，使用动态二分法
        return await self._binary_split_embedding(embedder, chunk_items)

    async def _binary_split_embedding(self, embedder, chunk_items: List[Dict[str, Any]], depth: int = 0) -> List[Any]:
        """递归二分法处理API限制"""
        if depth > 10:  # 防止无限递归
            logger.error(f"Max recursion depth reached, skipping {len(chunk_items)} chunks")
            return [None] * len(chunk_items)

        chunk_texts = [item["content"] for item in chunk_items]

        try:
            # 尝试批量处理
            embeddings = await embedder.encode_batch_concurrent(chunk_texts)
            logger.info(f"✅ Batch embedding: {len(chunk_texts)} chunks")
            return embeddings

        except Exception as e:
            if "413" in str(e) or "Request Entity Too Large" in str(e):
                # API请求过大，进行二分
                if len(chunk_items) == 1:
                    # 单个chunk都太大，跳过
                    logger.warning(f"Single chunk too large, skipping: {len(chunk_texts[0])} chars")
                    return [None]

                # 二分处理
                mid = len(chunk_items) // 2
                logger.info(f"API limit hit, splitting {len(chunk_items)} chunks into {mid} + {len(chunk_items) - mid}")

                left_embeddings = await self._binary_split_embedding(embedder, chunk_items[:mid], depth + 1)
                right_embeddings = await self._binary_split_embedding(embedder, chunk_items[mid:], depth + 1)

                return left_embeddings + right_embeddings
            else:
                # 其他错误，跳过所有chunks
                logger.error(f"Embedding error: {e}, skipping {len(chunk_items)} chunks")
                return [None] * len(chunk_items)


async def main():
    """Main function"""
    async with Processor() as processor:
        await processor.start_processing()


if __name__ == "__main__":
    asyncio.run(main())
