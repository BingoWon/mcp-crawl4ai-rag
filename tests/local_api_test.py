#!/usr/bin/env python3
"""
本地API参数化查询测试
专门测试本地API服务器的参数化查询功能
"""

import asyncio
import sys
import os

# 添加src路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from database.http_client import HTTPDatabaseClient
from database.config import DatabaseConfig


async def test_local_api_params():
    """测试本地API的参数化查询"""
    print("🔍 测试本地API参数化查询")
    print("=" * 50)
    
    # 创建本地API配置
    config = DatabaseConfig()
    config.remote_api_base_url = 'http://localhost:8000'
    config.api_key = 'ZBYlBx77H9Sc87k'
    
    client = HTTPDatabaseClient(config)
    await client.initialize()
    
    try:
        print(f"📡 连接到: {config.remote_api_base_url}")
        
        # 测试1: 简单查询（无参数）
        print("\n📊 测试1: 简单查询")
        result = await client.fetch_val("SELECT COUNT(*) FROM pages")
        print(f"  ✅ 页面总数: {result}")
        
        # 测试2: 参数化查询
        print("\n📊 测试2: 参数化查询")
        
        # 测试不同的参数传递方式
        test_queries = [
            ("单参数", "SELECT COUNT(*) FROM pages WHERE crawl_count >= $1", [0]),
            ("多参数", "SELECT COUNT(*) FROM pages WHERE crawl_count BETWEEN $1 AND $2", [0, 5]),
            ("字符串参数", "SELECT url FROM pages WHERE url LIKE $1 LIMIT 2", ['%apple%'])
        ]
        
        for test_name, query, params in test_queries:
            try:
                print(f"\n  🔍 {test_name}:")
                print(f"    查询: {query}")
                print(f"    参数: {params}")
                
                if "COUNT" in query:
                    result = await client.fetch_val(query, *params)
                else:
                    result = await client.fetch_all(query, *params)
                
                print(f"    ✅ 结果: {result}")
                
            except Exception as e:
                print(f"    ❌ 失败: {e}")
        
        # 测试3: 直接HTTP请求
        print("\n📊 测试3: 直接HTTP请求")
        import aiohttp
        import json
        
        async with aiohttp.ClientSession() as session:
            data = {
                "query": "SELECT COUNT(*) FROM pages WHERE crawl_count >= $1",
                "params": [0]
            }
            
            async with session.post(
                f"{config.remote_api_base_url}/query",
                headers={
                    "X-API-Key": config.api_key,
                    "Content-Type": "application/json"
                },
                json=data
            ) as response:
                result = await response.json()
                print(f"  HTTP响应: {result}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


async def main():
    """主函数"""
    await test_local_api_params()


if __name__ == "__main__":
    asyncio.run(main())
