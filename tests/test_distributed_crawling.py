#!/usr/bin/env python3
"""
分布式爬虫安全性测试 - PostgreSQL FOR UPDATE SKIP LOCKED 验证
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from database import get_database_client, DatabaseOperations


async def test_realistic_crawling_scenario():
    """测试真实爬虫场景下的URL分配"""
    client = await get_database_client()
    db_ops = DatabaseOperations(client)

    all_urls = set()
    duplicate_count = 0

    async def crawler_worker(worker_id: int):
        """模拟真实爬虫worker的行为"""
        nonlocal duplicate_count

        # 获取URL批次
        urls = await db_ops.get_urls_batch(2)

        # 检查重复
        worker_urls = []
        for url in urls:
            if url in all_urls:
                duplicate_count += 1
                print(f"❌ Duplicate: {url} (Worker {worker_id})")
            else:
                all_urls.add(url)
                worker_urls.append(url)

        # 模拟爬取处理时间
        if worker_urls:
            await asyncio.sleep(0.01)  # 10ms处理时间

            # 模拟更新crawl_count（真实场景中会做的）
            for url in worker_urls:
                await db_ops.client.execute_command("""
                    UPDATE pages SET crawl_count = crawl_count + 1
                    WHERE url = $1
                """, url)

        return worker_urls

    # 3个worker，每个执行2轮
    all_results = []
    for round_num in range(2):
        print(f"Round {round_num + 1}:")
        round_results = await asyncio.gather(*[
            crawler_worker(i) for i in range(3)
        ])
        all_results.extend(round_results)
        await asyncio.sleep(0.05)  # 轮次间隔

    total_urls = sum(len(urls) for urls in all_results)
    unique_urls = len(all_urls)

    print(f"📊 Total: {total_urls}, Unique: {unique_urls}, Duplicates: {duplicate_count}")
    return duplicate_count == 0


async def main():
    """主测试函数"""
    print("🧪 Testing distributed crawling safety with PostgreSQL Advisory Locks")
    print("=" * 65)

    try:
        success = await test_realistic_crawling_scenario()

        if success:
            print("✅ Test passed! No duplicate URLs detected.")
            print("🎉 Multi-machine crawling is now safe!")
        else:
            print("❌ Test failed! Duplicate URLs detected.")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
