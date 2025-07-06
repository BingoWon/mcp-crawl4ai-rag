#!/usr/bin/env python3
"""
Smart Website Crawl Tool - Direct execution
智能网站爬取工具 - 直接执行

Configure hyperparameters below and run: python tools/crawl_smart.py
"""

import sys
import asyncio
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from crawler import IndependentCrawler, CrawlerConfig


# ============================================================================
# HYPERPARAMETERS - Configure your smart crawl here
# ============================================================================

TARGET_URL = "https://developer.apple.com/documentation/visionos/"
MAX_DEPTH = 2
MAX_CONCURRENT = 5
CHUNK_SIZE = 5000


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main() -> None:
    """Execute smart website crawl with hyperparameters"""
    print("🌐 Smart Website Crawl Tool")
    print("=" * 60)
    print(f"Target URL: {TARGET_URL}")
    print(f"Max Depth: {MAX_DEPTH}")
    print(f"Max Concurrent: {MAX_CONCURRENT}")
    print(f"Chunk Size: {CHUNK_SIZE}")

    # Validate URL
    if not TARGET_URL.startswith(("http://", "https://")):
        print("❌ Error: TARGET_URL must start with http:// or https://")
        print(f"Current value: {TARGET_URL}")
        return

    # Create crawler configuration
    config = CrawlerConfig.with_params(
        max_depth=MAX_DEPTH,
        max_concurrent=MAX_CONCURRENT,
        chunk_size=CHUNK_SIZE
    )

    # Execute crawl using independent crawler
    try:
        print("🚀 Starting smart website crawl...")
        async with IndependentCrawler(config) as crawler:
            result = await crawler.smart_crawl_url(TARGET_URL, MAX_DEPTH, MAX_CONCURRENT, CHUNK_SIZE)

        if result["success"]:
            print("✅ Smart website crawl completed successfully!")
            print(f"📊 Crawl type: {result.get('crawl_type', 'N/A')}")
            print(f"📄 Total pages: {result.get('total_pages', 'N/A')}")
            print(f"📝 Total chunks: {result.get('total_chunks', 'N/A')}")
            print(f"🗂️ Sources updated: {result.get('sources_updated', 'N/A')}")
        else:
            print("❌ Smart website crawl failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Smart website crawl failed: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Crawl interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
