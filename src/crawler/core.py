"""
Independent Crawler Core
独立爬虫核心模块

Complete standalone crawling functionality with no MCP dependencies.
完全独立的爬虫功能，无MCP依赖。

=== 智能链接发现设计 ===

本模块实现了基于内容状态的智能链接发现策略，提高爬取效率：

**核心优化：基于内容状态的智能链接发现决策**
- 传统方式：无条件发现和存储新链接，浪费资源
- 优化方式：根据系统状态智能决定链接发现策略
- 实现方法：_crawl_and_process_url(url, need_more_urls) 根据 need_more_urls 决定链接发现策略

**设计原理：**
1. 爬取优先级基于 crawl_count：优先爬取 crawl_count 最小的页面
2. 如果最小 crawl_count 的页面已有内容，说明所有页面都已爬取过
3. 此时需要发现新链接以扩展爬取范围 → need_more_urls = True → 双重爬取
4. 如果最小 crawl_count 的页面没有内容，说明还有未完成的爬取任务
5. 此时应优先完成现有页面的爬取 → need_more_urls = False → 单次爬取

**实现逻辑：**
- 从 get_next_crawl_url() 获取 (url, content)
- 根据 content 是否为空设置 need_more_urls 标志
- 在 _crawl_and_process_url 中根据 need_more_urls 决定链接发现策略
- need_more_urls=True: 双重爬取获得最大链接覆盖
- need_more_urls=False: 单次爬取专注现有任务

**性能收益：**
- 减少不必要的链接提取操作
- 避免在空内容页面上执行无意义的操作
- 优化爬取策略，提高系统整体效率
- 减少数据库负载和网络请求
"""

from typing import List, Optional
from crawl4ai import AsyncWebCrawler
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from embedding import create_embedding
from database import get_database_client, DatabaseOperations
from chunking import SmartChunker
from .apple_stealth_crawler import AppleStealthCrawler
from utils.logger import setup_logger
import asyncio
import torch

logger = setup_logger(__name__)


