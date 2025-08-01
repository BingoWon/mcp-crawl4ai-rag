#!/usr/bin/env python3
"""
PgBouncer监控和管理工具
PgBouncer monitoring and management tool
"""

import asyncio
import asyncpg
import sys
from datetime import datetime

class PgBouncerMonitor:
    def __init__(self):
        self.pgbouncer_dsn = "postgresql://bingo:xRdtkHIa53nYMWJ@localhost:6432/pgbouncer"
        self.postgres_dsn = "postgresql://bingo:xRdtkHIa53nYMWJ@localhost:5432/crawl4ai_rag"
    
    async def connect_pgbouncer(self):
        """连接到PgBouncer管理界面"""
        try:
            return await asyncpg.connect(self.pgbouncer_dsn)
        except Exception as e:
            print(f"❌ 无法连接到PgBouncer: {e}")
            return None
    
    async def connect_postgres(self):
        """直接连接到PostgreSQL"""
        try:
            return await asyncpg.connect(self.postgres_dsn)
        except Exception as e:
            print(f"❌ 无法连接到PostgreSQL: {e}")
            return None
    
    async def show_pools(self):
        """显示连接池状态"""
        conn = await self.connect_pgbouncer()
        if not conn:
            return
        
        try:
            print("🏊 连接池状态")
            print("=" * 60)
            pools = await conn.fetch("SHOW POOLS")
            
            print(f"{'数据库':<15} {'用户':<10} {'活跃':<6} {'等待':<6} {'服务器':<8} {'最大':<6}")
            print("-" * 60)
            
            for pool in pools:
                print(f"{pool['database']:<15} {pool['user']:<10} {pool['cl_active']:<6} "
                      f"{pool['cl_waiting']:<6} {pool['sv_active']:<8} {pool['maxwait']:<6}")
            
        except Exception as e:
            print(f"❌ 查询连接池失败: {e}")
        finally:
            await conn.close()
    
    async def show_clients(self):
        """显示客户端连接"""
        conn = await self.connect_pgbouncer()
        if not conn:
            return
        
        try:
            print("\n👥 客户端连接")
            print("=" * 60)
            clients = await conn.fetch("SHOW CLIENTS")
            
            print(f"{'类型':<10} {'用户':<10} {'数据库':<15} {'状态':<10} {'地址':<15}")
            print("-" * 60)
            
            for client in clients[:10]:  # 只显示前10个
                print(f"{client['type']:<10} {client['user']:<10} {client['database']:<15} "
                      f"{client['state']:<10} {client['addr']:<15}")
            
            if len(clients) > 10:
                print(f"... 还有 {len(clients) - 10} 个连接")
            
        except Exception as e:
            print(f"❌ 查询客户端连接失败: {e}")
        finally:
            await conn.close()
    
    async def show_servers(self):
        """显示服务器连接"""
        conn = await self.connect_pgbouncer()
        if not conn:
            return
        
        try:
            print("\n🖥️  服务器连接")
            print("=" * 60)
            servers = await conn.fetch("SHOW SERVERS")
            
            print(f"{'类型':<10} {'用户':<10} {'数据库':<15} {'状态':<10} {'地址':<15}")
            print("-" * 60)
            
            for server in servers:
                print(f"{server['type']:<10} {server['user']:<10} {server['database']:<15} "
                      f"{server['state']:<10} {server['addr']:<15}")
            
        except Exception as e:
            print(f"❌ 查询服务器连接失败: {e}")
        finally:
            await conn.close()
    
    async def show_stats(self):
        """显示统计信息"""
        conn = await self.connect_pgbouncer()
        if not conn:
            return
        
        try:
            print("\n📊 统计信息")
            print("=" * 60)
            stats = await conn.fetch("SHOW STATS")
            
            for stat in stats:
                if stat['database'] == 'crawl4ai_rag':
                    print(f"数据库: {stat['database']}")
                    print(f"总请求: {stat['total_xact_count']}")
                    print(f"总查询: {stat['total_query_count']}")
                    print(f"总接收: {stat['total_received']} bytes")
                    print(f"总发送: {stat['total_sent']} bytes")
                    print(f"平均请求时间: {stat['avg_xact_time']} µs")
                    print(f"平均查询时间: {stat['avg_query_time']} µs")
            
        except Exception as e:
            print(f"❌ 查询统计信息失败: {e}")
        finally:
            await conn.close()
    
    async def compare_connections(self):
        """比较PgBouncer和直连PostgreSQL的连接数"""
        print("\n🔍 连接数对比")
        print("=" * 60)
        
        # 检查PgBouncer连接
        pgb_conn = await self.connect_pgbouncer()
        if pgb_conn:
            try:
                pools = await pgb_conn.fetch("SHOW POOLS")
                clients = await pgb_conn.fetch("SHOW CLIENTS")
                servers = await pgb_conn.fetch("SHOW SERVERS")
                
                total_clients = len(clients)
                total_servers = len(servers)
                active_clients = len([c for c in clients if c['state'] == 'active'])
                active_servers = len([s for s in servers if s['state'] == 'active'])
                
                print(f"PgBouncer:")
                print(f"  客户端连接: {total_clients} (活跃: {active_clients})")
                print(f"  服务器连接: {total_servers} (活跃: {active_servers})")
                
            except Exception as e:
                print(f"❌ 查询PgBouncer连接失败: {e}")
            finally:
                await pgb_conn.close()
        
        # 检查PostgreSQL直连
        pg_conn = await self.connect_postgres()
        if pg_conn:
            try:
                result = await pg_conn.fetchrow("""
                    SELECT count(*) as total,
                           count(*) FILTER (WHERE state = 'active') as active,
                           count(*) FILTER (WHERE state = 'idle') as idle
                    FROM pg_stat_activity 
                    WHERE datname = 'crawl4ai_rag'
                """)
                
                print(f"PostgreSQL直连:")
                print(f"  总连接: {result['total']}")
                print(f"  活跃: {result['active']}")
                print(f"  空闲: {result['idle']}")
                
            except Exception as e:
                print(f"❌ 查询PostgreSQL连接失败: {e}")
            finally:
                await pg_conn.close()
    
    async def monitor_loop(self, interval=10):
        """监控循环"""
        print(f"🔄 开始监控 (每{interval}秒刷新)")
        print("按 Ctrl+C 停止监控")
        
        try:
            while True:
                print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                await self.show_pools()
                await self.compare_connections()
                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            print("\n👋 监控已停止")

