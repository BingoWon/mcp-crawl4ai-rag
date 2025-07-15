"""
Database Operations
数据库操作

High-level database operations for crawled content and RAG functionality.
爬取内容和RAG功能的高级数据库操作。

=== 智能爬取优化设计 ===

本模块实现了基于内容状态的智能爬取优化策略：

**核心优化：get_next_crawl_url() 方法**
- 同时返回 URL 和 content，避免重复数据库查询
- 返回格式：Optional[tuple[str, str]] = (url, content)
- 单次查询获取爬取决策所需的全部信息

**设计原理：**
1. 传统方式：先查询 URL，再查询 content（2次数据库访问）
2. 优化方式：一次查询同时获取 URL 和 content（1次数据库访问）
3. 性能提升：减少50%的数据库查询，降低延迟

**逻辑关系：**
- crawl_count = 0：新URL，content 必为空，无需链接发现
- crawl_count > 0 且最小：已爬取过，通常有 content，需要链接发现
- 通过 content 状态判断是否执行链接发现，避免无效操作

**实际效果：**
- 减少数据库负载
- 提高爬取效率
- 避免在空内容页面上执行无意义的链接提取
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

    async def get_next_crawl_url(self) -> Optional[tuple[str, str]]:
        """Get URL and content with minimum crawl_count for next crawl"""
        result = await self.client.fetch_one("""
            SELECT url, content FROM pages
            WHERE crawl_count = (SELECT MIN(crawl_count) FROM pages)
            ORDER BY created_at ASC
            LIMIT 1
        """)
        return (result['url'], result['content']) if result else None

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
    

    

    

    

