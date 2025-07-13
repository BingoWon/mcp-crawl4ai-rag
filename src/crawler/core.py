"""
Independent Crawler Core
独立爬虫核心模块

Complete standalone crawling functionality with no MCP dependencies.
完全独立的爬虫功能，无MCP依赖。
"""

from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from xml.etree import ElementTree
import requests
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

from .config import CrawlerConfig

# Import modules with unified style
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from embedding import create_embeddings_batch
from database import get_database_client, DatabaseOperations
from chunking import SmartChunker

# Import Apple extractor
try:
    from .apple_content_extractor import AppleContentExtractor
    APPLE_EXTRACTOR_AVAILABLE = True
except ImportError:
    APPLE_EXTRACTOR_AVAILABLE = False
    print("⚠️  Apple content extractor not available")


class IndependentCrawler:
    """Independent crawler that doesn't depend on MCP context"""

    def __init__(self, config: CrawlerConfig):
        """Initialize the independent crawler"""
        self.config = config
        self.crawler: Optional[AsyncWebCrawler] = None
        self.db_client = None
        self.db_operations = None
        self.chunker = SmartChunker(config.chunk_size)
        
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

    def is_apple_documentation(self, url: str) -> bool:
        """Check if URL is Apple developer documentation"""
        return 'developer.apple.com/documentation/' in url

    def is_sitemap(self, url: str) -> bool:
        """Check if URL is a sitemap"""
        return url.endswith('sitemap.xml') or 'sitemap' in urlparse(url).path

    def is_txt(self, url: str) -> bool:
        """Check if URL is a text file"""
        return url.endswith('.txt')



    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and trailing slashes."""
        from urllib.parse import urldefrag
        normalized, _ = urldefrag(url)
        return normalized.rstrip('/')



    async def crawl_apple_documentation(self, url: str) -> List[Dict[str, Any]]:
        """Crawl Apple documentation using specialized extractor"""
        if not APPLE_EXTRACTOR_AVAILABLE:
            print(f"⚠️  Apple extractor not available, falling back to standard crawling for {url}")
            return []

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

    def parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Parse sitemap and extract URLs"""
        resp = requests.get(sitemap_url)
        urls = []

        if resp.status_code == 200:
            try:
                tree = ElementTree.fromstring(resp.content)
                urls = [loc.text for loc in tree.findall('.//{*}loc')]
            except Exception as e:
                print(f"Error parsing sitemap XML: {e}")

        return urls

    async def crawl_markdown_file(self, url: str) -> List[Dict[str, Any]]:
        """Crawl a markdown/text file"""
        if not self.crawler:
            return []

        try:
            crawl_config = CrawlerRunConfig()
            result = await self.crawler.arun(url=url, config=crawl_config)
            if result.success and result.markdown:
                return [{'url': url, 'markdown': result.markdown}]
            else:
                print(f"Failed to crawl {url}: {result.error_message}")
                return []
        except Exception as e:
            print(f"❌ Error fetching {url}: {e}")
            return []

    async def crawl_batch(self, urls: List[str], max_concurrent: int = 10) -> List[Dict[str, Any]]:
        """Batch crawl multiple URLs in parallel"""
        if not self.crawler:
            return []

        crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=False)

        results = await self.crawler.arun_many(urls=urls, config=crawl_config)
        return [{'url': r.url, 'markdown': r.markdown} for r in results if r.success and r.markdown]
        
    async def crawl_single_page(self, url: str) -> Dict[str, Any]:
        """Crawl a single web page"""
        if not self.crawler or not self.db_operations:
            raise RuntimeError("Crawler not initialized. Use async with statement.")
            
        try:
            # Use intelligent URL routing
            if self.is_apple_documentation(url):
                # For Apple documentation, use specialized extractor
                apple_results = await self.crawl_apple_documentation(url)
                if apple_results:
                    result_data = apple_results[0]
                    # Simulate crawler result structure
                    class MockResult:
                        def __init__(self, success, markdown):
                            self.success = success
                            self.markdown = markdown
                    result = MockResult(True, result_data['markdown'])
                else:
                    result = MockResult(False, None)
            else:
                # Configure crawl for standard pages
                run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=False)
                # Crawl the page
                result = await self.crawler.arun(url=url, config=run_config)
                
            if not result.success:
                return {
                    "success": False,
                    "url": url,
                    "error": "Failed to crawl the page"
                }
                
            # Process and store content (implementation continues in next part)
            return await self._process_and_store_content(url, result.markdown)
            
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }
            
    async def smart_crawl_url(self, url: str, max_depth: int = None, max_concurrent: int = None, chunk_size: int = None) -> Dict[str, Any]:
        """Intelligently crawl URL based on its type"""
        if not self.crawler or not self.db_operations:
            raise RuntimeError("Crawler not initialized. Use async with statement.")
            
        # Use provided parameters or fall back to config defaults
        max_depth = max_depth or self.config.max_depth
        max_concurrent = max_concurrent or self.config.max_concurrent
        chunk_size = chunk_size or self.config.chunk_size
        
        try:
            # Determine crawl type and execute appropriate method
            if self.is_apple_documentation(url):
                crawl_results = await self.crawl_apple_documentation(url)
                crawl_type = "apple_documentation"
            elif self.is_txt(url):
                crawl_results = await self._crawl_markdown_file(url)
                crawl_type = "text_file"
            elif self.is_sitemap(url):
                sitemap_urls = self.parse_sitemap(url)
                if not sitemap_urls:
                    return {
                        "success": False,
                        "url": url,
                        "error": "No URLs found in sitemap"
                    }
                crawl_results = await self._crawl_batch(sitemap_urls, max_concurrent)
                crawl_type = "sitemap"
            else:
                # For regular URLs, use recursive crawl
                crawl_results = await self._crawl_recursive_internal_links(
                    [url], max_depth, max_concurrent
                )
                crawl_type = "webpage"
                
            if not crawl_results:
                return {
                    "success": False,
                    "url": url,
                    "error": "No content found"
                }
                
            # Process and store all results
            return await self._process_and_store_batch(crawl_results, chunk_size, crawl_type)
            
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }

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

    async def _process_and_store_batch(self, crawl_results: List[Dict[str, Any]], chunk_size: int, crawl_type: str) -> Dict[str, Any]:
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
            chunker = SmartChunker(chunk_size)
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



    async def _crawl_markdown_file(self, url: str) -> List[Dict[str, Any]]:
        """Crawl a markdown/text file"""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return [{'url': url, 'markdown': response.text}]
            else:
                print(f"❌ Failed to fetch {url}: HTTP {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error fetching {url}: {e}")
            return []

    async def _crawl_batch(self, urls: List[str], max_concurrent: int) -> List[Dict[str, Any]]:
        """Crawl multiple URLs in parallel"""
        if not self.crawler:
            return []

        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=False)

        # Process URLs in batches to respect concurrency limits
        results = []
        for i in range(0, len(urls), max_concurrent):
            batch_urls = urls[i:i + max_concurrent]
            batch_results = await self.crawler.arun_many(urls=batch_urls, config=run_config)

            for result in batch_results:
                if result.success and result.markdown:
                    results.append({'url': result.url, 'markdown': result.markdown})

        return results

    async def _crawl_recursive_internal_links(self, start_urls: List[str], max_depth: int, max_concurrent: int) -> List[Dict[str, Any]]:
        """Crawl internal links recursively with database checking"""
        if not self.crawler:
            return []

        visited = set()
        results = []
        current_urls = start_urls

        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=False)

        for depth in range(max_depth):
            if not current_urls:
                break

            # Filter out already visited URLs and check database
            urls_to_crawl = []
            for url in current_urls:
                normalized_url = self.normalize_url(url)

                # Check memory cache first
                if normalized_url in visited:
                    continue

                # Check database if available
                if self.db_operations and await self.db_operations.url_exists(normalized_url):
                    visited.add(normalized_url)
                    continue

                urls_to_crawl.append(normalized_url)

            if not urls_to_crawl:
                break

            # Crawl current level
            batch_results = await self.crawler.arun_many(urls=urls_to_crawl, config=run_config)
            next_level_urls = set()

            for result in batch_results:
                norm_url = self.normalize_url(result.url)
                visited.add(norm_url)

                if result.success and result.markdown:
                    results.append({'url': result.url, 'markdown': result.markdown})

                    # Collect internal links for next level
                    if hasattr(result, 'links') and result.links:
                        for link in result.links.get("internal", []):
                            next_url = self.normalize_url(link["href"])

                            # Skip if already visited
                            if next_url in visited:
                                continue

                            # Skip if already in database
                            if self.db_operations and await self.db_operations.url_exists(next_url):
                                visited.add(next_url)
                                continue

                            next_level_urls.add(next_url)

            current_urls = list(next_level_urls)

        return results
