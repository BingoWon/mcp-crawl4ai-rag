"""
Database Operations
数据库操作

High-level database operations for crawled content and RAG functionality.
爬取内容和RAG功能的高级数据库操作。
"""

from typing import List, Dict, Any
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
            INSERT INTO crawled_pages (url, content, embedding)
            VALUES ($1, $2, $3)
        """, [
            (
                item['url'],
                item['content'],
                item.get('embedding')
            )
            for item in data
        ])
    
    async def search_documents_vector(self, query_embedding: List[float],
                                    match_count: int = 10) -> List[Dict[str, Any]]:
        """Vector similarity search in crawled_pages"""
        return await self.client.execute_query("""
            SELECT id, url, content,
                   1 - (embedding <=> $1::vector) as similarity
            FROM crawled_pages
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT $2
        """, query_embedding, match_count)
    
    async def search_documents_keyword(self, query: str,
                                     match_count: int = 10) -> List[Dict[str, Any]]:
        """Keyword search in crawled_pages"""
        return await self.client.execute_query("""
            SELECT id, url, content
            FROM crawled_pages
            WHERE content ILIKE $1
            ORDER BY created_at DESC
            LIMIT $2
        """, f'%{query}%', match_count)

    async def get_all_crawled_urls(self) -> List[Dict[str, Any]]:
        """Get all crawled URLs"""
        return await self.client.execute_query("""
            SELECT url, created_at
            FROM crawled_pages
            ORDER BY created_at DESC
        """)
    
    async def url_exists(self, url: str) -> bool:
        """Check if URL already exists in crawled_pages"""
        result = await self.client.fetch_val(
            "SELECT EXISTS(SELECT 1 FROM crawled_pages WHERE url = $1)",
            url
        )
        return result

    async def get_all_crawled_urls(self) -> List[str]:
        """Get all unique URLs from crawled_pages"""
        result = await self.client.execute_query(
            "SELECT DISTINCT url FROM crawled_pages ORDER BY url"
        )
        return [row['url'] for row in result]
    
    # ============================================================================
    # CODE EXAMPLES OPERATIONS
    # ============================================================================
    

    

    

    

