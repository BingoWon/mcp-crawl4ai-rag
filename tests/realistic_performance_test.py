#!/usr/bin/env python3
"""
现实场景的数据库访问性能对比测试
修正了测试方法，提供更准确的性能对比
"""

import asyncio
import time
import statistics
import sys
import os
from typing import List, Dict, Any

# 添加src路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from database.client import DatabaseClient
from database.http_client import HTTPDatabaseClient
from database.config import DatabaseConfig


class RealisticPerformanceTest:
    """现实场景性能测试"""
    
    def __init__(self):
        self.results = {}
        
    async def setup_clients(self):
        """设置测试客户端"""
        # 直接访问客户端
        local_config = DatabaseConfig()
        local_config.db_access_mode = 'local'
        self.local_client = DatabaseClient(local_config)
        await self.local_client.initialize()
        
        # Tunnel访问客户端 (模拟远程访问)
        tunnel_config = DatabaseConfig()
        tunnel_config.db_access_mode = 'remote'
        tunnel_config.remote_api_base_url = 'http://localhost:8000'  # 本地测试
        self.tunnel_client = HTTPDatabaseClient(tunnel_config)
        await self.tunnel_client.initialize()
        
        print("✅ 测试客户端初始化完成")
        print(f"  - 直接访问: {type(self.local_client).__name__}")
        print(f"  - Tunnel访问: {type(self.tunnel_client).__name__}")
        print(f"  - Tunnel URL: {tunnel_config.remote_api_base_url}")
    
    async def cleanup_clients(self):
        """清理测试客户端"""
        if hasattr(self, 'local_client'):
            await self.local_client.close()
        if hasattr(self, 'tunnel_client'):
            await self.tunnel_client.close()
    
    async def measure_query_time(self, client, query: str, params: List = None, iterations: int = 5):
        """测量查询时间"""
        times = []
        errors = []
        
        for i in range(iterations):
            start_time = time.perf_counter()
            try:
                if params:
                    result = await client.fetch_all(query, *params)
                else:
                    result = await client.fetch_all(query)
                end_time = time.perf_counter()
                times.append(end_time - start_time)
            except Exception as e:
                end_time = time.perf_counter()
                errors.append(str(e))
                print(f"    ❌ 查询失败: {e}")
            
            # 避免过快请求
            await asyncio.sleep(0.1)
        
        if times:
            return {
                'avg_time': statistics.mean(times),
                'min_time': min(times),
                'max_time': max(times),
                'times': times,
                'errors': errors,
                'success_count': len(times)
            }
        else:
            return {
                'avg_time': 0,
                'min_time': 0,
                'max_time': 0,
                'times': [],
                'errors': errors,
                'success_count': 0
            }
    
    async def test_basic_queries(self):
        """测试基础查询"""
        print("\n🔍 测试1: 基础查询性能对比")
        print("=" * 60)
        
        queries = [
            ("页面计数", "SELECT COUNT(*) FROM pages"),
            ("最新页面", "SELECT url FROM pages ORDER BY created_at DESC LIMIT 5"),
            ("有内容页面", "SELECT COUNT(*) FROM pages WHERE content != ''"),
        ]
        
        for query_name, query in queries:
            print(f"\n📊 {query_name}:")
            
            # 直接访问测试
            local_result = await self.measure_query_time(self.local_client, query)
            if local_result['success_count'] > 0:
                print(f"  直接访问: {local_result['avg_time']:.4f}s (成功{local_result['success_count']}次)")
            else:
                print(f"  直接访问: 失败 - {local_result['errors']}")
                continue
            
            # Tunnel访问测试
            tunnel_result = await self.measure_query_time(self.tunnel_client, query)
            if tunnel_result['success_count'] > 0:
                print(f"  Tunnel访问: {tunnel_result['avg_time']:.4f}s (成功{tunnel_result['success_count']}次)")
                
                # 计算性能开销
                if local_result['avg_time'] > 0:
                    overhead = (tunnel_result['avg_time'] - local_result['avg_time']) / local_result['avg_time'] * 100
                    print(f"  性能开销: {overhead:.1f}%")
                    
                    self.results[f"basic_{query_name}"] = {
                        'local': local_result,
                        'tunnel': tunnel_result,
                        'overhead_percent': overhead
                    }
            else:
                print(f"  Tunnel访问: 失败 - {tunnel_result['errors']}")
    
    async def test_realistic_scenarios(self):
        """测试现实使用场景"""
        print("\n🔍 测试2: 现实使用场景")
        print("=" * 60)
        
        scenarios = [
            ("爬虫获取任务", "SELECT url FROM pages WHERE crawl_count < 3 ORDER BY crawl_count ASC LIMIT 10"),
            ("检查处理状态", "SELECT url, crawl_count FROM pages WHERE url LIKE '%apple%' LIMIT 5"),
            ("统计爬取进度", """
                SELECT 
                    crawl_count,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
                FROM pages 
                GROUP BY crawl_count 
                ORDER BY crawl_count
            """)
        ]
        
        for scenario_name, query in scenarios:
            print(f"\n📊 {scenario_name}:")
            
            # 直接访问测试
            local_result = await self.measure_query_time(self.local_client, query)
            if local_result['success_count'] > 0:
                print(f"  直接访问: {local_result['avg_time']:.4f}s")
            else:
                print(f"  直接访问: 失败")
                continue
            
            # Tunnel访问测试
            tunnel_result = await self.measure_query_time(self.tunnel_client, query)
            if tunnel_result['success_count'] > 0:
                print(f"  Tunnel访问: {tunnel_result['avg_time']:.4f}s")
                
                # 计算性能开销
                overhead = (tunnel_result['avg_time'] - local_result['avg_time']) / local_result['avg_time'] * 100
                print(f"  性能开销: {overhead:.1f}%")
                
                self.results[f"scenario_{scenario_name}"] = {
                    'local': local_result,
                    'tunnel': tunnel_result,
                    'overhead_percent': overhead
                }
            else:
                print(f"  Tunnel访问: 失败")
    
    async def test_network_latency(self):
        """测试网络延迟影响"""
        print("\n🔍 测试3: 网络延迟分析")
        print("=" * 60)
        
        # 简单的ping测试
        simple_query = "SELECT 1"
        
        print(f"\n📊 网络延迟测试 (简单查询):")
        
        # 多次测试获取稳定数据
        local_result = await self.measure_query_time(self.local_client, simple_query, iterations=10)
        tunnel_result = await self.measure_query_time(self.tunnel_client, simple_query, iterations=10)
        
        if local_result['success_count'] > 0 and tunnel_result['success_count'] > 0:
            print(f"  直接访问: {local_result['avg_time']:.4f}s (±{statistics.stdev(local_result['times']):.4f}s)")
            print(f"  Tunnel访问: {tunnel_result['avg_time']:.4f}s (±{statistics.stdev(tunnel_result['times']):.4f}s)")
            
            # 网络延迟 = Tunnel时间 - 直接访问时间
            network_latency = tunnel_result['avg_time'] - local_result['avg_time']
            print(f"  网络延迟: {network_latency:.4f}s")
            
            overhead = (tunnel_result['avg_time'] - local_result['avg_time']) / local_result['avg_time'] * 100
            print(f"  性能开销: {overhead:.1f}%")
            
            self.results["network_latency"] = {
                'local': local_result,
                'tunnel': tunnel_result,
                'latency_seconds': network_latency,
                'overhead_percent': overhead
            }
    
    def generate_realistic_report(self):
        """生成现实场景测试报告"""
        print("\n" + "="*80)
        print("🎯 现实场景性能测试报告")
        print("="*80)
        
        if not self.results:
            print("❌ 没有成功的测试结果")
            return
        
        # 收集开销数据
        overheads = []
        for test_name, result in self.results.items():
            if 'overhead_percent' in result:
                overheads.append(result['overhead_percent'])
        
        if overheads:
            avg_overhead = statistics.mean(overheads)
            min_overhead = min(overheads)
            max_overhead = max(overheads)
            
            print(f"\n📊 性能开销统计:")
            print(f"  平均开销: {avg_overhead:.1f}%")
            print(f"  最小开销: {min_overhead:.1f}%")
            print(f"  最大开销: {max_overhead:.1f}%")
            
            # 网络延迟分析
            if 'network_latency' in self.results:
                latency = self.results['network_latency']['latency_seconds']
                print(f"  网络延迟: {latency:.4f}s")
            
            print(f"\n📋 各场景性能开销:")
            for test_name, result in self.results.items():
                if 'overhead_percent' in result:
                    print(f"  {test_name}: {result['overhead_percent']:.1f}%")
            
            # 性能评级
            if avg_overhead < 50:
                grade = "优秀"
                color = "🟢"
                recommendation = "适合生产环境使用"
            elif avg_overhead < 100:
                grade = "良好"
                color = "🟡"
                recommendation = "适合大多数场景使用"
            elif avg_overhead < 200:
                grade = "一般"
                color = "🟠"
                recommendation = "可接受，注意性能敏感操作"
            else:
                grade = "较差"
                color = "🔴"
                recommendation = "需要优化或考虑其他方案"
            
            print(f"\n🏆 Cloudflare Tunnel 性能评级: {color} {grade}")
            print(f"💡 建议: {recommendation}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 现实场景数据库访问性能对比测试")
        print("="*80)
        print("测试说明: 对比本地直接访问 vs 通过HTTP代理访问的性能差异")
        print("="*80)
        
        try:
            await self.setup_clients()
            
            await self.test_basic_queries()
            await self.test_realistic_scenarios()
            await self.test_network_latency()
            
            self.generate_realistic_report()
            
        except Exception as e:
            print(f"❌ 测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup_clients()


async def main():
    """主函数"""
    test_suite = RealisticPerformanceTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
