#!/usr/bin/env python3
"""
CrawlerPool - Apple网站专用爬虫连接池
基于真实浏览器请求头的精确伪装实现，支持高效连接池复用

=== 连接池架构设计 ===

本模块实现了Apple网站专用的隐蔽爬虫连接池，为批量并发爬取提供高效的浏览器实例管理：

**核心功能：**
- 连接池管理：预创建和复用多个浏览器实例，避免重复启动开销
- 隐蔽伪装：完美模拟真实浏览器行为，有效规避反爬检测
- 并发控制：支持可配置的并发数量，平衡性能和资源使用
- 资源管理：自动管理浏览器实例的生命周期和资源清理

**连接池特性：**
- 预初始化：启动时创建指定数量的浏览器实例
- 队列管理：使用异步队列管理可用的爬虫实例
- 自动复用：爬取完成后自动归还实例到连接池
- 优雅关闭：支持连接池的完整清理和资源释放

=== 双重爬取支持 ===

**爬取模式：**
- 内容爬取：使用CSS选择器("#app-main")获取页面核心内容
- 链接爬取：不使用CSS选择器获取完整页面链接
- 批量处理：支持批量URL的并发爬取处理
- 异常处理：完善的异常隔离和错误处理机制

**性能优化：**
- 浏览器复用：减少50%+的浏览器启动开销
- 并发控制：可配置的并发数量，避免资源竞争
- 内容过滤：智能的Apple文档内容清理和格式化
- 链接提取：高效的内部链接发现和去重处理

**反爬策略：**
- 真实User-Agent：使用真实的浏览器标识
- 完整请求头：模拟真实浏览器的HTTP请求头
- 行为伪装：禁用自动化检测特征
- 延迟控制：合理的页面加载延迟设置
"""

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from typing import Dict, List
import asyncio
import os
from utils.logger import setup_logger
import re
import browser_cookie3

logger = setup_logger(__name__)


