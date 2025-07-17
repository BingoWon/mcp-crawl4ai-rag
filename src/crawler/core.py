"""
Pure Crawler Core
纯爬取器核心模块

专注于网页爬取和智能链接发现的独立组件，是统一爬虫系统的爬取引擎。

=== 统一爬虫系统架构 ===

本模块是统一爬虫系统的核心组件之一，与处理器组件协同工作：

**系统架构：**
- 统一入口：tools/continuous_crawler.py 并发运行爬取器和处理器
- 职责分离：爬取器专注爬取，处理器专注分块嵌入
- 数据库协调：通过 crawl_count 和 process_count 实现智能调度

**爬取器职责：**
- 网页内容爬取和存储到 pages 表
- 智能链接发现和新URL存储
- crawl_count 计数管理

=== 智能链接发现策略 ===

**核心优化：基于内容状态的智能决策**
- 智能判断：根据页面是否已有内容决定链接发现策略
- 性能优化：避免在空内容页面执行无意义的链接提取
- 双重爬取：需要更多URL时进行第二次爬取获得最大链接覆盖

**实现逻辑：**
1. 获取最小 crawl_count 的页面和其内容状态
2. 智能决策：need_more_urls = bool(existing_content)
3. 执行爬取：_crawl_and_store_page(url, need_more_urls)
4. 条件链接发现：仅在 need_more_urls=True 时进行双重爬取

**性能收益：**
- 减少不必要的网络请求和链接提取操作
- 优化爬取策略，提高系统整体效率
- 智能资源分配，避免浪费计算资源
"""

from typing import Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from database import get_database_client, DatabaseOperations
from .apple_stealth_crawler import AppleStealthCrawler
from utils.logger import setup_logger
import asyncio

logger = setup_logger(__name__)


class PureCrawler:
    """Pure crawler component - only crawling and pages storage"""

    # Apple文档URL常量
    APPLE_DOCS_URL_PREFIX = "https://developer.apple.com/documentation/"

    def __init__(self):
        """Initialize the pure crawler"""
        self.db_client = None
        self.db_operations = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self) -> None:
        """Initialize database connections"""
        logger.info("Initializing pure crawler")
        # Initialize PostgreSQL client
        self.db_client = await get_database_client()
        self.db_operations = DatabaseOperations(self.db_client)

    async def cleanup(self) -> None:
        """Clean up resources"""
        logger.info("Cleaning up crawler resources")

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
        if not self.db_operations:
            raise RuntimeError("Crawler not initialized. Use async with statement.")

        if not start_url.startswith(self.APPLE_DOCS_URL_PREFIX):
            logger.error("Only Apple documentation URLs are supported")
            return

        # Insert start URL if not exists
        await self.db_operations.insert_url_if_not_exists(start_url)
        logger.info(f"Starting pure crawler from: {start_url}")

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

                # Intelligent link discovery strategy based on content status
                need_more_urls = bool(existing_content)  # 有内容说明需要发现更多URL
                await self._crawl_and_store_page(next_url, need_more_urls)

            except KeyboardInterrupt:
                logger.info("Crawl interrupted by user")
                break
            except Exception as e:
                logger.error(f"Crawl error: {e}")
                continue

    async def _crawl_and_store_page(self, url: str, need_more_urls: bool = False) -> None:
        """Crawl single URL and store page content with intelligent link discovery"""
        logger.info(f"Crawling URL: {url}")

        async with AppleStealthCrawler() as crawler:
            # Crawl content and links
            content = ""
            links_data = None
            for i in range(3):
                content, links_data = await crawler.extract_content_and_links(url, "#app-main")
                if content:
                    break
                if i == 2:
                    logger.error(f"❌ No content crawled for {url}")
                    break
                else:
                    logger.error(f"❌ No content crawled for {url}, retrying...")
                    await asyncio.sleep(1)

            # Update page content and crawl_count
            await self.db_operations.update_page_after_crawl(url, content)

            # Intelligent link discovery strategy
            if need_more_urls:
                # Double crawl for maximum link coverage when we need more URLs
                logger.info("Need more URLs: performing double crawl for link discovery")
                _, links_data = await crawler.extract_content_and_links(url)

            # Process discovered links
            extracted_links = self._extract_links_from_data(links_data)
            if extracted_links:
                await self._store_discovered_links(extracted_links)
                logger.info(f"✅ Crawled {url}: {len(extracted_links)} new links discovered")
            else:
                logger.info(f"✅ Crawled {url}: no links discovered")

    async def _store_discovered_links(self, links: list[str]) -> None:
        """Store discovered links to database if not exists"""
        new_count = 0
        for link in links:
            clean_link = self.clean_and_normalize_url(link)
            if clean_link.startswith(self.APPLE_DOCS_URL_PREFIX):
                if await self.db_operations.insert_url_if_not_exists(clean_link):
                    new_count += 1

        if new_count > 0:
            logger.info(f"Added {new_count} new URLs to crawl queue")



    def _extract_links_from_data(self, links_data) -> list[str]:
        """Extract all internal links from crawl results"""
        if not links_data or not links_data.get("internal"):
            return []

        extracted_links = []
        for link in links_data["internal"]:
            # crawl4ai已确保link是dict且包含href
            extracted_links.append(link["href"])

        return list(set(extracted_links))  # Remove duplicates


