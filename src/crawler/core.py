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

from typing import List, Tuple
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from database import get_database_client, DatabaseOperations
from .apple_stealth_crawler import CrawlerPool
from utils.logger import setup_logger
import asyncio

logger = setup_logger(__name__)


class BatchCrawler:
    """批量并发网页爬虫，专注于高效的批量爬取和链接发现"""

    # Apple文档URL常量
    APPLE_DOCS_URL_PREFIX = "https://developer.apple.com/documentation/"

    def __init__(self, batch_size: int = 5, max_concurrent: int = 3):
        """Initialize pure crawler with batch configuration"""
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.db_client = None
        self.db_operations = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
        
    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
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
                # Get batch of URLs and content to crawl (minimum crawl_count)
                batch_results = await self.db_operations.get_urls_batch(self.batch_size)
                if not batch_results:
                    logger.info("No URLs to crawl")
                    break

                batch_count += 1
                logger.info(f"=== Batch #{batch_count}: Processing {len(batch_results)} URLs ===")

                # Process batch concurrently
                await self._process_batch(batch_results)

            except KeyboardInterrupt:
                logger.info("Batch crawl interrupted by user")
                break
            except Exception as e:
                logger.error(f"Batch crawl error: {e}")
                continue

    async def _process_batch(self, batch_results: List[Tuple[str, str]]) -> None:
        """简化的双重爬取批量处理"""
        logger.info(f"Batch processing: {len(batch_results)} URLs with dual crawling")

        async with CrawlerPool(pool_size=self.max_concurrent) as crawler:
            all_tasks = []

            # 为每个URL创建两个任务：内容爬取 + 链接爬取
            for url, _ in batch_results:
                # 第一次爬取：带CSS选择器，获取内容
                content_task = crawler.crawl_page(url, "#app-main")
                all_tasks.append((url, content_task, "content"))

                # 第二次爬取：不带CSS选择器，获取链接
                links_task = crawler.crawl_page(url)
                all_tasks.append((url, links_task, "links"))

            # 并发执行所有任务
            results = await asyncio.gather(*[task for _, task, _ in all_tasks], return_exceptions=True)

            # 处理结果
            await self._save_dual_results(batch_results, results, all_tasks)

    async def _save_dual_results(self, batch_results: List[Tuple[str, str]],
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
        for url, _ in batch_results:
            content = content_results.get(url, "")
            url_content_pairs.append((url, content))

        # 批量更新数据库
        if url_content_pairs:
            await self.db_operations.update_pages_batch(url_content_pairs)

        # 存储发现的链接
        if all_discovered_links:
            await self._store_discovered_links(all_discovered_links)
            logger.info(f"✅ Batch processed: {len(url_content_pairs)} pages, {len(all_discovered_links)} new links discovered")
        else:
            logger.info(f"✅ Batch processed: {len(url_content_pairs)} pages, no new links discovered")

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


