"""
PostgreSQL Client
PostgreSQL客户端

Modern async PostgreSQL client with pgvector support.
现代化异步PostgreSQL客户端，支持pgvector。
"""

import asyncpg
import json
from typing import List, Dict, Any, Optional
from .config import PostgreSQLConfig


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
            print(f"✅ PostgreSQL client initialized: {self.config.host}:{self.config.port}/{self.config.database}")
            
        except Exception as e:
            print(f"❌ Failed to initialize PostgreSQL client: {e}")
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
            
            # Create crawled_pages table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS crawled_pages (
                    id SERIAL PRIMARY KEY,
                    url TEXT NOT NULL,
                    chunk_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    source_id TEXT NOT NULL,
                    embedding vector(2560),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(url, chunk_number)
                )
            """)
            
            # Create sources table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id SERIAL PRIMARY KEY,
                    source_id TEXT UNIQUE NOT NULL,
                    summary TEXT,
                    total_word_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            

            
            # Create indexes for better performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_crawled_pages_source_id ON crawled_pages(source_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_crawled_pages_url ON crawled_pages(url)")

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_sources_source_id ON sources(source_id)")
            
            # Vector indexes not needed for exact search with vector(2560)
            # pgvector performs brute-force exact nearest neighbor search without indexes
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dicts"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute_command(self, command: str, *args) -> str:
        """Execute a command and return status"""
        async with self.pool.acquire() as conn:
            return await conn.execute(command, *args)
    
    async def execute_many(self, command: str, args_list: List[tuple]) -> None:
        """Execute command with multiple parameter sets"""
        async with self.pool.acquire() as conn:
            await conn.executemany(command, args_list)

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch single row as dictionary"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def fetch_val(self, query: str, *args) -> Any:
        """Fetch single value"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
