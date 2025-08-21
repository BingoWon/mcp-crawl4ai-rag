#!/usr/bin/env python3
"""
VPS HNSW 索引创建脚本
直接在 VPS 上运行，无需额外依赖

使用方法：
1. 将此脚本复制到 VPS 上
2. 修改下面的数据库配置
3. 运行: python3 vps_hnsw_creator.py
"""

import asyncio
import asyncpg
import sys
from datetime import datetime
import os

# ============================================================================
# 数据库配置 - 请修改为你的实际配置
# ============================================================================
DB_CONFIG = {
    'host': '198.12.70.36',
    'port': 5432,
    'database': 'apple_rag_db',
    'user': 'apple_rag_user',
    'password': 'REDACTED_PASSWORD',  # 请填入你的密码
}

# ============================================================================
# 日志函数
# ============================================================================
def log_info(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"🔵 [INFO] {timestamp} - {message}")

def log_success(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"✅ [SUCCESS] {timestamp} - {message}")

def log_warning(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"⚠️  [WARNING] {timestamp} - {message}")

def log_error(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"❌ [ERROR] {timestamp} - {message}")

# ============================================================================
# 主要功能函数
# ============================================================================
async def create_hnsw_index():
    """创建 HNSW 索引"""
    
    print("=" * 80)
    print("🚀 VPS HNSW 索引创建工具")
    print("=" * 80)
    
    log_info("开始 HNSW 索引创建流程")
    
    # 检查会话类型
    if os.getenv('STY'):
        log_info(f"✅ 检测到 screen 会话: {os.getenv('STY')}")
    elif os.getenv('TMUX'):
        log_info("✅ 检测到 tmux 会话")
    else:
        log_warning("⚠️  未检测到持久会话，建议使用 screen 或 tmux")
        response = input("是否继续？(y/N): ")
        if response.lower() != 'y':
            log_info("用户取消操作")
            return False
    
    conn = None
    try:
        # ========================================================================
        # 第一步：连接数据库
        # ========================================================================
        log_info("连接数据库...")
        conn = await asyncpg.connect(**DB_CONFIG)
        log_success("数据库连接成功")
        
        # ========================================================================
        # 第二步：检查数据状态
        # ========================================================================
        log_info("检查数据状态...")
        
        # 检查总记录数
        total_count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
        embedding_count = await conn.fetchval("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL")
        
        log_info(f"数据库状态:")
        log_info(f"  - 总记录数: {total_count:,}")
        log_info(f"  - 有 embedding 的记录: {embedding_count:,}")
        
        if embedding_count == 0:
            log_error("没有找到 embedding 数据，无法创建索引")
            return False
        
        # ========================================================================
        # 第三步：检查并删除现有向量索引
        # ========================================================================
        log_info("检查现有向量索引...")
        
        existing_indexes = await conn.fetch("""
            SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) as size
            FROM pg_indexes 
            WHERE tablename = 'chunks' 
            AND (indexdef ILIKE '%hnsw%' OR indexdef ILIKE '%ivfflat%' OR indexdef ILIKE '%vector%')
            AND indexname != 'chunks_pkey'
        """)
        
        if existing_indexes:
            log_warning(f"找到 {len(existing_indexes)} 个现有向量索引:")
            for idx in existing_indexes:
                log_warning(f"  - {idx['indexname']} (大小: {idx['size']})")
            
            log_info("删除现有向量索引...")
            for idx in existing_indexes:
                index_name = idx['indexname']
                log_info(f"  删除索引: {index_name}")
                await conn.execute(f"DROP INDEX IF EXISTS {index_name}")
            
            log_success("现有向量索引删除完成")
        else:
            log_info("没有找到现有向量索引")
        
        # ========================================================================
        # 第四步：优化数据库参数
        # ========================================================================
        log_info("优化数据库参数...")
        
        # 显示当前参数
        current_maintenance = await conn.fetchval("SELECT current_setting('maintenance_work_mem')")
        current_workers = await conn.fetchval("SELECT current_setting('max_parallel_maintenance_workers')")
        current_work = await conn.fetchval("SELECT current_setting('work_mem')")
        
        log_info("当前参数:")
        log_info(f"  - maintenance_work_mem: {current_maintenance}")
        log_info(f"  - max_parallel_maintenance_workers: {current_workers}")
        log_info(f"  - work_mem: {current_work}")
        
        # 设置优化参数
        await conn.execute("SET maintenance_work_mem = '2GB'")
        await conn.execute("SET max_parallel_maintenance_workers = 3")
        await conn.execute("SET work_mem = '512MB'")
        await conn.execute("SET random_page_cost = 1.1")
        
        log_success("数据库参数优化完成")
        
        # ========================================================================
        # 第五步：创建 HNSW 索引
        # ========================================================================
        log_info("开始创建 HNSW 索引...")
        log_warning("此过程可能需要 2-6 小时，请保持连接稳定")
        
        start_time = datetime.now()
        log_info(f"索引创建开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 创建 HNSW 索引
        await conn.execute("""
            CREATE INDEX CONCURRENTLY idx_chunks_embedding_hnsw 
            ON chunks USING hnsw (embedding halfvec_cosine_ops) 
            WITH (m = 16, ef_construction = 64)
        """)
        
        end_time = datetime.now()
        duration = end_time - start_time
        log_success("🎉 HNSW 索引创建完成！")
        log_success(f"总耗时: {duration}")
        
        # ========================================================================
        # 第六步：验证索引
        # ========================================================================
        log_info("验证索引创建结果...")
        
        # 检查索引
        index_info = await conn.fetch("""
            SELECT 
                indexname,
                pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
            FROM pg_indexes 
            WHERE tablename = 'chunks' 
            AND indexname = 'idx_chunks_embedding_hnsw'
        """)
        
        if index_info:
            for info in index_info:
                log_success(f"索引验证成功: {info['indexname']}")
                log_success(f"索引大小: {info['index_size']}")
        else:
            log_error("索引验证失败：未找到创建的索引")
            return False
        
        # 性能测试
        log_info("执行性能测试...")
        test_vector = await conn.fetchrow("SELECT embedding FROM chunks WHERE embedding IS NOT NULL LIMIT 1")
        
        if test_vector:
            search_results = await conn.fetch("""
                SELECT id, url, 1 - (embedding <=> $1) as similarity
                FROM chunks
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> $1
                LIMIT 5
            """, test_vector['embedding'])
            
            log_success(f"性能测试完成，返回 {len(search_results)} 条结果")
            for i, result in enumerate(search_results[:3]):
                log_info(f"  {i+1}. 相似度: {result['similarity']:.4f}")
        
        # ========================================================================
        # 完成
        # ========================================================================
        print("\n" + "=" * 80)
        log_success("🎉 HNSW 索引创建流程全部完成！")
        print("=" * 80)
        
        log_info("后续建议:")
        log_info("1. 监控查询性能变化")
        log_info("2. 定期备份数据库")
        log_info("3. 观察索引使用情况")
        
        return True
        
    except Exception as e:
        log_error(f"操作失败: {e}")
        return False
        
    finally:
        if conn:
            await conn.close()

# ============================================================================
# 监控进度函数（可选）
# ============================================================================
async def monitor_progress():
    """监控索引创建进度"""
    conn = None
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # 查看正在运行的索引创建查询
        active_queries = await conn.fetch("""
            SELECT 
                pid,
                usename,
                state,
                query_start,
                NOW() - query_start as duration,
                LEFT(query, 100) as query_preview
            FROM pg_stat_activity 
            WHERE state = 'active' 
            AND query ILIKE '%CREATE INDEX%'
            AND query ILIKE '%hnsw%'
        """)
        
        if active_queries:
            print("🔍 正在运行的索引创建查询:")
            for query in active_queries:
                print(f"  - PID: {query['pid']}, 用户: {query['usename']}")
                print(f"  - 运行时间: {query['duration']}")
                print(f"  - 查询: {query['query_preview']}...")
        else:
            print("📋 没有找到正在运行的索引创建查询")
        
        # 查看数据库大小
        db_size = await conn.fetchval("SELECT pg_size_pretty(pg_database_size(current_database()))")
        print(f"💾 数据库大小: {db_size}")
        
    except Exception as e:
        print(f"❌ 监控失败: {e}")
    finally:
        if conn:
            await conn.close()

# ============================================================================
# 主程序
# ============================================================================
async def main():
    """主程序"""
    if len(sys.argv) > 1 and sys.argv[1] == 'monitor':
        await monitor_progress()
    else:
        success = await create_hnsw_index()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_warning("用户中断操作")
        sys.exit(1)
    except Exception as e:
        log_error(f"未预期的错误: {e}")
        sys.exit(1)
