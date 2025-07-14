"""
Independent Crawler Core
独立爬虫核心模块

Complete standalone crawling functionality with no MCP dependencies.
完全独立的爬虫功能，无MCP依赖。
"""

import os
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
        self.crawled_urls: set = set()  # 内存中的已爬取URL集合
        
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

        # 预加载已爬取的URL到内存
        await self._preload_crawled_urls()
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

    async def _preload_crawled_urls(self) -> None:
        """预加载所有已爬取的URL到内存集合"""
        logger.info("Preloading crawled URLs from database")
        crawled_urls = await self.db_operations.get_all_chunk_urls()
        self.crawled_urls = set(url_record['url'] for url_record in crawled_urls)
        logger.info(f"Preloaded {len(self.crawled_urls)} crawled URLs")

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

    async def smart_crawl_url(self, url: str) -> Dict[str, Any]:
        """Apple文档专用爬取 - 流式实时处理"""
        if not self.crawler or not self.db_operations:
            raise RuntimeError("Crawler not initialized. Use async with statement.")

        if not url.startswith(self.APPLE_DOCS_URL_PREFIX):
            return {"success": False, "url": url, "error": "Only Apple documentation URLs are supported"}

        logger.info(f"Starting streaming crawl for URL: {url}")
        try:
            # 流式递归爬取：每个页面立即处理，不等待批量
            stats = await self._crawl_recursive_streaming([url], int(os.getenv('MAX_DEPTH', '3')))

            logger.info(f"Streaming crawl completed for URL: {url}")
            return {
                "success": True,
                "crawl_type": "apple_streaming",
                "total_pages": stats["pages_processed"],
                "total_chunks": stats["chunks_stored"]
            }

        except Exception as e:
            logger.error(f"Crawl failed for URL {url}: {e}")
            return {"success": False, "url": url, "error": str(e)}

    async def _process_and_store_content(self, url: str, markdown: str) -> Dict[str, Any]:
        """Process and store single page content"""
        # Store page information first
        await self.db_operations.upsert_page(url, markdown)

        chunks = self.chunker.chunk_text_simple(markdown)

        if not chunks:
            return {
                "success": False,
                "url": url,
                "error": "No content to store after chunking"
            }

        # GPU内存监控：embedding前
        self.log_gpu_memory("before embedding")

        # Generate embeddings for each chunk individually
        data_to_insert = []
        for chunk in chunks:
            embedding = create_embedding(chunk)
            data_to_insert.append({
                "url": url,
                "content": chunk,
                "embedding": str(embedding)
            })

        # GPU内存监控：embedding后
        self.log_gpu_memory("after embedding")

        await self.db_operations.insert_chunks(data_to_insert)

        return {
            "success": True,
            "url": url,
            "chunks_stored": len(chunks),
            "total_characters": len(markdown)
        }

    async def _crawl_recursive_streaming(self, start_urls: List[str], max_depth: int) -> Dict[str, int]:
        """流式递归爬取：每个页面立即处理，不等待批量"""
        if not self.crawler:
            return {"pages_processed": 0, "chunks_stored": 0}

        logger.info(f"Starting streaming recursive crawl: {len(start_urls)} URLs, max depth: {max_depth}")

        # 统计信息
        total_pages_processed = 0
        total_chunks_stored = 0
        current_urls = start_urls

        for depth in range(max_depth):
            if not current_urls:
                break

            logger.info(f"Depth {depth + 1}: Processing {len(current_urls)} URLs")

            next_level_urls = set()
            depth_pages_processed = 0

            for i, url in enumerate(current_urls, 1):
                # 添加到内存中的已爬取URL集合
                self.crawled_urls.add(url)

                # 爬取页面内容
                apple_results = await self.crawl_apple_documentation(url)

                if apple_results:
                    # 立即处理每个页面：chunk + embed + store
                    for result in apple_results:
                        process_result = await self._process_and_store_content(
                            result['url'],
                            result['markdown']
                        )

                        if process_result["success"]:
                            total_pages_processed += 1
                            total_chunks_stored += process_result["chunks_stored"]
                            depth_pages_processed += 1
                            logger.info(f"✅ Processed {result['url']}: {process_result['chunks_stored']} chunks stored")
                        else:
                            logger.warning(f"❌ Failed to process {result['url']}: {process_result.get('error', 'Unknown error')}")

                # 发现新链接（用于下一层递归）
                links = await self._extract_apple_links(url)
                self._add_apple_links_to_queue(links, next_level_urls)

                logger.info(f"Depth {depth + 1}: Completed {i}/{len(current_urls)} URLs")

            current_urls = list(next_level_urls)
            logger.info(f"Depth {depth + 1} completed: {depth_pages_processed} pages processed, {len(next_level_urls)} new URLs discovered")

        logger.info(f"Streaming crawl completed: {total_pages_processed} pages, {total_chunks_stored} chunks")
        return {"pages_processed": total_pages_processed, "chunks_stored": total_chunks_stored}

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

    def _add_apple_links_to_queue(self, links: List[str], next_level_urls: set):
        """添加Apple文档链接到下一级爬取队列 - 严格过滤和清洗"""
        initial_count = len(next_level_urls)
        for link in links:
            # 先清洗和标准化URL
            cleaned_link = self.clean_and_normalize_url(link)

            # 严格检查是否为Apple文档URL
            if not cleaned_link.startswith(self.APPLE_DOCS_URL_PREFIX):
                continue

            # 避免重复爬取
            if cleaned_link not in self.crawled_urls:
                next_level_urls.add(cleaned_link)

        added_count = len(next_level_urls) - initial_count
        logger.info(f"Added {added_count} new Apple links to queue")
