"""
BatchCrawler - 简化双重爬取批量爬虫
批量并发网页爬虫，采用简化的双重爬取策略

专注于高效的批量网页爬取和完整链接发现的独立组件，是统一爬虫系统的核心爬取引擎。

=== 简化双重爬取架构 ===

本模块实现了简化的双重爬取策略，确保逻辑清晰和完整覆盖：

**核心策略：**
- 统一双重爬取：每个URL都进行两次爬取，无例外
- 第一次爬取：带CSS选择器("#app-main")，专门获取页面核心内容
- 第二次爬取：不带CSS选择器，专门获取完整页面链接
- 并发执行：所有爬取任务并发处理，最大化性能

**系统架构：**
- 统一入口：tools/continuous_crawler.py 运行批量爬取器
- 职责分离：爬取器专注内容和链接获取，处理器专注分块嵌入
- 数据库协调：通过 crawl_count 实现智能调度
- 连接池复用：复用浏览器实例，减少启动开销

**爬取器职责：**
- 批量网页内容爬取和存储到 pages 表
- 完整链接发现和新URL存储
- crawl_count 计数管理

=== 双重爬取策略详解 ===

**策略设计原理：**
- 内容获取：使用CSS选择器过滤，获取页面核心内容用于存储和处理
- 链接发现：不使用CSS选择器，获取完整页面所有链接用于URL池扩展
- 职责分离：内容和链接获取完全独立，避免相互干扰
- 覆盖完整：确保每个页面的内容和链接都被完整获取

**批量处理流程：**
1. 批量获取：一次获取多个最小 crawl_count 的页面
2. 任务创建：为每个URL创建内容爬取和链接爬取两个任务
3. 并发执行：使用连接池并发处理所有任务
4. 结果分离：分别处理内容结果和链接结果
5. 批量存储：批量更新数据库，减少I/O开销

**性能特点：**
- 逻辑简单：无复杂条件判断，易于理解和维护
- 覆盖完整：每个URL都进行完整的内容和链接获取
- 并发高效：连接池复用 + 批量并发处理
- 数据库优化：批量操作减少数据库交互次数
"""

from typing import List
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from database import get_database_client, DatabaseOperations
from .apple_stealth_crawler import CrawlerPool
from utils.logger import setup_logger
import asyncio
from urllib.parse import urlparse, urlunparse

logger = setup_logger(__name__)


