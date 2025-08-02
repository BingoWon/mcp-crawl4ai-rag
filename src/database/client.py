"""
Database Client - 纯粹的PostgreSQL连接管理

提供纯粹的数据库连接和基础操作，不包含业务逻辑。

职责：
- 连接池管理
- 数据库初始化
- 基础CRUD操作
- 结果序列化

不包含：
- 业务逻辑
- 复杂查询
- 批处理策略
"""

import asyncpg
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from .config import DatabaseConfig


def serialize_db_value(value):
    """Convert database values to JSON-serializable format"""
    if isinstance(value, uuid.UUID):
        return str(value)
    elif isinstance(value, datetime):
        return value.isoformat()
    return value


def serialize_db_row(row):
    """Convert database row to JSON-serializable dictionary"""
    return {key: serialize_db_value(value) for key, value in row.items()}


class DatabaseClient:
    """
    PostgreSQL database client with connection pooling

    Simple PostgreSQL client for the Apple RAG system with optimized
    connection pooling and atomic batch operations.

    Features:
    - asyncpg connection pool for high performance
    - PostgreSQL advisory locks for atomic batch operations
    - Automatic JSON serialization of results
    - Comprehensive error handling and logging
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """Initialize PostgreSQL client with configuration"""
        self.config = config or DatabaseConfig.from_env()
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize connection pool and setup database"""
        if self._initialized:
            return

        try:
            # Validate configuration
            self.config.validate()

            # Create connection pool
            self.pool = await asyncpg.create_pool(**self.config.to_dict())
            await self._setup_database()
            self._initialized = True

            from utils.logger import setup_logger
            logger = setup_logger(__name__)
            logger.info(f"✅ Database client initialized (cloud): {self.config.host}:{self.config.port}/{self.config.database}")

        except Exception as e:
            from utils.logger import setup_logger
            logger = setup_logger(__name__)
            logger.error(f"❌ Failed to initialize database client: {e}")
            raise

    async def close(self) -> None:
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            self._initialized = False

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _setup_database(self) -> None:
        """Setup database schema and extensions"""
        async with self.pool.acquire() as conn:
            # Enable pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Create pages table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    url TEXT UNIQUE NOT NULL,
                    content TEXT DEFAULT '',
                    crawl_count INTEGER DEFAULT 0,
                    last_crawled_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Create chunks table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    url TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(2560),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Create indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pages_url ON pages(url)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pages_crawl_count ON pages(crawl_count)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_url ON chunks(url)")

    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dicts"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [serialize_db_row(row) for row in rows]

    async def execute_command(self, command: str, *args) -> str:
        """Execute a command and return status"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(command, *args)
            return result

    async def execute_many(self, command: str, args_list: List[Tuple]) -> None:
        """Execute command with multiple parameter sets"""
        async with self.pool.acquire() as conn:
            await conn.executemany(command, args_list)

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch single row as dictionary"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return serialize_db_row(row) if row else None

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch all rows as list of dictionaries"""
        return await self.execute_query(query, *args)

    async def fetch_val(self, query: str, *args) -> Any:
        """Fetch single value"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)




def create_database_client(config: Optional[DatabaseConfig] = None) -> DatabaseClient:
    """Factory function to create database client"""
    config = config or DatabaseConfig.from_env()
    return DatabaseClient(config)