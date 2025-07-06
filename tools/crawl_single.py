#!/usr/bin/env python3
"""
Single Page Crawl Tool - Direct execution
单页面爬取工具 - 直接执行

Configure TARGET_URL below and run: python tools/crawl_single.py
"""

import sys
import asyncio
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from crawler import IndependentCrawler, CrawlerConfig


# ============================================================================
# HYPERPARAMETERS - Configure your single page crawl here
# ============================================================================

TARGET_URL = "https://developer.apple.com/documentation/visionos/world"


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main() -> None:
    """Execute single page crawl with hyperparameters"""
    print("🔍 Single Page Crawl Tool")
    print("=" * 60)
    print(f"Target URL: {TARGET_URL}")

    # Validate URL
    if not TARGET_URL.startswith(("http://", "https://")):
        print("❌ Error: TARGET_URL must start with http:// or https://")
        print(f"Current value: {TARGET_URL}")
        return

    # Create crawler configuration
    config = CrawlerConfig.from_env()

    # Execute crawl using independent crawler
    try:
        print("🚀 Starting single page crawl...")
        async with IndependentCrawler(config) as crawler:
            result = await crawler.crawl_single_page(TARGET_URL)

        if result["success"]:
            print("✅ Single page crawl completed successfully!")
            print(f"📊 Chunks stored: {result.get('chunks_stored', 'N/A')}")
            print(f"📝 Source ID: {result.get('source_id', 'N/A')}")
            print(f"📏 Total characters: {result.get('total_characters', 'N/A')}")
        else:
            print("❌ Single page crawl failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Single page crawl failed: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Crawl interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
