"""
PostgreSQL Client
PostgreSQL客户端

Modern async PostgreSQL client with pgvector support.
现代化异步PostgreSQL客户端，支持pgvector。
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

            # Create pages table with crawl_count and process_count
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    url TEXT UNIQUE NOT NULL,
                    crawl_count INTEGER DEFAULT 0,
                    process_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_crawled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    content TEXT NOT NULL
                )
            """)

            # Migrate existing tables to new schema
            try:
                # Add process_count column if it doesn't exist
                await conn.execute("""
                    ALTER TABLE pages
                    ADD COLUMN IF NOT EXISTS process_count INTEGER DEFAULT 0
                """)

                # Rename updated_at to last_crawled_at if needed
                await conn.execute("""
                    ALTER TABLE pages
                    RENAME COLUMN updated_at TO last_crawled_at
                """)
            except Exception:
                # Column might already be renamed
                pass

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

            # Create indexes for performance
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
