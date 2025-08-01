"""
Database Client - Simple PostgreSQL Interface

This module provides a simple async PostgreSQL database client for the Apple RAG system.

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

    async def insert_page(self, url: str) -> bool:
        """Insert URL if not exists. Returns True if inserted."""
        try:
            result = await self.execute_command(
                "INSERT INTO pages (url, crawl_count, content, last_crawled_at) VALUES ($1, 0, '', NULL) ON CONFLICT (url) DO NOTHING",
                url
            )
            return "INSERT 0 1" in result
        except Exception:
            return False

    async def get_pages_batch(self, batch_size: int = 5) -> List[str]:
        """Get batch of URLs for crawling with atomic operations"""
        lock_id = 12345

        async with self.pool.acquire() as conn:
            await conn.execute("SELECT pg_advisory_lock($1)", lock_id)

            try:
                results = await conn.fetch("""
                    UPDATE pages
                    SET crawl_count = crawl_count + 1,
                        last_crawled_at = NOW()
                    WHERE url IN (
                        SELECT url FROM pages
                        ORDER BY crawl_count ASC, last_crawled_at ASC NULLS FIRST
                        LIMIT $1
                        FOR UPDATE SKIP LOCKED
                    )
                    RETURNING url
                """, batch_size)

                return [row['url'] for row in results]

            finally:
                await conn.execute("SELECT pg_advisory_unlock($1)", lock_id)

    async def get_process_urls_batch(self, batch_size: int = 5) -> List[Tuple[str, str]]:
        """Get batch of URLs and content for processing with atomic operations"""
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT url, content
                FROM pages
                WHERE content != '' AND content IS NOT NULL
                ORDER BY last_crawled_at DESC
                LIMIT $1
            """, batch_size)

            return [(row['url'], row['content']) for row in results]

    async def update_pages_batch(self, updates: List[Tuple[str, str]]) -> None:
        """Update pages content in batch"""
        if not updates:
            return

        await self.execute_many(
            "UPDATE pages SET content = $2, updated_at = NOW() WHERE url = $1",
            updates
        )

    async def insert_chunks(self, data: List[Dict[str, Any]]) -> None:
        """Insert chunks data in batch"""
        if not data:
            return

        values = [(item['url'], item['content'], item.get('embedding')) for item in data]
        await self.execute_many(
            "INSERT INTO chunks (url, content, embedding) VALUES ($1, $2, $3)",
            values
        )


def create_database_client(config: Optional[DatabaseConfig] = None) -> DatabaseClient:
    """Factory function to create database client"""
    config = config or DatabaseConfig.from_env()
    return DatabaseClient(config)