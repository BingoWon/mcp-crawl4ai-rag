"""
Pure Processor Core
纯处理器核心模块

专注于内容处理的独立组件，是统一爬虫系统的处理引擎。

=== 统一爬虫系统架构 ===

本模块是统一爬虫系统的核心组件之一，与爬取器组件协同工作：

**系统架构：**
- 统一入口：tools/continuous_crawler.py 并发运行爬取器和处理器
- 职责分离：爬取器专注爬取，处理器专注分块嵌入
- 数据库协调：通过 crawl_count 和 process_count 实现智能调度

**处理器职责：**
- 从 pages 表读取已爬取的页面内容
- 智能分块处理（H1/H2/H3分层策略）
- 向量嵌入生成（Qwen3-Embedding-4B）
- chunks 数据存储和 process_count 管理

=== 处理流程设计 ===

**优先级调度：**
- 基于 process_count 最小值优先处理
- 确保所有页面得到均衡处理
- 自动平衡系统负载

**处理流程：**
1. 获取最小 process_count 的页面内容
2. 删除该URL的所有旧chunks（确保数据一致性）
3. 智能分块：使用SmartChunker的分层策略
4. 向量嵌入：为每个chunk生成2560维嵌入向量
5. 数据存储：插入新chunks并更新process_count

**容错机制：**
- 空内容页面跳过处理但更新计数
- 分块失败时记录错误但继续处理
- 嵌入失败时跳过该chunk但不中断流程
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_database_client, DatabaseOperations
from chunking import SmartChunker
from embedding import create_embedding, get_embedder
from embedding.providers import SiliconFlowProvider
from utils.logger import setup_logger
import asyncio
import os

logger = setup_logger(__name__)


class ContentProcessor:
    """内容处理器，专注于分块和嵌入处理"""

    def __init__(self):
        self.db_client = None
        self.db_operations = None
        self.chunker = SmartChunker()

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    async def initialize(self) -> None:
        """Initialize database connections"""
        logger.info("Initializing pure processor")
        self.db_client = await get_database_client()
        self.db_operations = DatabaseOperations(self.db_client)

    async def cleanup(self) -> None:
        """Clean up resources"""
        logger.info("Cleaning up processor resources")

    async def start_processing(self) -> None:
        """批量内容处理循环 - 全局最优解"""
        batch_size = int(os.getenv("PROCESSOR_BATCH_SIZE", "5"))
        logger.info(f"🚀 Starting batch processor (batch_size={batch_size})")

        process_count = 0
        while True:
            try:
                # 批量获取待处理的URL和内容
                batch_results = await self.db_operations.get_process_urls_batch(batch_size)

                if not batch_results:
                    logger.info("No URLs to process")
                    await asyncio.sleep(3)
                    continue

                logger.info(f"=== Processing batch of {len(batch_results)} URLs ===")

                # 批量处理所有URL（租约已在获取时建立）
                processed_count = 0
                for url, content in batch_results:
                    process_count += 1
                    logger.info(f"Process #{process_count}: {url}")

                    try:
                        await self._process_content(url, content)
                        processed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to process {url}: {e}")
                        continue

                logger.info(f"✅ Batch completed: {processed_count}/{len(batch_results)} URLs processed")

            except KeyboardInterrupt:
                logger.info("Processor interrupted by user")
                break
            except Exception as e:
                logger.error(f"Batch process error: {e}")
                continue

    async def _process_content(self, url: str, content: str) -> None:
        """处理页面内容：分块 + 嵌入 + 存储 - 全局最优解"""
        logger.info(f"Processing content for: {url}")

        # Skip if no content
        if not content.strip():
            logger.error(f"❌ No content to process for {url}")
            await self.db_operations.update_process_count(url)
            return

        # Delete old chunks and process content
        await self.db_operations.delete_chunks_by_url(url)
        chunks = self.chunker.chunk_text(content)

        if not chunks:
            logger.error(f"❌ No chunks generated for {url}")
            await self.db_operations.update_process_count(url)
            return

        # Process chunks with embedding - 智能策略选择
        data_to_insert = []
        valid_chunks = [chunk for chunk in chunks if chunk.strip()]

        if not valid_chunks:
            logger.error(f"❌ No valid chunks for {url}")
            await self.db_operations.update_process_count(url)
            return

        # 检测embedding provider类型并选择处理策略
        embedder = get_embedder()

        if isinstance(embedder, SiliconFlowProvider):
            # API模式：批量并发处理
            logger.info(f"API mode: batch processing {len(valid_chunks)} chunks")
            embeddings = await embedder.encode_batch_concurrent(valid_chunks)

            for i, (chunk, embedding) in enumerate(zip(valid_chunks, embeddings)):
                if len(chunk) < 128:
                    logger.error(f"⚠️ Chunk {i+1} 长度过短: {len(chunk)} 字符")
                data_to_insert.append({
                    "url": url,
                    "content": chunk,
                    "embedding": str(embedding)
                })
        else:
            # 本地模式：严格单个处理
            logger.info(f"Local mode: sequential processing {len(valid_chunks)} chunks")
            for i, chunk in enumerate(valid_chunks):
                if len(chunk) < 128:
                    logger.error(f"⚠️ Chunk {i+1} 长度过短: {len(chunk)} 字符")

                logger.info(f"Processing chunk {i+1}/{len(valid_chunks)}, length: {len(chunk)}")
                embedding = create_embedding(chunk)
                data_to_insert.append({
                    "url": url,
                    "content": chunk,
                    "embedding": str(embedding)
                })

        if not data_to_insert:
            logger.error(f"❌ No data to insert for {url}")
            return

        # Insert chunks (process_count will be updated in batch)
        await self.db_operations.insert_chunks(data_to_insert)
        logger.info(f"✅ Processed {url}: {len(data_to_insert)} chunks created")


async def main():
    """Main function for direct execution"""
    logger.info("🚀 Pure Processor Starting")

    try:
        async with ContentProcessor() as processor:
            await processor.start_processing()
    except KeyboardInterrupt:
        logger.info("Processor interrupted by user")
    except Exception as e:
        logger.error(f"Processor error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Processor interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import sys
        sys.exit(1)
