#!/usr/bin/env python3
"""
更新项目配置以使用PgBouncer
Update project configuration to use PgBouncer
"""

import os
import re
from pathlib import Path

def update_env_file():
    """更新.env文件中的数据库端口"""
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env文件不存在")
        return
    
    content = env_file.read_text()
    
    # 更新本地数据库端口为PgBouncer端口
    content = re.sub(r'LOCAL_DB_PORT=5432', 'LOCAL_DB_PORT=6432', content)
    
    # 添加PgBouncer配置注释
    if 'PGBOUNCER_PORT' not in content:
        content += '\n# PgBouncer Configuration\n'
        content += 'PGBOUNCER_PORT=6432\n'
        content += 'POSTGRES_DIRECT_PORT=5432\n'
    
    env_file.write_text(content)
    print("✅ 更新.env文件 - 数据库端口改为6432 (PgBouncer)")

def update_api_config():
    """更新API服务配置"""
    api_file = Path('api/postgres_proxy.py')
    if not api_file.exists():
        print("❌ API配置文件不存在")
        return
    
    content = api_file.read_text()
    
    # 更新默认端口
    content = re.sub(
        r"f\"{os\.getenv\('PGPORT', '5432'\)}/\"",
        "f\"{os.getenv('PGPORT', '6432')}/\"",
        content
    )
    
    # 更新连接池配置 - 可以增加连接数，因为PgBouncer会管理
    content = re.sub(
        r'min_size=5,\s*max_size=20,',
        'min_size=10,\n        max_size=50,',
        content
    )
    
    api_file.write_text(content)
    print("✅ 更新API服务配置 - 端口改为6432，增加连接池大小")

def update_database_config():
    """更新数据库配置"""
    config_file = Path('src/database/config.py')
    if not config_file.exists():
        print("❌ 数据库配置文件不存在")
        return
    
    content = config_file.read_text()
    
    # 更新默认端口
    content = re.sub(
        r"local_port: int = int\(os\.getenv\('LOCAL_DB_PORT', '5432'\)\)",
        "local_port: int = int(os.getenv('LOCAL_DB_PORT', '6432'))",
        content
    )
    
    # 可以增加连接池大小，因为PgBouncer会管理实际的数据库连接
    content = re.sub(
        r'max_pool_size: int = 10',
        'max_pool_size: int = 30',
        content
    )
    
    config_file.write_text(content)
    print("✅ 更新数据库配置 - 端口改为6432，增加连接池大小")

def create_pgbouncer_docker_config():
    """创建PgBouncer的Docker配置"""
    docker_compose = Path('docker-compose.yml')
    if not docker_compose.exists():
        print("❌ docker-compose.yml不存在")
        return
    
    content = docker_compose.read_text()
    
    # 在postgres服务后添加pgbouncer服务
    pgbouncer_service = '''
  # PgBouncer连接池
  pgbouncer:
    image: pgbouncer/pgbouncer:latest
    environment:
      DATABASES_HOST: postgres
      DATABASES_PORT: 5432
      DATABASES_USER: bingo
      DATABASES_PASSWORD: xRdtkHIa53nYMWJ
      DATABASES_DBNAME: crawl4ai_rag
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 200
      DEFAULT_POOL_SIZE: 20
      MIN_POOL_SIZE: 5
      RESERVE_POOL_SIZE: 5
      AUTH_TYPE: md5
    ports:
      - "6432:5432"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "psql", "-h", "localhost", "-U", "bingo", "-d", "pgbouncer", "-c", "SHOW POOLS;"]
      interval: 30s
      timeout: 10s
      retries: 3
'''
    
    # 在volumes之前插入pgbouncer服务
    content = content.replace('volumes:', pgbouncer_service + '\nvolumes:')
    
    # 更新gateway服务连接到pgbouncer
    content = re.sub(
        r'PGHOST: postgres\s*PGPORT: 5432',
        'PGHOST: pgbouncer\n      PGPORT: 5432',
        content
    )
    
    docker_compose.write_text(content)
    print("✅ 更新Docker配置 - 添加PgBouncer服务")

def main():
    """主函数"""
    print("🔧 更新项目配置以使用PgBouncer")
    print("=" * 40)
    
    # 检查是否在正确的目录
    if not Path('.env').exists():
        print("❌ 请在项目根目录运行此脚本")
        return
    
    # 执行更新
    update_env_file()
    update_api_config()
    update_database_config()
    create_pgbouncer_docker_config()
    
    print("\n🎉 配置更新完成！")
    print("\n下一步操作:")
    print("1. 安装PgBouncer: ./pgbouncer/install_pgbouncer.sh")
    print("2. 重启API服务: launchctl kickstart -k gui/$(id -u)/com.apple-rag.api")
    print("3. 测试连接: psql -h localhost -p 6432 -U bingo -d crawl4ai_rag")
    print("4. 运行爬虫测试连接池效果")

if __name__ == "__main__":
    main()
