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
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self) -> None:
        """Initialize crawler and database connections"""
        # Initialize PostgreSQL client
        self.db_client = await get_database_client()
        self.db_operations = DatabaseOperations(self.db_client)

        # Initialize crawler
        self.crawler = AsyncWebCrawler(verbose=False)
        await self.crawler.start()

    async def cleanup(self) -> None:
        """Clean up resources"""
        if self.crawler:
            await self.crawler.close()

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
        try:
            async with AppleContentExtractor() as extractor:
                result = await extractor.extract_clean_content(url)

                if result["success"]:
                    return [{'url': url, 'markdown': result["clean_content"]}]
                else:
                    print(f"❌ Apple extraction failed for {url}: {result.get('error', 'Unknown error')}")
                    return []
        except Exception as e:
            print(f"❌ Apple extractor error for {url}: {e}")
            return []

    async def _extract_apple_links(self, url: str) -> List[str]:
        """Extract links from Apple documentation using stealth crawler"""
        try:
            from .apple_stealth_crawler import AppleStealthCrawler
            async with AppleStealthCrawler() as stealth_crawler:
                result = await stealth_crawler.extract_full_page(url)

                if result["success"] and result.get("links"):
                    return self._extract_links_from_data(result["links"])
                return []
        except Exception as e:
            print(f"❌ Apple link extraction error for {url}: {e}")
            return []

    async def smart_crawl_url(self, url: str) -> Dict[str, Any]:
        """Apple文档专用爬取 - 只处理Apple文档"""
        if not self.crawler or not self.db_operations:
            raise RuntimeError("Crawler not initialized. Use async with statement.")

        if not url.startswith(self.APPLE_DOCS_URL_PREFIX):
            return {"success": False, "url": url, "error": "Only Apple documentation URLs are supported"}

        try:
            crawl_results = await self._crawl_recursive_apple_docs([url], int(os.getenv('MAX_DEPTH', '3')))

            if not crawl_results:
                return {"success": False, "url": url, "error": "No content found"}

            return await self._process_and_store_batch(crawl_results, "apple_recursive")

        except Exception as e:
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

        visited = set()
        results = []
        current_urls = start_urls

        for _ in range(max_depth):
            if not current_urls:
                break

            # Filter unvisited URLs with strict cleaning
            urls_to_crawl = []
            for url in current_urls:
                cleaned_url = self.clean_and_normalize_url(url)

                # 严格检查是否为Apple文档URL
                if not cleaned_url.startswith(self.APPLE_DOCS_URL_PREFIX):
                    continue

                if cleaned_url in visited:
                    continue
                if self.db_operations and await self.db_operations.url_exists(cleaned_url):
                    visited.add(cleaned_url)
                    continue
                urls_to_crawl.append(cleaned_url)

            if not urls_to_crawl:
                break

            # Process Apple documentation URLs (already filtered)
            next_level_urls = set()
            for url in urls_to_crawl:
                visited.add(url)

                # Apple documentation: dual approach for quality + completeness
                apple_results = await self.crawl_apple_documentation(url)
                if apple_results:
                    results.extend(apple_results)

                # Get complete page for link discovery using Apple stealth crawler
                links = await self._extract_apple_links(url)
                self._add_apple_links_to_queue(links, visited, next_level_urls)

            current_urls = list(next_level_urls)

        return results



    def _extract_links_from_data(self, links_data) -> List[str]:
        """Extract all internal links from crawl results"""
        if not links_data or not links_data.get("internal"):
            return []

        extracted_links = []
        for link in links_data["internal"]:
            # crawl4ai已确保link是dict且包含href
            extracted_links.append(link["href"])

        return list(set(extracted_links))  # Remove duplicates

    def _add_apple_links_to_queue(self, links: List[str], visited: set, next_level_urls: set):
        """添加Apple文档链接到下一级爬取队列 - 严格过滤和清洗"""
        for link in links:
            # 先清洗和标准化URL
            cleaned_link = self.clean_and_normalize_url(link)

            # 严格检查是否为Apple文档URL
            if not cleaned_link.startswith(self.APPLE_DOCS_URL_PREFIX):
                continue

            # 避免重复爬取
            if cleaned_link not in visited:
                next_level_urls.add(cleaned_link)
