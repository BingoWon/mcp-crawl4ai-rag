"""
Database Client - Modern Async Interface

This module provides a high-performance async PostgreSQL client optimized for
vector operations and Apple Developer Documentation storage.

Features:
- Async connection pool for high performance
- pgvector extension support for vector similarity search
- JSON-serializable result formatting
- Comprehensive error handling and logging

Database Schema Support:
- pages: Full page content with metadata (id, url, content, crawl_count)
- chunks: Document fragments with embeddings (id, url, content, embedding)
- pgvector: Vector similarity operations with cosine distance

Performance:
- Connection pooling for efficiency
- Async-first design for concurrency
- Efficient vector operations
- Automatic serialization of UUID and datetime objects

Usage:
Provides execute_query() method for parameterized SQL execution with
automatic result serialization and error handling.
"""

import asyncpg
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from .config import DatabaseConfig, DatabaseAccessMode
from .http_client import HTTPDatabaseClient


def serialize_db_value(value):
    """Convert database values to JSON-serializable format"""
    if isinstance(value, uuid.UUID):
        return str(value)
    elif isinstance(value, datetime):
        return value.isoformat()
    elif value is None:
        return None
    else:
        return value


def serialize_db_row(row) -> Dict[str, Any]:
    """Convert database row to JSON-serializable dictionary"""
    return {key: serialize_db_value(value) for key, value in row.items()}


def create_database_client(config: Optional[DatabaseConfig] = None):
    """Factory function to create appropriate database client based on access mode"""
    config = config or DatabaseConfig.from_env()

    # 根据访问模式选择正确的客户端类型
    if config.access_mode == DatabaseAccessMode.REMOTE:
        from .http_client import HTTPDatabaseClient
        return HTTPDatabaseClient(config)
    else:
        # LOCAL 和 CLOUD 模式都使用直接连接
        return DatabaseClient(config)


class DatabaseClient:
    """Modern async PostgreSQL database client with pgvector support"""

    def __init__(self, config: Optional[DatabaseConfig] = None):
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
            logger.info(f"✅ Database client initialized ({self.config.access_mode.value}): {self.config.current_host}:{self.config.current_port}/{self.config.current_database}")

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
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
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
                    crawl_count INTEGER DEFAULT 0,
                    process_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_crawled_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
                    content TEXT NOT NULL DEFAULT ''
                )
            """)

            # Create chunks table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    url TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding halfvec(2560),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)

            # Create indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pages_url ON pages(url)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pages_crawl_count ON pages(crawl_count)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pages_process_count ON pages(process_count)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_url ON chunks(url)")
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dicts with serialized values"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [serialize_db_row(row) for row in rows]
    
    async def execute_command(self, command: str, *args) -> str:
        """Execute a command and return status"""
        async with self.pool.acquire() as conn:
            return await conn.execute(command, *args)
    
    async def execute_many(self, command: str, args_list: List[tuple]) -> None:
        """Execute command with multiple parameter sets"""
        async with self.pool.acquire() as conn:
            await conn.executemany(command, args_list)

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch single row as dictionary with serialized values"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return serialize_db_row(row) if row else None

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch all rows as list of dictionaries with serialized values"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [serialize_db_row(row) for row in rows]

    async def fetch_val(self, query: str, *args) -> Any:
        """Fetch single value"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def get_pages_batch(self, batch_size: int = 5) -> List[str]:
        """获取待爬取URL批次"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT url FROM pages
                WHERE crawl_count = 0
                ORDER BY created_at ASC
                LIMIT $1
            """, batch_size)
            return [row['url'] for row in rows]

    async def insert_page(self, url: str) -> bool:
        """Insert URL with crawl_count=0 and last_crawled_at=NULL if not exists. Returns True if inserted."""
        async with self.pool.acquire() as conn:
            try:
                result = await conn.execute("""
                    INSERT INTO pages (url, crawl_count, content, last_crawled_at)
                    VALUES ($1, 0, '', NULL)
                    ON CONFLICT (url) DO NOTHING
                """, url)
                # 检查是否有行被影响（即是否插入了新记录）
                # PostgreSQL的execute返回类似"INSERT 0 1"的字符串，其中最后的数字是affected rows
                return result.split()[-1] != '0'
            except Exception:
                return False
