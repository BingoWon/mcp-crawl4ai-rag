"""
Independent Crawler Core
独立爬虫核心模块

Complete standalone crawling functionality with no MCP dependencies.
完全独立的爬虫功能，无MCP依赖。
"""

from typing import List, Dict, Any, Optional

from crawl4ai import AsyncWebCrawler

# Import modules with unified style
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from embedding import create_embedding
from database import get_database_client, DatabaseOperations
from chunking import SmartChunker

# Import Apple extractor (always available)
from .apple_content_extractor import AppleContentExtractor
from utils.logger import setup_logger

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

    def log_gpu_memory(self, context: str = ""):
        """Log current GPU memory usage for optimization monitoring"""
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            cached = torch.cuda.memory_reserved() / 1024**3
            logger.info(f"GPU Memory {context}: {allocated:.2f}GB allocated, {cached:.2f}GB cached")



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

    async def crawl_apple_documentation(self, url: str) -> List[Dict[str, Any]]:
        """Crawl Apple documentation using specialized extractor"""
        logger.info(f"Crawling Apple documentation: {url}")
        try:
            async with AppleContentExtractor() as extractor:
                clean_content = await extractor.extract_clean_content(url)
                result = [{'url': url, 'markdown': clean_content}] if clean_content else []
                logger.info(f"Apple documentation crawl completed: {url}")
                return result
        except Exception as e:
            logger.error(f"Apple extractor error for {url}: {e}")
            return []

    async def _extract_apple_links(self, url: str) -> List[str]:
        """Extract links from Apple documentation using stealth crawler"""
        try:
            from .apple_stealth_crawler import AppleStealthCrawler
            async with AppleStealthCrawler() as stealth_crawler:
                links = await stealth_crawler.extract_links(url)
                return self._extract_links_from_data(links) if links else []
        except Exception as e:
            logger.error(f"Apple link extraction error for {url}: {e}")
            return []

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
                # Get next URL to crawl (minimum crawl_count)
                next_url = await self.db_operations.get_next_crawl_url()
                if not next_url:
                    logger.info("No URLs to crawl")
                    break

                crawl_count += 1
                logger.info(f"=== Crawl #{crawl_count}: {next_url} ===")

                # Crawl and process the URL
                await self._crawl_and_process_url(next_url)

            except KeyboardInterrupt:
                logger.info("Crawl interrupted by user")
                break
            except Exception as e:
                logger.error(f"Crawl error: {e}")
                continue

    async def _crawl_and_process_url(self, url: str) -> None:
        """Crawl single URL and complete processing pipeline"""
        logger.info(f"Processing URL: {url}")

        # 1. Crawl content
        apple_results = await self.crawl_apple_documentation(url)

        # 即便没有爬到结果也要更新数据库
        content = ""
        if apple_results:
            content = apple_results[0]['markdown']

            # 2. Delete old chunks for this URL
            await self.db_operations.delete_chunks_by_url(url)

        # 3. Update page content and crawl_count
        await self.db_operations.update_page_after_crawl(url, content)

        # 3.1. 如果没有爬到内容，则不进行后续处理
        if not content:
            logger.info(f"No content crawled for {url}, skipping chunking and embedding")
            return

        # 4. Process content: chunking + embedding + storage
        chunks = self.chunker.chunk_text_simple(content)
        if not chunks:
            logger.warning(f"No chunks generated for {url}")
            return

        self.log_gpu_memory("before embedding")

        data_to_insert = []
        for chunk in chunks:
            embedding = create_embedding(chunk)
            data_to_insert.append({
                "url": url,
                "content": chunk,
                "embedding": str(embedding)
            })

        self.log_gpu_memory("after embedding")
        await self.db_operations.insert_chunks(data_to_insert)

        # 5. Discover and store new links
        links = await self._extract_apple_links(url)
        await self._store_discovered_links(links)

        logger.info(f"✅ Processed {url}: {len(chunks)} chunks, {len(links)} new links")

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

        logger.info(f"Extracted {len(extracted_links)} internal links")
        return list(set(extracted_links))  # Remove duplicates