async def main():
    """主函数"""
    monitor = PgBouncerMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "pools":
            await monitor.show_pools()
        elif command == "clients":
            await monitor.show_clients()
        elif command == "servers":
            await monitor.show_servers()
        elif command == "stats":
            await monitor.show_stats()
        elif command == "compare":
            await monitor.compare_connections()
        elif command == "monitor":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            await monitor.monitor_loop(interval)
        else:
            print("❌ 未知命令")
            print_usage()
    else:
        # 默认显示所有信息
        await monitor.show_pools()
        await monitor.show_clients()
        await monitor.show_servers()
        await monitor.show_stats()
        await monitor.compare_connections()

def print_usage():
    """打印使用说明"""
    print("PgBouncer监控工具")
    print("用法:")
    print("  python3 pgbouncer_monitor.py [命令]")
    print("")
    print("命令:")
    print("  pools     - 显示连接池状态")
    print("  clients   - 显示客户端连接")
    print("  servers   - 显示服务器连接")
    print("  stats     - 显示统计信息")
    print("  compare   - 比较连接数")
    print("  monitor [间隔] - 持续监控 (默认10秒)")
    print("")
    print("示例:")
    print("  python3 pgbouncer_monitor.py pools")
    print("  python3 pgbouncer_monitor.py monitor 5")

if __name__ == "__main__":
    asyncio.run(main())