class CrawlerPool:
    """Apple网站专用隐蔽爬虫连接池"""

    # 统一User-Agent定义
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"

    def __init__(self, pool_size: int = 3):
        """初始化Apple隐蔽爬虫连接池"""
        self.pool_size = pool_size
        self.apple_cookies = self._get_apple_cookies()
        self.browser_config = self._create_stealth_browser_config()
        self.crawler_pool: List[AsyncWebCrawler] = []
        self.available_crawlers: asyncio.Queue = asyncio.Queue()
        self._initialized = False

    async def initialize(self) -> None:
        """初始化连接池"""
        if self._initialized:
            return

        logger.info(f"Initializing Apple stealth crawler pool with {self.pool_size} instances")

        for _ in range(self.pool_size):
            crawler = AsyncWebCrawler(config=self.browser_config)
            await crawler.__aenter__()
            self.crawler_pool.append(crawler)
            await self.available_crawlers.put(crawler)

        self._initialized = True
        logger.info(f"Apple stealth crawler pool initialized with {self.pool_size} instances")

    async def close(self) -> None:
        """关闭连接池"""
        if not self._initialized:
            return

        logger.info("Closing Apple stealth crawler pool")
        for crawler in self.crawler_pool:
            await crawler.__aexit__(None, None, None)

        self.crawler_pool.clear()
        self._initialized = False
        logger.info("Apple stealth crawler pool closed")

    def _get_apple_cookies(self) -> Dict[str, str]:
        """从Edge浏览器获取Apple网站Cookie，Edge不存在时跳过"""
        try:
            cookies = browser_cookie3.edge(domain_name='apple.com')
            cookie_dict = {}

            for cookie in cookies:
                if 'apple.com' in cookie.domain or 'developer.apple.com' in cookie.domain:
                    cookie_dict[cookie.name] = cookie.value

            if cookie_dict:
                logger.info(f"Successfully extracted {len(cookie_dict)} Apple cookies from Edge")

            return cookie_dict

        except Exception as e:
            logger.info(f"Edge browser not found or cookie extraction failed: {e}")
            logger.info("Continuing without browser cookies")
            return {}

    def _create_stealth_browser_config(self) -> BrowserConfig:
        """创建完美伪装的浏览器配置"""
        headers = self._get_apple_headers()

        # 如果有Apple Cookie，添加到请求头中
        if self.apple_cookies:
            cookie_string = '; '.join([f"{name}={value}" for name, value in self.apple_cookies.items()])
            headers['Cookie'] = cookie_string
            logger.info(f"Added {len(self.apple_cookies)} Apple cookies to browser headers")

        return BrowserConfig(
            headless=True,  # 静默运行，不弹出浏览器窗口
            text_mode=True,
            java_script_enabled=True, # Apple的现代网站需要JavaScript来渲染内容
            light_mode=True,
            browser_type="chromium",
            user_agent=self.USER_AGENT,
            viewport_width=1920,
            viewport_height=1080,
            headers=headers,
            extra_args=[
                "--disable-blink-features=AutomationControlled",
                "--exclude-switches=enable-automation",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
                "--no-first-run",
                "--disable-default-apps",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection"
            ]
        )
    
    def _get_apple_headers(self) -> Dict[str, str]:
        """获取Apple网站专用请求头"""
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-CH-UA": '"Not)A;Brand";v="8", "Chromium";v="138", "Microsoft Edge";v="138"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.USER_AGENT
        }

    def _create_config(self, css_selector=None) -> CrawlerRunConfig:
        """创建爬虫配置 - 支持环境变量动态配置"""
        # 从环境变量读取配置参数
        delay_before_return = int(os.getenv("CRAWLER_DELAY_BEFORE_RETURN", "5"))
        page_timeout = int(os.getenv("CRAWLER_PAGE_TIMEOUT", "5000"))

        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, # 必须使用 BYPASS！！！
            delay_before_return_html=delay_before_return,
            page_timeout=page_timeout,
            css_selector=css_selector,
            exclude_external_links=True,
            only_text=False,
            wait_until="domcontentloaded",
            scan_full_page=False,
            process_iframes=False,
            screenshot=False,
            pdf=False,
            capture_mhtml=False,
            exclude_all_images=True,
        )
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def get_crawler(self) -> AsyncWebCrawler:
        """从连接池获取爬虫实例"""
        return await self.available_crawlers.get()

    async def return_crawler(self, crawler: AsyncWebCrawler) -> None:
        """将爬虫实例归还到连接池"""
        await self.available_crawlers.put(crawler)
    
    async def crawl_page(self, url: str, css_selector: str = None, max_retries: int = 2):
        """爬取页面内容和链接，智能错误处理和重试"""
        logger.info(f"Extracting content and links from: {url}")

        for attempt in range(max_retries + 1):
            crawler = await self.get_crawler()
            try:
                config = self._create_config(css_selector)
                result = await crawler.arun(url=url, config=config)

                content = result.markdown or ""
                if css_selector and content:
                    content = self._post_process_apple_content(content)

                await self.return_crawler(crawler)
                logger.info(f"Content and links extracted from: {url}")
                return content, result.links

            except Exception as e:
                error_msg = str(e)
                is_permanent_error = any(keyword in error_msg.lower() for keyword in [
                    'connection closed', 'pipe closed', 'browsercontext.new_page'
                ])

                if is_permanent_error:
                    # 永久错误：清理实例，创建新实例
                    try:
                        await crawler.__aexit__(None, None, None)
                    except Exception:
                        pass

                    if attempt < max_retries:
                        logger.warning(f"Permanent error on attempt {attempt + 1}, recreating instance: {error_msg}")
                        new_crawler = AsyncWebCrawler(config=self.browser_config)
                        await new_crawler.__aenter__()
                        await self.available_crawlers.put(new_crawler)
                        continue
                else:
                    # 临时错误：归还实例，直接重试
                    await self.return_crawler(crawler)
                    if attempt < max_retries:
                        logger.warning(f"Temporary error on attempt {attempt + 1}, retrying: {error_msg}")
                        continue

                logger.error(f"Failed to crawl {url} after {attempt + 1} attempts: {error_msg}")
                raise

    async def crawl_pages_batch(self, url_selector_pairs: List[tuple[str, str]]):
        """批量爬取页面"""
        tasks = []
        for url, css_selector in url_selector_pairs:
            task = self.crawl_page(url, css_selector)
            tasks.append(task)

        return await asyncio.gather(*tasks, return_exceptions=True)

    def _post_process_apple_content(self, content: str) -> str:
        """后处理Apple文档内容，清理导航元素、图片内容和不需要的章节"""
        if not content:
            return ""
        lines = content.split('\n')
        clean_lines = []

        for line in lines:
            # 移除图片部分，保留后面的文字：![描述](URL)文字说明
            line = re.sub(r'!\[.*?\]\([^)]+\)', '', line)

            # 清理章节标题中的URL链接
            title_url_pattern = r'^(\s*)(#{1,6})\s*\[(.*?)\]\((.*?)\)'
            match = re.match(title_url_pattern, line)
            if match:
                leading_whitespace, level, title_text, _ = match.groups()
                line = f'{leading_whitespace}{level} {title_text}'

            # 清理行内超链接：[text](url) -> text (智能处理转义括号)
            line = re.sub(r'\[([^\]]+)\]\((?:[^)\\]|\\.)*\)', r'\1', line)

            line_stripped = line.strip()

            # 检查是否遇到需要截断的章节
            if line_stripped in ['## Topics', '## See Also']:
                break  # 直接跳出循环，后续内容全部丢弃

            clean_lines.append(line)

        return '\n'.join(clean_lines)

