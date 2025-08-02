"""
Processor - 跨URL批量Embedding处理器

实现跨URL chunks收集和批量处理。

核心机制：
- 跨URL收集chunks到chunk_buffer
- 达到阈值时批量处理
- API模式：真正的批量embedding (单次API调用)
- 本地模式：逐个embedding处理
- 批量storage (删除+插入)

环境变量：
- PROCESSOR_CONTENT_FETCH_SIZE: 内容获取批次 (默认50)
- PROCESSOR_CHUNK_BATCH_SIZE: chunks批处理阈值 (默认50)

使用方式：
    async with Processor() as processor:
        await processor.start_processing()
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
    MIN_CHUNK_LENGTH = 128

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
        """执行统一批处理：embedding + storage 一体化"""
        if not self.chunk_buffer:
            return

        start_time = time.perf_counter()

        # 1. 提取所有chunks文本
        chunk_texts = [item["content"] for item in self.chunk_buffer]

        # 2. 批量embedding处理 - 真正的跨URL批处理
        embedder = get_embedder()
        if isinstance(embedder, SiliconFlowProvider):
            embeddings = await embedder.encode_batch_concurrent(chunk_texts)
            logger.info(f"✅ True batch embedding: {len(chunk_texts)} chunks in single API call")
        else:
            embeddings = [create_embedding(chunk) for chunk in chunk_texts]
            logger.info(f"✅ Local embedding: {len(chunk_texts)} chunks processed")

        # 3. 准备批量存储数据
        all_data_to_insert = [
            {
                "url": self.chunk_buffer[i]["url"],
                "content": self.chunk_buffer[i]["content"],
                "embedding": str(embeddings[i])
            }
            for i in range(len(self.chunk_buffer))
        ]

        # 4. 获取涉及的URLs并批量删除旧chunks
        urls_to_process = list(set(item["url"] for item in self.chunk_buffer))
        await self.db_operations.delete_chunks_batch(urls_to_process)

        # 5. 批量插入新chunks
        await self.db_operations.insert_chunks(all_data_to_insert)

        # 6. 统计和清理
        processing_time = time.perf_counter() - start_time
        logger.info(f"📊 Unified batch completed: {len(urls_to_process)} URLs, "
                   f"{len(all_data_to_insert)} chunks, {processing_time:.2f}s")

        # 清空缓冲池
        self.chunk_buffer.clear()


async def main():
    """Main function"""
    async with Processor() as processor:
        await processor.start_processing()


if __name__ == "__main__":
    asyncio.run(main())
