"""
Independent Crawler Core
独立爬虫核心模块

Complete standalone crawling functionality with no MCP dependencies.
完全独立的爬虫功能，无MCP依赖。
"""

import os
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler

# Import modules with unified style
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from embedding import create_embeddings_batch
from database import get_database_client, DatabaseOperations
from chunking import SmartChunker

# Import Apple extractor (always available)
from .apple_content_extractor import AppleContentExtractor
from .logger import logger


class IndependentCrawler:
    """Independent crawler that doesn't depend on MCP context"""

    # Apple文档URL常量
    APPLE_DOCS_URL_PREFIX = "https://developer.apple.com/documentation/"

    def __init__(self):
        """Initialize the independent crawler"""
        self.crawler: Optional[AsyncWebCrawler] = None
        self.db_client = None
        self.db_operations = None
        self.chunker = SmartChunker(int(os.getenv('CHUNK_SIZE', '5000')))
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

    async def _preload_crawled_urls(self) -> None:
        """预加载所有已爬取的URL到内存集合"""
        logger.info("Preloading crawled URLs from database")
        crawled_urls = await self.db_operations.get_all_crawled_urls()
        self.crawled_urls = set(crawled_urls)
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
        """Apple文档专用爬取 - 只处理Apple文档"""
        if not self.crawler or not self.db_operations:
            raise RuntimeError("Crawler not initialized. Use async with statement.")

        if not url.startswith(self.APPLE_DOCS_URL_PREFIX):
            return {"success": False, "url": url, "error": "Only Apple documentation URLs are supported"}

        logger.info(f"Starting crawl for URL: {url}")
        try:
            crawl_results = await self._crawl_recursive_apple_docs([url], int(os.getenv('MAX_DEPTH', '3')))

            if not crawl_results:
                return {"success": False, "url": url, "error": "No content found"}

            result = await self._process_and_store_batch(crawl_results, "apple_recursive")
            logger.info(f"Crawl completed for URL: {url}")
            return result

        except Exception as e:
            logger.error(f"Crawl failed for URL {url}: {e}")
            return {"success": False, "url": url, "error": str(e)}

    async def _process_and_store_content(self, url: str, markdown: str) -> Dict[str, Any]:
        """Process and store single page content"""
        # Generate source_id
        parsed_url = urlparse(url)
        source_id = parsed_url.netloc or parsed_url.path

        # Chunk the content
        chunks = self.chunker.chunk_text_simple(markdown)

        if not chunks:
            return {
                "success": False,
                "url": url,
                "error": "No content to store after chunking"
            }

        # Prepare data for storage
        urls = [url] * len(chunks)
        chunk_numbers = list(range(len(chunks)))
        contents = chunks
        metadatas = [{"chunk_index": i, "url": url, "source": source_id} for i in range(len(chunks))]

        # Generate embeddings
        embeddings = create_embeddings_batch(contents)

        # Store in database
        data_to_insert = []
        for i in range(len(chunks)):
            data_to_insert.append({
                "url": urls[i],
                "chunk_number": chunk_numbers[i],
                "content": contents[i],
                "metadata": metadatas[i],
                "source_id": source_id,
                "embedding": embeddings[i]
            })

        # Insert into crawled_pages table
        await self.db_operations.insert_crawled_pages(data_to_insert)

        return {
            "success": True,
            "url": url,
            "chunks_stored": len(chunks),
            "source_id": source_id,
            "total_characters": len(markdown)
        }

    async def _process_and_store_batch(self, crawl_results: List[Dict[str, Any]], crawl_type: str) -> Dict[str, Any]:
        """Process and store batch crawl results"""
        logger.info(f"Processing batch of {len(crawl_results)} crawl results")
        urls = []
        chunk_numbers = []
        contents = []
        metadatas = []
        chunk_count = 0

        for result in crawl_results:
            url = result['url']
            markdown = result['markdown']

            if not markdown:
                continue

            # Generate source_id
            parsed_url = urlparse(url)
            source_id = parsed_url.netloc or parsed_url.path

            # Chunk the content
            chunker = SmartChunker(int(os.getenv('CHUNK_SIZE', '5000')))
            chunks = chunker.chunk_text_simple(markdown)

            for i, chunk in enumerate(chunks):
                urls.append(url)
                chunk_numbers.append(i)
                contents.append(chunk)
                metadatas.append({
                    "chunk_index": i,
                    "url": url,
                    "source": source_id,
                    "crawl_type": crawl_type
                })
                chunk_count += 1

        if not contents:
            return {
                "success": False,
                "error": "No content to store after processing"
            }

        # Generate embeddings
        embeddings = create_embeddings_batch(contents)

        # Store in database
        data_to_insert = []
        for i in range(len(contents)):
            data_to_insert.append({
                "url": urls[i],
                "chunk_number": chunk_numbers[i],
                "content": contents[i],
                "metadata": metadatas[i],
                "source_id": metadatas[i]["source"],
                "embedding": embeddings[i]
            })

        # Insert into crawled_pages table
        await self.db_operations.insert_crawled_pages(data_to_insert)
        logger.info(f"Batch processing completed: {len(crawl_results)} pages, {chunk_count} chunks stored")

        return {
            "success": True,
            "crawl_type": crawl_type,
            "total_pages": len(crawl_results),
            "total_chunks": chunk_count
        }



    async def _crawl_recursive_apple_docs(self, start_urls: List[str], max_depth: int) -> List[Dict[str, Any]]:
        """Unified recursive crawling with Apple documentation integration"""
        if not self.crawler:
            return []

        logger.info(f"Starting recursive crawl: {len(start_urls)} URLs, max depth: {max_depth}")
        results = []
        current_urls = start_urls

        for depth in range(max_depth):
            if not current_urls:
                break

            # 显示当前层级的所有URL
            logger.info(f"Depth {depth + 1}: URLs to process:")
            for i, url in enumerate(current_urls, 1):
                logger.info(f"  {i}. {url}")

            if not current_urls:
                logger.info(f"Depth {depth + 1}: No URLs to process, stopping")
                break

            # Process Apple documentation URLs
            next_level_urls = set()
            crawled_count = 0
            for i, url in enumerate(current_urls, 1):
                # 添加到内存中的已爬取URL集合
                self.crawled_urls.add(url)

                # Apple documentation: dual approach for quality + completeness
                apple_results = await self.crawl_apple_documentation(url)
                if apple_results:
                    results.extend(apple_results)
                    crawled_count += 1
                logger.info(f"Depth {depth + 1}: Processed {i}/{len(current_urls)} URLs")

                # Get complete page for link discovery using Apple stealth crawler
                links = await self._extract_apple_links(url)
                self._add_apple_links_to_queue(links, next_level_urls)

            current_urls = list(next_level_urls)
            logger.info(f"Depth {depth + 1} completed: {crawled_count} URLs successfully crawled, {len(next_level_urls)} new URLs discovered")

        logger.info(f"Recursive crawl completed: {len(results)} total results")
        return results



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
