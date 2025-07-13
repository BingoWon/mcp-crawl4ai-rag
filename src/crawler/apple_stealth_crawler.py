#!/usr/bin/env python3
"""
Apple网站隐蔽爬虫
基于真实浏览器请求头的精确伪装实现
"""

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from typing import Dict, Any, Optional
import asyncio


class AppleStealthCrawler:
    """Apple网站专用隐蔽爬虫"""

    def __init__(self):
        """初始化Apple隐蔽爬虫"""
        self.browser_config = self._create_stealth_browser_config()
        self.crawler: Optional[AsyncWebCrawler] = None

    def _create_stealth_browser_config(self) -> BrowserConfig:
        """创建完美伪装的浏览器配置"""
        return BrowserConfig(
            headless=True,  # 静默运行，不弹出浏览器窗口
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0",
            viewport_width=1920,
            viewport_height=1080,
            headers=self._get_apple_headers(),
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

    def _create_content_config(self) -> CrawlerRunConfig:
        """创建内容提取配置 - 高质量内容"""
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=10,
            delay_before_return_html=3.0,
            page_timeout=15000,
            remove_overlay_elements=True,
            css_selector="#app-main",  # 精确定位主要内容区域
            exclude_external_links=False,
            exclude_social_media_links=True
        )

    def _create_full_config(self) -> CrawlerRunConfig:
        """创建完整页面配置 - 包含所有链接"""
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=10,
            delay_before_return_html=3.0,
            page_timeout=15000,
            # 不使用css_selector，获取完整页面
            exclude_external_links=False,
            exclude_social_media_links=True
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
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.crawler = AsyncWebCrawler(config=self.browser_config)
        await self.crawler.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc_val, exc_tb)
    
    async def extract_content(self, url: str) -> Dict[str, Any]:
        """提取高质量内容 - 使用css_selector"""
        if not self.crawler:
            raise RuntimeError("Crawler not initialized. Use async with statement.")

        config = self._create_content_config()
        result = await self.crawler.arun(url=url, config=config)

        return {
            "success": result.success,
            "url": url,
            "markdown": result.markdown if result.success else None,
            "error": result.error_message if not result.success else None,
            "content_length": len(result.markdown) if result.success and result.markdown else 0
        }

    async def extract_full_page(self, url: str) -> Dict[str, Any]:
        """提取完整页面 - 包含所有链接"""
        if not self.crawler:
            raise RuntimeError("Crawler not initialized. Use async with statement.")

        config = self._create_full_config()
        result = await self.crawler.arun(url=url, config=config)

        return {
            "success": result.success,
            "url": url,
            "markdown": result.markdown if result.success else None,
            "links": result.links if result.success and hasattr(result, 'links') else None,
            "error": result.error_message if not result.success else None,
            "content_length": len(result.markdown) if result.success and result.markdown else 0
        }


async def test_apple_stealth_crawling():
    """测试Apple隐蔽爬虫"""
    test_url = "https://developer.apple.com/documentation/realitykit"
    
    print("🕵️ 开始Apple隐蔽爬取测试")
    print(f"🎯 目标URL: {test_url}")
    print("=" * 60)
    
    async with AppleStealthCrawler() as crawler:
        result = await crawler.crawl(test_url)
        
        print(f"✅ 爬取状态: {'成功' if result['success'] else '失败'}")
        print(f"📊 内容长度: {result['content_length']} 字符")
        
        if result['success'] and result['markdown']:
            print(f"📝 内容预览 (前500字符):")
            print("-" * 40)
            print(result['markdown'][:500])
            print("-" * 40)
        elif not result['success']:
            print(f"❌ 错误信息: {result['error']}")
        
        return result


if __name__ == "__main__":
    asyncio.run(test_apple_stealth_crawling())
