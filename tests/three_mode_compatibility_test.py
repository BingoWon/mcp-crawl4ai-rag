#!/usr/bin/env python3
"""
三种数据库模式兼容性测试
测试 local、remote、cloud 三种数据库访问模式的兼容性
注意：只进行只读测试，不影响生产数据
"""

import asyncio
import sys
import os
from typing import Dict, Any, List
from dataclasses import dataclass

# 添加src路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from database.config import DatabaseConfig, DatabaseAccessMode
from database.client import DatabaseClient
from database.http_client import HTTPDatabaseClient
from database.utils import get_database_client, get_database_operations


@dataclass
class TestResult:
    """测试结果"""
    mode: str
    test_name: str
    success: bool
    result: Any = None
    error: str = None
    duration: float = 0.0


class ThreeModeCompatibilityTest:
    """三种模式兼容性测试"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.clients = {}
        self.operations = {}
    
    async def setup_all_modes(self):
        """设置所有三种模式的客户端"""
        print("🔧 设置三种数据库访问模式...")
        print("=" * 60)
        
        modes = [
            ('local', DatabaseAccessMode.LOCAL),
            ('remote', DatabaseAccessMode.REMOTE), 
            ('cloud', DatabaseAccessMode.CLOUD)
        ]
        
        for mode_name, mode_enum in modes:
            try:
                print(f"\n📡 设置 {mode_name} 模式...")
                
                # 创建配置
                config = DatabaseConfig.from_env()
                config.access_mode = mode_enum
                
                # 创建客户端
                if mode_enum == DatabaseAccessMode.REMOTE:
                    client = HTTPDatabaseClient(config)
                else:
                    client = DatabaseClient(config)
                
                await client.initialize()
                self.clients[mode_name] = client
                
                print(f"  ✅ {mode_name} 模式客户端初始化成功")
                print(f"     类型: {type(client).__name__}")
                
                if mode_name == 'local':
                    print(f"     连接: {config.local_host}:{config.local_port}/{config.local_database}")
                elif mode_name == 'remote':
                    print(f"     API: {config.remote_api_base_url}")
                elif mode_name == 'cloud':
                    print(f"     连接: {config.cloud_host}:{config.cloud_port}/{config.cloud_database}")
                
            except Exception as e:
                print(f"  ❌ {mode_name} 模式设置失败: {e}")
                self.clients[mode_name] = None
    
    async def cleanup_all_modes(self):
        """清理所有客户端"""
        for mode_name, client in self.clients.items():
            if client:
                try:
                    await client.close()
                    print(f"✅ {mode_name} 模式客户端已关闭")
                except Exception as e:
                    print(f"❌ {mode_name} 模式关闭失败: {e}")
    
    async def test_basic_connectivity(self):
        """测试基础连接性"""
        print("\n🔍 测试1: 基础连接性测试")
        print("=" * 60)
        
        for mode_name, client in self.clients.items():
            if not client:
                print(f"❌ {mode_name} 模式: 客户端未初始化")
                continue
            
            print(f"\n📊 测试 {mode_name} 模式连接性:")
            
            try:
                # 测试简单查询
                import time
                start_time = time.perf_counter()
                result = await client.fetch_val("SELECT 1")
                end_time = time.perf_counter()
                
                duration = end_time - start_time
                
                # 对于不同的客户端，返回值可能不同
                expected_value = 1
                actual_value = result

                # HTTP客户端可能返回字符串或包装的结果
                if isinstance(result, str) and result == "1":
                    actual_value = 1
                elif isinstance(result, dict) and 'result' in result:
                    actual_value = int(result['result']) if str(result['result']).isdigit() else result['result']

                if actual_value == expected_value:
                    print(f"  ✅ 连接成功 ({duration:.4f}s)")
                    self.results.append(TestResult(
                        mode=mode_name,
                        test_name="basic_connectivity",
                        success=True,
                        result=result,
                        duration=duration
                    ))
                else:
                    print(f"  ❌ 连接异常: 期望{expected_value}，得到{result}")
                    self.results.append(TestResult(
                        mode=mode_name,
                        test_name="basic_connectivity",
                        success=False,
                        error=f"Unexpected result: {result}"
                    ))
                    
            except Exception as e:
                print(f"  ❌ 连接失败: {e}")
                self.results.append(TestResult(
                    mode=mode_name,
                    test_name="basic_connectivity",
                    success=False,
                    error=str(e)
                ))
    
    async def test_read_operations(self):
        """测试只读操作（不影响生产数据）"""
        print("\n🔍 测试2: 只读操作测试")
        print("=" * 60)
        
        read_tests = [
            ("count_pages", "SELECT COUNT(*) FROM pages", "页面总数"),
            ("count_chunks", "SELECT COUNT(*) FROM chunks", "块总数"),
            ("sample_pages", "SELECT url FROM pages LIMIT 3", "样本页面"),
            ("table_info", """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """, "表信息")
        ]
        
        for mode_name, client in self.clients.items():
            if not client:
                continue
                
            print(f"\n📊 测试 {mode_name} 模式只读操作:")
            
            for test_name, query, description in read_tests:
                try:
                    import time
                    start_time = time.perf_counter()
                    
                    if "COUNT" in query:
                        result = await client.fetch_val(query)
                    else:
                        result = await client.fetch_all(query)
                    
                    end_time = time.perf_counter()
                    duration = end_time - start_time
                    
                    print(f"  ✅ {description}: {result} ({duration:.4f}s)")
                    
                    self.results.append(TestResult(
                        mode=mode_name,
                        test_name=test_name,
                        success=True,
                        result=result,
                        duration=duration
                    ))
                    
                except Exception as e:
                    print(f"  ❌ {description}: {e}")
                    self.results.append(TestResult(
                        mode=mode_name,
                        test_name=test_name,
                        success=False,
                        error=str(e)
                    ))
    
    async def test_parameterized_queries(self):
        """测试参数化查询"""
        print("\n🔍 测试3: 参数化查询测试")
        print("=" * 60)
        
        param_tests = [
            ("param_count", "SELECT COUNT(*) FROM pages WHERE crawl_count >= $1", [0], "参数化计数"),
            ("param_search", "SELECT url FROM pages WHERE url LIKE $1 LIMIT 2", ['%apple%'], "参数化搜索"),
            ("param_range", "SELECT COUNT(*) FROM pages WHERE crawl_count BETWEEN $1 AND $2", [0, 5], "参数化范围")
        ]
        
        for mode_name, client in self.clients.items():
            if not client:
                continue
                
            print(f"\n📊 测试 {mode_name} 模式参数化查询:")
            
            for test_name, query, params, description in param_tests:
                try:
                    import time
                    start_time = time.perf_counter()
                    
                    if "COUNT" in query:
                        result = await client.fetch_val(query, *params)
                    else:
                        result = await client.fetch_all(query, *params)
                    
                    end_time = time.perf_counter()
                    duration = end_time - start_time
                    
                    print(f"  ✅ {description}: {result} ({duration:.4f}s)")
                    
                    self.results.append(TestResult(
                        mode=mode_name,
                        test_name=test_name,
                        success=True,
                        result=result,
                        duration=duration
                    ))
                    
                except Exception as e:
                    print(f"  ❌ {description}: {e}")
                    self.results.append(TestResult(
                        mode=mode_name,
                        test_name=test_name,
                        success=False,
                        error=str(e)
                    ))
    
    async def test_operations_layer(self):
        """测试操作层兼容性"""
        print("\n🔍 测试4: 操作层兼容性测试")
        print("=" * 60)
        
        for mode_name in ['local', 'remote', 'cloud']:
            if mode_name not in self.clients or not self.clients[mode_name]:
                continue
                
            print(f"\n📊 测试 {mode_name} 模式操作层:")
            
            try:
                # 临时设置环境变量
                original_mode = os.environ.get('DB_ACCESS_MODE')
                os.environ['DB_ACCESS_MODE'] = mode_name
                
                # 测试客户端方法（只读）
                import time
                start_time = time.perf_counter()

                # 测试获取URL批次（只读操作）
                # 直接使用当前模式的客户端
                if mode_name in self.clients and self.clients[mode_name]:
                    urls = await self.clients[mode_name].get_pages_batch(3)
                else:
                    raise Exception(f"Client for {mode_name} mode not available")
                
                end_time = time.perf_counter()
                duration = end_time - start_time
                
                print(f"  ✅ 获取URL批次: {len(urls)}个URL ({duration:.4f}s)")
                
                self.results.append(TestResult(
                    mode=mode_name,
                    test_name="operations_layer",
                    success=True,
                    result=f"{len(urls)} URLs",
                    duration=duration
                ))
                
                # 恢复环境变量
                if original_mode:
                    os.environ['DB_ACCESS_MODE'] = original_mode
                else:
                    os.environ.pop('DB_ACCESS_MODE', None)
                    
            except Exception as e:
                print(f"  ❌ 操作层测试失败: {e}")
                self.results.append(TestResult(
                    mode=mode_name,
                    test_name="operations_layer",
                    success=False,
                    error=str(e)
                ))
    
    def generate_compatibility_report(self):
        """生成兼容性报告"""
        print("\n" + "="*80)
        print("🎯 三种模式兼容性测试报告")
        print("="*80)
        
        # 按模式分组结果
        mode_results = {}
        for result in self.results:
            if result.mode not in mode_results:
                mode_results[result.mode] = []
            mode_results[result.mode].append(result)
        
        # 生成每个模式的报告
        for mode_name in ['local', 'remote', 'cloud']:
            if mode_name not in mode_results:
                print(f"\n🔴 {mode_name.upper()} 模式: 未测试")
                continue
                
            results = mode_results[mode_name]
            success_count = sum(1 for r in results if r.success)
            total_count = len(results)
            success_rate = success_count / total_count * 100 if total_count > 0 else 0
            
            if success_rate == 100:
                status = "🟢 完全兼容"
            elif success_rate >= 75:
                status = "🟡 基本兼容"
            elif success_rate >= 50:
                status = "🟠 部分兼容"
            else:
                status = "🔴 不兼容"
            
            print(f"\n{status} {mode_name.upper()} 模式:")
            print(f"  成功率: {success_rate:.1f}% ({success_count}/{total_count})")
            
            # 显示详细结果
            for result in results:
                if result.success:
                    print(f"  ✅ {result.test_name}: {result.duration:.4f}s")
                else:
                    print(f"  ❌ {result.test_name}: {result.error}")
        
        # 总体兼容性评估
        total_success = sum(1 for r in self.results if r.success)
        total_tests = len(self.results)
        overall_rate = total_success / total_tests * 100 if total_tests > 0 else 0
        
        print(f"\n🏆 总体兼容性评估:")
        print(f"  总成功率: {overall_rate:.1f}% ({total_success}/{total_tests})")
        
        if overall_rate >= 90:
            grade = "优秀 (A)"
            color = "🟢"
        elif overall_rate >= 75:
            grade = "良好 (B)"
            color = "🟡"
        elif overall_rate >= 60:
            grade = "一般 (C)"
            color = "🟠"
        else:
            grade = "较差 (D)"
            color = "🔴"
        
        print(f"  兼容性等级: {color} {grade}")
        
        # 使用建议
        print(f"\n💡 使用建议:")
        working_modes = [mode for mode in ['local', 'remote', 'cloud'] 
                        if mode in mode_results and 
                        sum(1 for r in mode_results[mode] if r.success) / len(mode_results[mode]) >= 0.75]
        
        if working_modes:
            print(f"  ✅ 推荐使用模式: {', '.join(working_modes)}")
        else:
            print(f"  ⚠️ 所有模式都存在兼容性问题，需要进一步调试")
    
    async def run_all_tests(self):
        """运行所有兼容性测试"""
        print("🚀 开始三种数据库模式兼容性测试")
        print("="*80)
        print("测试模式: local (本地直连) | remote (HTTP API) | cloud (云端直连)")
        print("测试类型: 只读测试，不影响生产数据")
        print("="*80)
        
        try:
            await self.setup_all_modes()
            await self.test_basic_connectivity()
            await self.test_read_operations()
            await self.test_parameterized_queries()
            await self.test_operations_layer()
            
            self.generate_compatibility_report()
            
        except Exception as e:
            print(f"❌ 测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup_all_modes()


async def main():
    """主函数"""
    test_suite = ThreeModeCompatibilityTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
