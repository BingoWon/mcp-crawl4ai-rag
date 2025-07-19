"""
PostgreSQL Client - Modern Async Database Interface

This module provides a high-performance async PostgreSQL client optimized for
vector operations and Apple Developer Documentation storage.

Features:
- Async connection pool management with asyncpg
- pgvector extension support for vector similarity search
- Optimized for Apple Developer Documentation schema
- JSON-serializable result formatting
- Comprehensive error handling and logging
- Connection pool optimization for MCP server usage

Database Schema Support:
- pages: Full page content with metadata (id, url, content, crawl_count)
- chunks: Document fragments with embeddings (id, url, content, embedding)
- pgvector: Vector similarity operations with cosine distance

Performance:
- Connection pooling for optimal resource usage
- Async-first design for high concurrency
- Efficient vector operations with proper type handling
- Automatic serialization of UUID and datetime objects

Usage:
Provides execute_query() method for parameterized SQL execution with
automatic result serialization and comprehensive error handling.
"""

import asyncpg
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from .config import PostgreSQLConfig


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


class PostgreSQLClient:
    """Modern async PostgreSQL client with pgvector support"""
    
    def __init__(self, config: Optional[PostgreSQLConfig] = None):
        self.config = config or PostgreSQLConfig.from_env()
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize connection pool and setup database"""
        if self._initialized:
            return
            
        try:
            self.pool = await asyncpg.create_pool(**self.config.to_dict())
            await self._setup_database()
            self._initialized = True
            from utils.logger import setup_logger
            logger = setup_logger(__name__)
            logger.info(f"✅ PostgreSQL client initialized: {self.config.host}:{self.config.port}/{self.config.database}")

        except Exception as e:
            from utils.logger import setup_logger
            logger = setup_logger(__name__)
            logger.error(f"❌ Failed to initialize PostgreSQL client: {e}")
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
                    embedding vector(2560),
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
