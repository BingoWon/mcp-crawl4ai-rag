"""
Database Operations
数据库操作

High-level database operations for crawled content and RAG functionality.
爬取内容和RAG功能的高级数据库操作。
"""

import json
from typing import List, Dict, Any, Optional
from .client import PostgreSQLClient


class DatabaseOperations:
    """High-level database operations"""
    
    def __init__(self, client: PostgreSQLClient):
        self.client = client
    
    # ============================================================================
    # CRAWLED PAGES OPERATIONS
    # ============================================================================
    
    async def insert_crawled_pages(self, data: List[Dict[str, Any]]) -> None:
        """Insert crawled pages data"""
        if not data:
            return
            
        await self.client.execute_many("""
            INSERT INTO crawled_pages (url, chunk_number, content, metadata, source_id, embedding)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (url, chunk_number) DO UPDATE SET
                content = EXCLUDED.content,
                metadata = EXCLUDED.metadata,
                source_id = EXCLUDED.source_id,
                embedding = EXCLUDED.embedding
        """, [
            (
                item['url'],
                item['chunk_number'],
                item['content'],
                json.dumps(item['metadata']) if item.get('metadata') else None,
                item['source_id'],
                item.get('embedding')
            )
            for item in data
        ])
    
    async def search_documents_vector(self, query_embedding: List[float], 
                                    match_count: int = 10, 
                                    source_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Vector similarity search in crawled_pages"""
        if source_filter:
            return await self.client.execute_query("""
                SELECT id, url, chunk_number, content, metadata, source_id,
                       1 - (embedding <=> $1::vector) as similarity
                FROM crawled_pages
                WHERE source_id = $2 AND embedding IS NOT NULL
                ORDER BY embedding <=> $1::vector
                LIMIT $3
            """, query_embedding, source_filter, match_count)
        else:
            return await self.client.execute_query("""
                SELECT id, url, chunk_number, content, metadata, source_id,
                       1 - (embedding <=> $1::vector) as similarity
                FROM crawled_pages
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """, query_embedding, match_count)
    
    async def search_documents_keyword(self, query: str, 
                                     match_count: int = 10,
                                     source_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Keyword search in crawled_pages"""
        if source_filter:
            return await self.client.execute_query("""
                SELECT id, url, chunk_number, content, metadata, source_id
                FROM crawled_pages
                WHERE content ILIKE $1 AND source_id = $2
                ORDER BY id
                LIMIT $3
            """, f'%{query}%', source_filter, match_count)
        else:
            return await self.client.execute_query("""
                SELECT id, url, chunk_number, content, metadata, source_id
                FROM crawled_pages
                WHERE content ILIKE $1
                ORDER BY id
                LIMIT $2
            """, f'%{query}%', match_count)
    
    async def url_exists(self, url: str) -> bool:
        """Check if URL already exists in crawled_pages"""
        result = await self.client.fetch_val(
            "SELECT EXISTS(SELECT 1 FROM crawled_pages WHERE url = $1)",
            url
        )
        return result
    
    # ============================================================================
    # CODE EXAMPLES OPERATIONS
    # ============================================================================
    

    

    

    
    # ============================================================================
    # SOURCES OPERATIONS
    # ============================================================================
    
    async def upsert_source(self, source_id: str, summary: str, word_count: int) -> None:
        """Insert or update source information"""
        await self.client.execute_command("""
            INSERT INTO sources (source_id, summary, total_word_count)
            VALUES ($1, $2, $3)
            ON CONFLICT (source_id) DO UPDATE SET
                summary = EXCLUDED.summary,
                total_word_count = EXCLUDED.total_word_count,
                updated_at = NOW()
        """, source_id, summary, word_count)
    
    async def get_sources(self) -> List[Dict[str, Any]]:
        """Get all sources"""
        return await self.client.execute_query(
            "SELECT * FROM sources ORDER BY source_id"
        )
    
    async def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get specific source"""
        return await self.client.fetch_one(
            "SELECT * FROM sources WHERE source_id = $1",
            source_id
        )
