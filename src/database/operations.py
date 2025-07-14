"""
Database Operations
数据库操作

High-level database operations for crawled content and RAG functionality.
爬取内容和RAG功能的高级数据库操作。
"""

from typing import List, Dict, Any, Optional
from .client import PostgreSQLClient


class DatabaseOperations:
    """High-level database operations"""
    
    def __init__(self, client: PostgreSQLClient):
        self.client = client
    
    # ============================================================================
    # CRAWLED PAGES OPERATIONS
    # ============================================================================
    
    async def insert_chunks(self, data: List[Dict[str, Any]]) -> None:
        """Insert chunks data"""
        if not data:
            return

        await self.client.execute_many("""
            INSERT INTO chunks (url, content, embedding)
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
        """Keyword search in chunks"""
        return await self.client.execute_query("""
            SELECT id, url, content
            FROM chunks
            WHERE content ILIKE $1
            ORDER BY created_at DESC
            LIMIT $2
        """, f'%{query}%', match_count)

    async def get_all_chunk_urls(self) -> List[Dict[str, Any]]:
        """Get all chunk URLs"""
        return await self.client.execute_query("""
            SELECT url, created_at
            FROM chunks
            ORDER BY created_at DESC
        """)

    async def insert_url_if_not_exists(self, url: str) -> bool:
        """Insert URL with crawl_count=0 if not exists. Returns True if inserted."""
        result = await self.client.execute_command("""
            INSERT INTO pages (url, crawl_count, content)
            VALUES ($1, 0, '')
            ON CONFLICT (url) DO NOTHING
        """, url)
        return "INSERT 0 1" in result

    async def get_next_crawl_url(self) -> Optional[str]:
        """Get URL with minimum crawl_count for next crawl"""
        result = await self.client.fetch_one("""
            SELECT url FROM pages
            WHERE crawl_count = (SELECT MIN(crawl_count) FROM pages)
            ORDER BY created_at ASC
            LIMIT 1
        """)
        return result['url'] if result else None

    async def update_page_after_crawl(self, url: str, content: str) -> None:
        """Update page content and increment crawl_count"""
        await self.client.execute_command("""
            UPDATE pages
            SET content = $2,
                crawl_count = crawl_count + 1,
                updated_at = NOW()
            WHERE url = $1
        """, url, content)

    async def delete_chunks_by_url(self, url: str) -> None:
        """Delete all chunks for a specific URL"""
        await self.client.execute_command(
            "DELETE FROM chunks WHERE url = $1", url
        )
    
    # ============================================================================
    # CODE EXAMPLES OPERATIONS
    # ============================================================================
    

    

    

    

