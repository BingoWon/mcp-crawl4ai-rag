#!/usr/bin/env python3
"""
数据库公网访问监控工具
监控本地数据库的公网访问状态
"""

import asyncio
import aiohttp
import sys
from datetime import datetime
import json

class DatabaseAccessMonitor:
    def __init__(self):
        self.local_api_url = "http://localhost:8000"
        self.public_api_url = "https://db.apple-rag.com"
        self.api_key = "ZBYlBx77H9Sc87k"
    
    async def check_local_api(self):
        """检查本地API状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.local_api_url}/health", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "healthy":
                            print("✅ 本地API: 正常运行")
                            return True
                    print("❌ 本地API: 响应异常")
                    return False
        except Exception as e:
            print(f"❌ 本地API: 连接失败 - {e}")
            return False
    
    async def check_public_access(self):
        """检查公网访问状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.public_api_url}/health", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "healthy":
                            print("✅ 公网访问: 正常运行")
                            return True
                    print("❌ 公网访问: 响应异常")
                    return False
        except Exception as e:
            print(f"❌ 公网访问: 连接失败 - {e}")
            return False
    
    async def check_database_connection(self):
        """检查数据库连接"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json"
                }
                data = {"query": "SELECT 1 as test"}
                
                async with session.post(
                    f"{self.public_api_url}/query",
                    headers=headers,
                    json=data,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("success"):
                            print("✅ 数据库连接: 正常")
                            return True
                    print("❌ 数据库连接: 查询失败")
                    return False
        except Exception as e:
            print(f"❌ 数据库连接: 失败 - {e}")
            return False
    
    async def get_database_stats(self):
        """获取数据库统计信息"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.public_api_url}/stats", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        print("📊 数据库统计:")
                        for key, value in data.items():
                            if isinstance(value, (int, float)):
                                print(f"   {key}: {value:,}")
                            else:
                                print(f"   {key}: {value}")
                        return True
                    else:
                        print("❌ 无法获取数据库统计")
                        return False
        except Exception as e:
            print(f"❌ 获取统计失败: {e}")
            return False
    
    async def test_api_performance(self):
        """测试API性能"""
        print("⚡ 测试API性能...")
        
        # 测试本地API性能
        try:
            start_time = datetime.now()
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.local_api_url}/health") as response:
                    await response.json()
            local_time = (datetime.now() - start_time).total_seconds() * 1000
            print(f"   本地API响应时间: {local_time:.1f}ms")
        except Exception as e:
            print(f"   本地API测试失败: {e}")
        
        # 测试公网API性能
        try:
            start_time = datetime.now()
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.public_api_url}/health") as response:
                    await response.json()
            public_time = (datetime.now() - start_time).total_seconds() * 1000
            print(f"   公网API响应时间: {public_time:.1f}ms")
        except Exception as e:
            print(f"   公网API测试失败: {e}")
    
    async def monitor_once(self):
        """执行一次完整监控"""
        print(f"🔍 数据库公网访问监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 检查各项服务
        local_ok = await self.check_local_api()
        public_ok = await self.check_public_access()
        db_ok = await self.check_database_connection()
        
        print()
        
        # 获取统计信息
        if public_ok:
            await self.get_database_stats()
            print()
        
        # 性能测试
        if local_ok or public_ok:
            await self.test_api_performance()
            print()
        
        # 总结
        if local_ok and public_ok and db_ok:
            print("🎉 所有服务正常 - 数据库公网访问完全可用！")
        else:
            print("⚠️  部分服务异常 - 请检查相关配置")
        
        return local_ok and public_ok and db_ok
    
    async def monitor_loop(self, interval=30):
        """持续监控模式"""
        print(f"🔄 开始持续监控 (每{interval}秒检查一次)")
        print("按 Ctrl+C 停止监控")
        print()
        
        try:
            while True:
                await self.monitor_once()
                print()
                print(f"⏳ 等待{interval}秒后继续监控...")
                await asyncio.sleep(interval)
                print()
        except KeyboardInterrupt:
            print("\n👋 监控已停止")

async def main():
    """主函数"""
    monitor = DatabaseAccessMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "loop":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            await monitor.monitor_loop(interval)
        elif command == "stats":
            await monitor.get_database_stats()
        elif command == "performance":
            await monitor.test_api_performance()
        else:
            print("❌ 未知命令")
            print_usage()
    else:
        # 默认执行一次监控
        await monitor.monitor_once()

def print_usage():
    """打印使用说明"""
    print("数据库公网访问监控工具")
    print("用法:")
    print("  python3 monitor_access.py [命令]")
    print("")
    print("命令:")
    print("  (无)      - 执行一次完整监控")
    print("  loop [间隔] - 持续监控 (默认30秒)")
    print("  stats     - 获取数据库统计")
    print("  performance - 测试API性能")
    print("")
    print("示例:")
    print("  python3 monitor_access.py")
    print("  python3 monitor_access.py loop 10")
    print("  python3 monitor_access.py stats")

if __name__ == "__main__":
    asyncio.run(main())