class IndependentCrawler:
    """Independent crawler that doesn't depend on MCP context"""

    # Apple文档URL常量
    APPLE_DOCS_URL_PREFIX = "https://developer.apple.com/documentation/"

    def __init__(self):
        """Initialize the independent crawler"""
        self.crawler: Optional[AsyncWebCrawler] = None
        self.db_client = None
        self.db_operations = None
        self.chunker = SmartChunker()
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self) -> None:
        """Initialize crawler and database connections"""
        logger.info("Initializing crawler and database connections")
        # Initialize PostgreSQL client
        self.db_client = await get_database_client()
        self.db_operations = DatabaseOperations(self.db_client)

        # Initialize crawler
        self.crawler = AsyncWebCrawler(verbose=False)
        await self.crawler.start()
        logger.info("Crawler initialization completed")

    async def cleanup(self) -> None:
        """Clean up resources"""
        logger.info("Cleaning up crawler resources")
        if self.crawler:
            await self.crawler.close()
        logger.info("Cleanup completed")

    def log_mps_memory(self, context: str = ""):
        """Log Apple Silicon MPS memory usage"""
        allocated = torch.mps.current_allocated_memory() / 1024**3
        logger.info(f"MPS Memory {context}: {allocated:.2f}GB allocated")


    def clean_and_normalize_url(self, url: str) -> str:
        """清洗和标准化URL - 移除锚点片段和末尾斜杠"""
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(url)

        # 清洗：移除fragment（#后面的内容）
        cleaned_parsed = parsed._replace(fragment='')

        # 标准化：移除末尾斜杠
        path = cleaned_parsed.path.rstrip('/')
        normalized_parsed = cleaned_parsed._replace(path=path)

        return urlunparse(normalized_parsed)


    async def start_infinite_crawl(self, start_url: str) -> None:
        """Start infinite crawl loop based on crawl_count priority"""
        if not self.crawler or not self.db_operations:
            raise RuntimeError("Crawler not initialized. Use async with statement.")

        if not start_url.startswith(self.APPLE_DOCS_URL_PREFIX):
            logger.error("Only Apple documentation URLs are supported")
            return

        # Insert start URL if not exists
        await self.db_operations.insert_url_if_not_exists(start_url)
        logger.info(f"Starting infinite crawl from: {start_url}")

        crawl_count = 0
        while True:
            try:
                # Get next URL and content to crawl (minimum crawl_count)
                result = await self.db_operations.get_next_crawl_url()
                if not result:
                    logger.info("No URLs to crawl")
                    break

                next_url, existing_content = result
                crawl_count += 1
                logger.info(f"=== Crawl #{crawl_count}: {next_url} ===")

                # Crawl and process the URL
                need_more_urls = bool(existing_content)  # 有内容说明需要发现更多URL
                await self._crawl_and_process_url(next_url, need_more_urls)

            except KeyboardInterrupt:
                logger.info("Crawl interrupted by user")
                break
            except Exception as e:
                logger.error(f"Crawl error: {e}")
                continue

    async def _crawl_and_process_url(self, url: str, need_more_urls: bool) -> None:
        """Crawl single URL and complete processing pipeline"""
        logger.info(f"Processing URL: {url}")

        async with AppleStealthCrawler() as crawler:
            # 1. Crawl content and links
            content = ""
            links_data = None
            for i in range(3):
                content, links_data = await crawler.extract_content_and_links(url, "#app-main")
                if content:
                    break
                if i == 2:
                    logger.error(f"No content crawled for {url}, skipping")
                    break
                else:
                    logger.error(f"No content crawled for {url}, retrying...")
                    await asyncio.sleep(1)

            # 即便没有爬到结果也要更新数据库
            # 2. Delete old chunks for this URL
            await self.db_operations.delete_chunks_by_url(url)

            # 3. Update page content and crawl_count
            await self.db_operations.update_page_after_crawl(url, content)

            # 3.1. 如果没有爬到内容，则不进行后续处理
            if not content.strip():
                logger.error(f"No content crawled for {url}, skipping chunking and embedding")
                return

            # 4. Process content: chunking + embedding + storage
            chunks = self.chunker.chunk_text(content)
            if not chunks:
                logger.error(f"No chunks generated for {url}")
                return

            self.log_mps_memory("before embedding")

            data_to_insert = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing {i+1}/{len(chunks)} chunk")
                if not chunk.strip():
                    logger.error(f"Empty chunk {i+1} for {url}, skipping embedding")
                    continue
                embedding = create_embedding(chunk)
                data_to_insert.append({
                    "url": url,
                    "content": chunk,
                    "embedding": str(embedding)
                })

            if not data_to_insert:
                logger.error(f"No data to insert for {url}")
                return

            self.log_mps_memory("after embedding")
            await self.db_operations.insert_chunks(data_to_insert)

            # 5. Process discovered links
            # Choose link source based on system needs: full page vs content area
            if need_more_urls:
                _, links_data = await crawler.extract_content_and_links(url)
            
            extracted_links = self._extract_links_from_data(links_data)

            if extracted_links:
                await self._store_discovered_links(extracted_links)

            logger.info(f"✅ Processed {url}: {len(chunks)} chunks, {len(extracted_links)} new links")

    async def _store_discovered_links(self, links: List[str]) -> None:
        """Store discovered links to database if not exists"""
        new_count = 0
        for link in links:
            clean_link = self.clean_and_normalize_url(link)
            if clean_link.startswith(self.APPLE_DOCS_URL_PREFIX):
                if await self.db_operations.insert_url_if_not_exists(clean_link):
                    new_count += 1

        if new_count > 0:
            logger.info(f"Added {new_count} new URLs to crawl queue")



    def _extract_links_from_data(self, links_data) -> List[str]:
        """Extract all internal links from crawl results"""
        if not links_data or not links_data.get("internal"):
            return []

        extracted_links = []
        for link in links_data["internal"]:
            # crawl4ai已确保link是dict且包含href
            extracted_links.append(link["href"])

        return list(set(extracted_links))  # Remove duplicates


