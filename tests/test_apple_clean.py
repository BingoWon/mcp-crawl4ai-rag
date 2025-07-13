#!/usr/bin/env python3
"""
Apple文档爬取 - 精简版，只输出txt文件
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler.apple_stealth_crawler import AppleStealthCrawler
from crawler.core import IndependentCrawler
from crawler.apple_content_extractor import AppleContentExtractor


async def crawl_link_contents(cleaned_urls):
    """爬取每个链接的内容"""
    link_contents = {}
    
    async with AppleStealthCrawler() as stealth_crawler:
        for url in cleaned_urls:
            try:
                markdown = await stealth_crawler.extract_content(url)
                link_contents[url] = markdown if markdown else "❌ 无法获取内容"
            except Exception as e:
                link_contents[url] = f"❌ 爬取异常: {str(e)}"
    
    return link_contents


async def save_comprehensive_results(timestamp, content_result, clean_content_result, processing_stats):
    """保存综合结果到文件"""
    filename = f"apple_comprehensive_content_{timestamp}.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        # 原始内容
        f.write("=" * 80 + "\n")
        f.write("原始内容 (AppleStealthCrawler)\n")
        f.write("=" * 80 + "\n")
        if content_result:
            f.write(content_result)
        else:
            f.write("❌ 无法获取原始内容\n")

        # 清理后内容
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("清理后内容 (AppleContentExtractor)\n")
        f.write("=" * 80 + "\n")
        if clean_content_result:
            f.write(clean_content_result)
        else:
            f.write("❌ 无法获取清理后内容\n")

        # 链接列表
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("链接列表\n")
        f.write("=" * 80 + "\n")

        if processing_stats and processing_stats.get('cleaned_urls'):
            for i, url in enumerate(processing_stats['cleaned_urls'], 1):
                f.write(f"{i}. {url}\n")
        else:
            f.write("❌ 无链接列表\n")

    return filename


async def analyze_link_processing(links):
    """分析链接处理过程"""
    if not links:
        return None

    # 创建爬虫实例用于URL处理
    crawler = IndependentCrawler()

    # 获取并过滤Apple文档链接
    internal_links = links.get('internal', []) if isinstance(links, dict) else []
    passed_urls = [
        link["href"] for link in internal_links
        if link["href"].startswith("https://developer.apple.com/documentation/")
    ]

    # 清洗并去重
    cleaned_urls = [crawler.clean_and_normalize_url(url) for url in passed_urls]
    unique_cleaned = list(set(cleaned_urls))

    return {
        'original_count': len(internal_links),
        'passed_count': len(passed_urls),
        'rejected_count': len(internal_links) - len(passed_urls),
        'final_count': len(unique_cleaned),
        'cleaned_urls': unique_cleaned
    }


async def test_single_page_crawl():
    """测试单页面爬取和内容提取"""
    test_url = "https://developer.apple.com/documentation/visionos/playing-immersive-media-with-realitykit"
    test_url = "https://developer.apple.com/documentation/"
    test_url = "https://developer.apple.com/documentation/accounts/acaccountstore"
    test_url = "https://developer.apple.com/documentation/Accounts/"

    # 使用Apple隐蔽爬虫获取原始内容
    async with AppleStealthCrawler() as stealth_crawler:
        content = await stealth_crawler.extract_content(test_url)
        links = await stealth_crawler.extract_links(test_url)

    # 使用Apple内容提取器获取清理后内容
    async with AppleContentExtractor() as content_extractor:
        clean_content = await content_extractor.extract_clean_content(test_url)

    # 分析链接处理过程
    processing_stats = await analyze_link_processing(links)

    return content, clean_content, processing_stats


async def main():
    """主测试函数 - 测试Apple内容提取器并输出txt文件"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 单页面爬取和内容提取测试
    content, clean_content, processing_stats = await test_single_page_crawl()

    # 保存综合结果到文件
    await save_comprehensive_results(timestamp, content, clean_content, processing_stats)


if __name__ == "__main__":
    asyncio.run(main())
