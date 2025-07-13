#!/usr/bin/env python3
"""
数据库清理脚本
删除除chunks和pages之外的所有表，并清空这两个表的数据
"""

import asyncio
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.client import PostgreSQLClient


async def cleanup_database():
    """清理数据库：删除多余表，清空保留表数据"""
    
    # 定义要保留的表
    KEEP_TABLES = {'chunks', 'pages'}
    
    print("🧹 开始数据库清理操作")
    print("=" * 50)
    
    async with PostgreSQLClient() as client:
        # 1. 查询所有表
        print("📋 查询数据库中的所有表...")
        tables = await client.execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        all_tables = {table['table_name'] for table in tables}
        print(f"发现 {len(all_tables)} 个表: {sorted(all_tables)}")
        
        # 2. 识别要删除的表
        tables_to_drop = all_tables - KEEP_TABLES
        tables_to_keep = all_tables & KEEP_TABLES
        
        print(f"\n📋 要保留的表 ({len(tables_to_keep)}个): {sorted(tables_to_keep)}")
        print(f"📋 要删除的表 ({len(tables_to_drop)}个): {sorted(tables_to_drop)}")
        
        # 3. 确认操作
        if tables_to_drop:
            print(f"\n⚠️  即将删除 {len(tables_to_drop)} 个表:")
            for table in sorted(tables_to_drop):
                print(f"   - {table}")
            
            confirm = input("\n确认删除这些表吗? (yes/no): ").strip().lower()
            if confirm != 'yes':
                print("❌ 操作已取消")
                return False
        
        # 4. 删除多余表
        if tables_to_drop:
            print(f"\n🗑️  删除多余表...")
            for table in sorted(tables_to_drop):
                try:
                    await client.execute_query(f'DROP TABLE IF EXISTS "{table}" CASCADE')
                    print(f"   ✅ 删除表: {table}")
                except Exception as e:
                    print(f"   ❌ 删除表 {table} 失败: {e}")
        else:
            print("\n✅ 没有多余的表需要删除")
        
        # 5. 清空保留表的数据
        if tables_to_keep:
            print(f"\n🧽 清空保留表的数据...")
            for table in sorted(tables_to_keep):
                try:
                    # 获取清空前的记录数
                    count_before = await client.execute_query(f'SELECT COUNT(*) as count FROM "{table}"')
                    records_before = count_before[0]['count']
                    
                    # 清空表数据
                    await client.execute_query(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE')
                    
                    # 获取清空后的记录数
                    count_after = await client.execute_query(f'SELECT COUNT(*) as count FROM "{table}"')
                    records_after = count_after[0]['count']
                    
                    print(f"   ✅ 清空表 {table}: {records_before} → {records_after} 条记录")
                except Exception as e:
                    print(f"   ❌ 清空表 {table} 失败: {e}")
        
        # 6. 验证清理结果
        print(f"\n📋 验证清理结果...")
        final_tables = await client.execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        final_table_names = {table['table_name'] for table in final_tables}
        print(f"清理后的表 ({len(final_table_names)}个): {sorted(final_table_names)}")
        
        # 验证表结构
        for table in sorted(final_table_names):
            columns = await client.execute_query("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = $1 AND table_schema = 'public'
                ORDER BY ordinal_position
            """, table)
            
            column_names = [col['column_name'] for col in columns]
            print(f"   {table}表字段: {column_names}")
        
        # 验证数据清空
        for table in sorted(final_table_names):
            count = await client.execute_query(f'SELECT COUNT(*) as count FROM "{table}"')
            record_count = count[0]['count']
            print(f"   {table}表记录数: {record_count}")
        
        print(f"\n🎉 数据库清理完成!")
        print(f"✅ 保留表: {sorted(final_table_names)}")
        print(f"✅ 所有表数据已清空")
        
        return True


async def main():
    """主函数"""
    try:
        success = await cleanup_database()
        if success:
            print("\n✅ 数据库清理成功完成")
        else:
            print("\n❌ 数据库清理被取消")
        return success
    except Exception as e:
        print(f"\n❌ 数据库清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