class BatchCrawler:
    """批量并发网页爬虫，专注于高效的批量爬取和链接发现"""

    # Apple文档URL常量
    APPLE_DOCS_URL_PREFIX = "https://developer.apple.com/documentation/"

    def __init__(self):
        """Initialize batch crawler with environment-based configuration"""
        self.batch_size = int(os.getenv("CRAWLER_BATCH_SIZE", "30"))
        self.max_concurrent = int(os.getenv("CRAWLER_MAX_CONCURRENT", "30"))
        self.db_client = None
        self.db_operations = None
        self.crawler_pool = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
        
    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self) -> None:
        """Initialize database connections and crawler pool"""
        logger.info("Initializing batch crawler with persistent connection pool")

        # Initialize NEON client
        self.db_client = await get_database_client()
        self.db_operations = DatabaseOperations(self.db_client)

        # Initialize persistent crawler pool
        self.crawler_pool = CrawlerPool(pool_size=self.max_concurrent)
        await self.crawler_pool.initialize()
        logger.info(f"Persistent crawler pool initialized with {self.max_concurrent} instances")

    async def cleanup(self) -> None:
        """Clean up resources including persistent crawler pool"""
        logger.info("Cleaning up batch crawler resources")

        # Close persistent crawler pool
        if self.crawler_pool:
            await self.crawler_pool.close()
            self.crawler_pool = None
            logger.info("Persistent crawler pool closed")

    def clean_and_normalize_urls_batch(self, urls: List[str]) -> List[str]:
        """批量清洗和标准化URL - 全局最优解"""
        cleaned_urls = []
        for url in urls:
            parsed = urlparse(url)
            # 清洗：移除fragment，标准化：移除末尾斜杠
            cleaned_parsed = parsed._replace(fragment='', path=parsed.path.rstrip('/'))
            cleaned_urls.append(urlunparse(cleaned_parsed))
        return cleaned_urls


    async def start_crawling(self, start_url: str) -> None:
        """开始批量爬取循环"""
        if not self.db_operations:
            raise RuntimeError("Crawler not initialized. Use async with statement.")

        if not start_url.startswith(self.APPLE_DOCS_URL_PREFIX):
            logger.error("Only Apple documentation URLs are supported")
            return

        # Insert start URL if not exists
        await self.db_operations.insert_url_if_not_exists(start_url)
        logger.info(f"Starting batch crawler from: {start_url} (batch_size={self.batch_size}, max_concurrent={self.max_concurrent})")

        batch_count = 0
        while True:
            try:
                # Get batch of URLs to crawl (minimum crawl_count)
                batch_urls = await self.db_operations.get_urls_batch(self.batch_size)
                if not batch_urls:
                    logger.info("No URLs to crawl")
                    break

                batch_count += 1
                logger.info(f"=== Batch #{batch_count}: Processing {len(batch_urls)} URLs ===")

                # Process batch concurrently
                await self._process_batch(batch_urls)

            except KeyboardInterrupt:
                logger.info("Batch crawl interrupted by user")
                break
            except Exception as e:
                logger.error(f"Batch crawl error: {e}")
                continue

    async def _process_batch(self, batch_urls: List[str]) -> None:
        """优化的双重爬取批量处理 - 使用持久连接池"""
        logger.info(f"Batch processing: {len(batch_urls)} URLs with persistent crawler pool")

        if not self.crawler_pool:
            raise RuntimeError("Crawler pool not initialized. Use async with statement.")

        all_tasks = []

        # 为每个URL创建两个任务：内容爬取 + 链接爬取
        for url in batch_urls:
            # 第一次爬取：带CSS选择器，获取内容
            content_task = self.crawler_pool.crawl_page(url, "#app-main")
            all_tasks.append((url, content_task, "content"))

            # 第二次爬取：不带CSS选择器，获取链接
            # links_task = self.crawler_pool.crawl_page(url)
            # all_tasks.append((url, links_task, "links"))
            # TODO: 只爬取一次则通过下面的配置：
            all_tasks.append((url, content_task, "links"))

        # 并发执行所有任务
        results = await asyncio.gather(*[task for _, task, _ in all_tasks], return_exceptions=True)

        # 处理结果
        await self._save_dual_results(batch_urls, results, all_tasks)

    async def _save_dual_results(self, batch_urls: List[str],
                               crawl_results: List, all_tasks: List) -> None:
        """保存双重爬取结果到数据库"""
        url_content_pairs = []
        all_discovered_links = []

        # 按任务类型分组处理结果
        content_results = {}

        for i, (url, _, task_type) in enumerate(all_tasks):
            result = crawl_results[i]
            if isinstance(result, Exception):
                logger.error(f"❌ Failed to crawl {url} ({task_type}): {result}")
                continue

            if task_type == "content":
                content, _ = result
                content_results[url] = content
            elif task_type == "links":
                _, links_data = result
                if links_data:
                    extracted_links = self._extract_links_from_data(links_data)
                    all_discovered_links.extend(extracted_links)

        # 准备内容更新数据
        for url in batch_urls:
            content = content_results.get(url, "")
            url_content_pairs.append((url, content))

        # 批量选择性更新数据库 - 全局最优解
        if url_content_pairs:
            valid_count, empty_count = await self.db_operations.update_pages_batch(url_content_pairs)
            logger.info(f"📊 Content update stats: {valid_count} valid, {empty_count} empty")

        # 存储发现的链接
        if all_discovered_links:
            await self._store_discovered_links(all_discovered_links)
            logger.info(f"✅ Batch processed: {len(url_content_pairs)} pages ({valid_count} valid content), {len(all_discovered_links)} new links discovered")
        else:
            logger.info(f"✅ Batch processed: {len(url_content_pairs)} pages ({valid_count} valid content), no new links discovered")

    async def _store_discovered_links(self, links: list[str]) -> None:
        """批量存储发现的链接 - 全局最优解"""
        if not links:
            return

        # 批量清理和过滤Apple文档链接
        cleaned_links = self.clean_and_normalize_urls_batch(links)
        apple_links = [link for link in cleaned_links if link.startswith(self.APPLE_DOCS_URL_PREFIX)]

        if not apple_links:
            return

        # 批量插入数据库
        new_count = await self.db_operations.insert_urls_batch(apple_links)

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


