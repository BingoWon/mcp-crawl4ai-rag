"""
Database Operations - High-level Database Interface
数据库操作 - 高级数据库接口

High-level database operations for the Apple RAG system with optimized
batch processing and intelligent scheduling.

Features:
- Intelligent crawling scheduling (prioritize least crawled pages)
- Efficient processing scheduling (prioritize recently crawled pages)
- Atomic batch operations with PostgreSQL locks
- Optimized database interactions
"""

from typing import List, Dict, Any, Tuple
from .client import DatabaseClient, create_database_client


class DatabaseOperations:
    """
    High-level database operations

    Provides high-level database operations for the Apple RAG system.
    """

    def __init__(self, client: DatabaseClient = None):
        self.client = client or create_database_client()
    
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
        """Vector similarity search in chunks using halfvec"""
        vector_str = str(query_embedding)
        return await self.client.execute_query("""
            SELECT id, url, content,
                   1 - (embedding <=> $1::halfvec) as similarity
            FROM chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> $1::halfvec
            LIMIT $2
        """, vector_str, match_count)
    
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
        """Insert URL with crawl_count=0 and last_crawled_at=NULL if not exists. Returns True if inserted."""
        return await self.client.insert_page(url)

    async def insert_urls_batch(self, urls: List[str]) -> int:
        """批量插入URL，返回实际插入的数量 - 全局最优解"""
        if not urls:
            return 0

        # 批量插入，使用ON CONFLICT避免重复
        await self.client.execute_many("""
            INSERT INTO pages (url, crawl_count, content, last_crawled_at)
            VALUES ($1, 0, '', NULL)
            ON CONFLICT (url) DO NOTHING
        """, [(url,) for url in urls])

        # 查询实际插入的数量
        result = await self.client.fetch_one("""
            SELECT COUNT(*) as count FROM pages
            WHERE url = ANY($1) AND crawl_count = 0 AND last_crawled_at IS NULL
        """, urls)

        return result['count'] if result else 0

    async def get_pages_batch(self, batch_size: int = 5) -> List[str]:
        """Get batch of URLs for crawling using unified interface with atomic operations"""
        return await self.client.get_pages_batch(batch_size)

    async def get_process_urls_batch(self, batch_size: int = 5) -> List[Tuple[str, str]]:
        """Get batch of URLs and content for processing using unified interface"""
        return await self.client.get_process_urls_batch(batch_size)

    async def delete_chunks_batch(self, urls: List[str]) -> None:
        """批量删除URL对应的chunks - 全局最优解"""
        if not urls:
            return

        await self.client.execute_many("""
            DELETE FROM chunks WHERE url = $1
        """, [(url,) for url in urls])

    async def update_pages_batch(self, url_content_pairs: List[Tuple[str, str]]) -> Tuple[int, int]:
        """Update pages content in batch using unified interface"""
        if not url_content_pairs:
            return 0, 0

        # Separate valid content and empty content
        valid_content_pairs = [(url, content) for url, content in url_content_pairs if content.strip()]
        empty_content_urls = [url for url, content in url_content_pairs if not content.strip()]

        # Update valid content using unified interface
        if valid_content_pairs:
            await self.client.update_pages_batch(valid_content_pairs)

        return len(valid_content_pairs), len(empty_content_urls)

    async def delete_chunks_by_url(self, url: str) -> None:
        """Delete all chunks for a specific URL"""
        await self.client.execute_command(
            "DELETE FROM chunks WHERE url = $1", url
        )

