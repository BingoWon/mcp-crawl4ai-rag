#!/usr/bin/env python3
"""
通用Apple文档测试工具
修改URL变量即可测试任何Apple开发者文档
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# 配置URL - 修改此处即可测试不同的Apple文档
TEST_URL = "https://developer.apple.com/documentation/visionos/playing-immersive-media-with-realitykit"

# 添加src目录到路径
sys.path.append(str(Path(__file__).parent.parent / "src"))

from apple_content_extractor import AppleContentExtractor


async def test_apple_documentation():
    """测试Apple文档的爬取和处理"""
    
    # 生成时间戳用于文件命名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    async with AppleContentExtractor() as extractor:
        result = await extractor.extract_clean_content(TEST_URL)

        if not result["success"]:
            print(f"爬取失败: {result['error']}")
            return

        clean_content = result["clean_content"]

        # 获取原始内容用于对比
        raw_result = await extractor.crawler.crawl(TEST_URL)
        raw_content = raw_result["markdown"] if raw_result["success"] else ""

        # 保存原始内容（清理前）
        raw_output_file = f"test/output/raw_content_{timestamp}.md"
        with open(raw_output_file, 'w', encoding='utf-8') as f:
            f.write(raw_content)

        # 保存清理后内容
        clean_output_file = f"test/output/clean_content_{timestamp}.md"
        with open(clean_output_file, 'w', encoding='utf-8') as f:
            f.write(clean_content)

        print("内容提取完成")
        print(f"原始内容: {raw_output_file}")
        print(f"清理后内容: {clean_output_file}")

        return {
            "success": True,
            "raw_file": raw_output_file,
            "clean_file": clean_output_file
        }


if __name__ == "__main__":
    result = asyncio.run(test_apple_documentation())
    if result and result["success"]:
        exit(0)
    else:
        exit(1)
