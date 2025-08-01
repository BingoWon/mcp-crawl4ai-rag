#!/usr/bin/env python3
"""
数据库访问性能对比测试
对比直接访问 vs Cloudflare Tunnel访问的性能差异
"""

import asyncio
import time
import statistics
import sys
import os
from typing import List, Dict, Any
from contextlib import asynccontextmanager

# 添加src路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from database.client import DatabaseClient
from database.http_client import HTTPDatabaseClient
from database.config import DatabaseConfig


class PerformanceTestSuite:
    """性能测试套件"""
    
    def __init__(self):
        self.results = {}
        
    async def setup_clients(self):
        """设置测试客户端"""
        # 直接访问客户端
        local_config = DatabaseConfig()
        local_config.db_access_mode = 'local'
        self.local_client = DatabaseClient(local_config)
        await self.local_client.initialize()
        
        # Tunnel访问客户端
        tunnel_config = DatabaseConfig()
        tunnel_config.db_access_mode = 'remote'
        self.tunnel_client = HTTPDatabaseClient(tunnel_config)
        await self.tunnel_client.initialize()
        
        print("✅ 测试客户端初始化完成")
        print(f"  - 直接访问: {type(self.local_client).__name__}")
        print(f"  - Tunnel访问: {type(self.tunnel_client).__name__}")
    
    async def cleanup_clients(self):
        """清理测试客户端"""
        if hasattr(self, 'local_client'):
            await self.local_client.close()
        if hasattr(self, 'tunnel_client'):
            await self.tunnel_client.close()
    
    async def measure_time(self, func, *args, **kwargs):
        """测量函数执行时间"""
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            end_time = time.perf_counter()
            return end_time - start_time, result, None
        except Exception as e:
            end_time = time.perf_counter()
            return end_time - start_time, None, str(e)
    
    async def run_query_test(self, client, query: str, params: List = None, iterations: int = 10):
        """运行查询测试"""
        times = []
        errors = []
        
        for i in range(iterations):
            if params:
                duration, result, error = await self.measure_time(
                    client.fetch_all, query, *params
                )
            else:
                duration, result, error = await self.measure_time(
                    client.fetch_all, query
                )
            
            times.append(duration)
            if error:
                errors.append(error)
            
            # 避免过快请求
            await asyncio.sleep(0.01)
        
        return {
            'times': times,
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'median_time': statistics.median(times),
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
            'errors': errors,
            'success_rate': (iterations - len(errors)) / iterations * 100
        }
    
    async def test_simple_queries(self):
        """测试简单查询"""
        print("\n🔍 测试1: 简单查询性能")
        print("=" * 50)
        
        queries = [
            ("COUNT查询", "SELECT COUNT(*) FROM pages"),
            ("LIMIT查询", "SELECT url FROM pages LIMIT 10"),
            ("WHERE查询", "SELECT url FROM pages WHERE crawl_count > 0 LIMIT 5"),
            ("ORDER查询", "SELECT url FROM pages ORDER BY last_crawled_at DESC LIMIT 5")
        ]
        
        for query_name, query in queries:
            print(f"\n📊 {query_name}:")
            
            # 直接访问测试
            local_result = await self.run_query_test(self.local_client, query)
            print(f"  直接访问: {local_result['avg_time']:.4f}s (±{local_result['std_dev']:.4f}s)")
            
            # Tunnel访问测试
            tunnel_result = await self.run_query_test(self.tunnel_client, query)
            print(f"  Tunnel访问: {tunnel_result['avg_time']:.4f}s (±{tunnel_result['std_dev']:.4f}s)")
            
            # 性能比较
            overhead = (tunnel_result['avg_time'] - local_result['avg_time']) / local_result['avg_time'] * 100
            print(f"  性能开销: {overhead:.1f}%")
            
            self.results[f"simple_{query_name}"] = {
                'local': local_result,
                'tunnel': tunnel_result,
                'overhead_percent': overhead
            }
    
    async def test_complex_queries(self):
        """测试复杂查询"""
        print("\n🔍 测试2: 复杂查询性能")
        print("=" * 50)
        
        queries = [
            ("聚合查询", """
                SELECT crawl_count, COUNT(*) as count 
                FROM pages 
                GROUP BY crawl_count 
                ORDER BY crawl_count
            """),
            ("统计查询", """
                SELECT 
                    COUNT(*) as total_pages,
                    AVG(crawl_count) as avg_crawl_count,
                    MAX(crawl_count) as max_crawl_count
                FROM pages
            """),
            ("条件统计", """
                SELECT 
                    CASE 
                        WHEN content = '' THEN 'empty'
                        ELSE 'has_content'
                    END as content_status,
                    COUNT(*) as count
                FROM pages
                GROUP BY content_status
            """)
        ]
        
        for query_name, query in queries:
            print(f"\n📊 {query_name}:")
            
            # 直接访问测试
            local_result = await self.run_query_test(self.local_client, query, iterations=5)
            print(f"  直接访问: {local_result['avg_time']:.4f}s (±{local_result['std_dev']:.4f}s)")
            
            # Tunnel访问测试
            tunnel_result = await self.run_query_test(self.tunnel_client, query, iterations=5)
            print(f"  Tunnel访问: {tunnel_result['avg_time']:.4f}s (±{tunnel_result['std_dev']:.4f}s)")
            
            # 性能比较
            overhead = (tunnel_result['avg_time'] - local_result['avg_time']) / local_result['avg_time'] * 100
            print(f"  性能开销: {overhead:.1f}%")
            
            self.results[f"complex_{query_name}"] = {
                'local': local_result,
                'tunnel': tunnel_result,
                'overhead_percent': overhead
            }
    
    async def test_parameterized_queries(self):
        """测试参数化查询"""
        print("\n🔍 测试3: 参数化查询性能")
        print("=" * 50)
        
        queries = [
            ("单参数查询", "SELECT url FROM pages WHERE crawl_count = $1", [1]),
            ("多参数查询", "SELECT url FROM pages WHERE crawl_count >= $1 AND crawl_count <= $2 LIMIT $3", [0, 5, 10]),
            ("LIKE查询", "SELECT url FROM pages WHERE url LIKE $1 LIMIT 5", ['%apple%'])
        ]
        
        for query_name, query, params in queries:
            print(f"\n📊 {query_name}:")
            
            # 直接访问测试
            local_result = await self.run_query_test(self.local_client, query, params)
            print(f"  直接访问: {local_result['avg_time']:.4f}s (±{local_result['std_dev']:.4f}s)")
            
            # Tunnel访问测试
            tunnel_result = await self.run_query_test(self.tunnel_client, query, params)
            print(f"  Tunnel访问: {tunnel_result['avg_time']:.4f}s (±{tunnel_result['std_dev']:.4f}s)")
            
            # 性能比较
            overhead = (tunnel_result['avg_time'] - local_result['avg_time']) / local_result['avg_time'] * 100
            print(f"  性能开销: {overhead:.1f}%")
            
            self.results[f"param_{query_name}"] = {
                'local': local_result,
                'tunnel': tunnel_result,
                'overhead_percent': overhead
            }

    async def test_write_operations(self):
        """测试写操作性能"""
        print("\n🔍 测试4: 写操作性能")
        print("=" * 50)

        # 测试INSERT操作
        print(f"\n📊 INSERT操作:")

        async def insert_test_data(client):
            test_url = f"https://test-{int(time.time())}.example.com"
            await client.execute_command(
                "INSERT INTO pages (url, crawl_count, content) VALUES ($1, $2, $3)",
                test_url, 0, "test content"
            )
            return test_url

        # 直接访问INSERT测试
        local_times = []
        for i in range(5):
            duration, result, error = await self.measure_time(insert_test_data, self.local_client)
            local_times.append(duration)
            await asyncio.sleep(0.01)

        # Tunnel访问INSERT测试
        tunnel_times = []
        for i in range(5):
            duration, result, error = await self.measure_time(insert_test_data, self.tunnel_client)
            tunnel_times.append(duration)
            await asyncio.sleep(0.01)

        local_avg = statistics.mean(local_times)
        tunnel_avg = statistics.mean(tunnel_times)
        overhead = (tunnel_avg - local_avg) / local_avg * 100

        print(f"  直接访问: {local_avg:.4f}s")
        print(f"  Tunnel访问: {tunnel_avg:.4f}s")
        print(f"  性能开销: {overhead:.1f}%")

        self.results["write_insert"] = {
            'local': {'avg_time': local_avg, 'times': local_times},
            'tunnel': {'avg_time': tunnel_avg, 'times': tunnel_times},
            'overhead_percent': overhead
        }

    async def test_connection_overhead(self):
        """测试连接开销"""
        print("\n🔍 测试5: 连接建立开销")
        print("=" * 50)

        # 测试连接建立时间
        async def test_connection_time(client_class, config):
            start_time = time.perf_counter()
            client = client_class(config)
            await client.initialize()
            end_time = time.perf_counter()
            await client.close()
            return end_time - start_time

        # 直接连接测试
        local_config = DatabaseConfig()
        local_config.db_access_mode = 'local'

        local_times = []
        for i in range(3):
            duration = await test_connection_time(DatabaseClient, local_config)
            local_times.append(duration)
            await asyncio.sleep(0.1)

        # Tunnel连接测试
        tunnel_config = DatabaseConfig()
        tunnel_config.db_access_mode = 'remote'

        tunnel_times = []
        for i in range(3):
            duration = await test_connection_time(HTTPDatabaseClient, tunnel_config)
            tunnel_times.append(duration)
            await asyncio.sleep(0.1)

        local_avg = statistics.mean(local_times)
        tunnel_avg = statistics.mean(tunnel_times)
        overhead = (tunnel_avg - local_avg) / local_avg * 100

        print(f"  直接连接: {local_avg:.4f}s")
        print(f"  Tunnel连接: {tunnel_avg:.4f}s")
        print(f"  连接开销: {overhead:.1f}%")

        self.results["connection_overhead"] = {
            'local': {'avg_time': local_avg, 'times': local_times},
            'tunnel': {'avg_time': tunnel_avg, 'times': tunnel_times},
            'overhead_percent': overhead
        }

    async def test_concurrent_queries(self):
        """测试并发查询性能"""
        print("\n🔍 测试6: 并发查询性能")
        print("=" * 50)

        query = "SELECT COUNT(*) FROM pages"
        concurrent_levels = [1, 5, 10]

        for level in concurrent_levels:
            print(f"\n📊 {level}个并发查询:")

            # 直接访问并发测试
            async def run_concurrent_local():
                tasks = []
                for i in range(level):
                    task = self.local_client.fetch_all(query)
                    tasks.append(task)

                start_time = time.perf_counter()
                await asyncio.gather(*tasks)
                end_time = time.perf_counter()
                return end_time - start_time

            # Tunnel访问并发测试
            async def run_concurrent_tunnel():
                tasks = []
                for i in range(level):
                    task = self.tunnel_client.fetch_all(query)
                    tasks.append(task)

                start_time = time.perf_counter()
                await asyncio.gather(*tasks)
                end_time = time.perf_counter()
                return end_time - start_time

            # 运行测试
            local_time = await run_concurrent_local()
            await asyncio.sleep(0.1)
            tunnel_time = await run_concurrent_tunnel()

            overhead = (tunnel_time - local_time) / local_time * 100

            print(f"  直接访问: {local_time:.4f}s")
            print(f"  Tunnel访问: {tunnel_time:.4f}s")
            print(f"  性能开销: {overhead:.1f}%")

            self.results[f"concurrent_{level}"] = {
                'local': {'time': local_time},
                'tunnel': {'time': tunnel_time},
                'overhead_percent': overhead
            }

    def generate_summary_report(self):
        """生成性能测试总结报告"""
        print("\n" + "="*80)
        print("🎯 性能测试总结报告")
        print("="*80)

        # 收集所有开销数据
        overheads = []
        for test_name, result in self.results.items():
            if 'overhead_percent' in result:
                overheads.append(result['overhead_percent'])

        if overheads:
            avg_overhead = statistics.mean(overheads)
            min_overhead = min(overheads)
            max_overhead = max(overheads)

            print(f"\n📊 总体性能开销统计:")
            print(f"  平均开销: {avg_overhead:.1f}%")
            print(f"  最小开销: {min_overhead:.1f}%")
            print(f"  最大开销: {max_overhead:.1f}%")

        print(f"\n📋 详细测试结果:")
        for test_name, result in self.results.items():
            if 'overhead_percent' in result:
                print(f"  {test_name}: {result['overhead_percent']:.1f}% 开销")

        # 性能评级
        if avg_overhead < 10:
            grade = "优秀 (A)"
            color = "🟢"
        elif avg_overhead < 25:
            grade = "良好 (B)"
            color = "🟡"
        elif avg_overhead < 50:
            grade = "一般 (C)"
            color = "🟠"
        else:
            grade = "较差 (D)"
            color = "🔴"

        print(f"\n🏆 Cloudflare Tunnel 性能评级: {color} {grade}")
        print(f"   (平均性能开销: {avg_overhead:.1f}%)")

        # 建议
        print(f"\n💡 使用建议:")
        if avg_overhead < 15:
            print("  ✅ Cloudflare Tunnel 性能优秀，适合生产环境使用")
            print("  ✅ 可以放心用于高频数据库操作")
        elif avg_overhead < 30:
            print("  ⚠️ Cloudflare Tunnel 性能良好，适合大多数场景")
            print("  ⚠️ 对性能敏感的操作建议直接访问")
        else:
            print("  ❌ Cloudflare Tunnel 性能开销较大")
            print("  ❌ 建议优化网络配置或考虑其他方案")

    async def run_all_tests(self):
        """运行所有性能测试"""
        print("🚀 开始数据库访问性能对比测试")
        print("="*80)
        print("测试环境: 本地电脑")
        print("对比方案: 直接访问 vs Cloudflare Tunnel访问")
        print("="*80)

        try:
            await self.setup_clients()

            # 运行各项测试
            await self.test_simple_queries()
            await self.test_complex_queries()
            await self.test_parameterized_queries()
            await self.test_write_operations()
            await self.test_connection_overhead()
            await self.test_concurrent_queries()

            # 生成报告
            self.generate_summary_report()

        except Exception as e:
            print(f"❌ 测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup_clients()


async def main():
    """主函数"""
    test_suite = PerformanceTestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
