"""
Modern PostgreSQL client for Crawl4AI RAG MCP server.

This module provides a clean, async interface to PostgreSQL with pgvector support,
replacing the Supabase client with native PostgreSQL operations.
"""
import os
import asyncio
import asyncpg
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
import json


class PostgreSQLClient:
    """Modern async PostgreSQL client with pgvector support."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._connection_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DATABASE', 'crawl4ai_rag'),
            'user': os.getenv('POSTGRES_USER', os.getenv('USER', 'postgres')),
            'password': os.getenv('POSTGRES_PASSWORD', ''),
        }
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        self.pool = await asyncpg.create_pool(
            **self._connection_params,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
    
    async def close(self) -> None:
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool."""
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dicts."""
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute_command(self, command: str, *args) -> str:
        """Execute a command and return status."""
        async with self.get_connection() as conn:
            return await conn.execute(command, *args)
    
    async def call_function(self, function_name: str, *args) -> List[Dict[str, Any]]:
        """Call a PostgreSQL function and return results."""
        placeholders = ', '.join(f'${i+1}' for i in range(len(args)))
        query = f"SELECT * FROM {function_name}({placeholders})"
        return await self.execute_query(query, *args)
    
    # Table operations with modern syntax
    async def insert_batch(self, table: str, records: List[Dict[str, Any]]) -> None:
        """Insert multiple records efficiently."""
        if not records:
            return
        
        columns = list(records[0].keys())
        placeholders = ', '.join(f'${i+1}' for i in range(len(columns)))
        query = f"""
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({placeholders})
        """
        
        async with self.get_connection() as conn:
            await conn.executemany(
                query,
                [[record[col] for col in columns] for record in records]
            )
    
    async def delete_by_condition(self, table: str, condition: str, *args) -> int:
        """Delete records matching condition."""
        query = f"DELETE FROM {table} WHERE {condition}"
        result = await self.execute_command(query, *args)
        return int(result.split()[-1])  # Extract count from "DELETE n"
    
    async def select_with_filter(self, table: str, columns: str = "*", 
                                condition: str = "", *args) -> List[Dict[str, Any]]:
        """Select records with optional filtering."""
        query = f"SELECT {columns} FROM {table}"
        if condition:
            query += f" WHERE {condition}"
        return await self.execute_query(query, *args)
    
    async def upsert_record(self, table: str, record: Dict[str, Any], 
                           conflict_columns: List[str]) -> None:
        """Insert or update record on conflict."""
        columns = list(record.keys())
        values_placeholders = ', '.join(f'${i+1}' for i in range(len(columns)))
        conflict_cols = ', '.join(conflict_columns)
        
        update_set = ', '.join(
            f"{col} = EXCLUDED.{col}" 
            for col in columns if col not in conflict_columns
        )
        
        query = f"""
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({values_placeholders})
            ON CONFLICT ({conflict_cols})
            DO UPDATE SET {update_set}
        """
        
        await self.execute_command(query, *[record[col] for col in columns])


# Global client instance
_postgres_client: Optional[PostgreSQLClient] = None


async def get_postgres_client() -> PostgreSQLClient:
    """Get or create the global PostgreSQL client."""
    global _postgres_client
    if _postgres_client is None:
        _postgres_client = PostgreSQLClient()
        await _postgres_client.initialize()
    return _postgres_client


async def close_postgres_client() -> None:
    """Close the global PostgreSQL client."""
    global _postgres_client
    if _postgres_client:
        await _postgres_client.close()
        _postgres_client = None
