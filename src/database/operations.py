"""
Database Operations - 业务逻辑层

集中所有数据库业务逻辑，提供高级操作接口。

职责：
- 爬虫调度逻辑 (优先级、原子操作)
- 处理器调度逻辑 (批量处理)
- 向量搜索业务逻辑
- 复杂查询和批处理策略

架构：
- 基于DatabaseClient的纯业务逻辑层
- 无重复代码，职责清晰
- 优雅现代精简
"""

from typing import List, Dict, Any, Tuple
from .client import DatabaseClient, create_database_client


class DatabaseOperations:
    """业务逻辑层 - 集中所有数据库业务操作"""

    def __init__(self, client: DatabaseClient = None):
        self.client = client or create_database_client()
    
    # ============================================================================
    # 爬虫业务逻辑
    # ============================================================================

    async def insert_url_if_not_exists(self, url: str) -> bool:
        """插入URL，如果不存在。返回是否实际插入。"""
        try:
            result = await self.client.execute_command(
                "INSERT INTO pages (url, content) VALUES ($1, '') ON CONFLICT (url) DO NOTHING",
                url
            )
            return "INSERT 0 1" in result
        except Exception:
            return False

    async def insert_urls_batch(self, urls: List[str]) -> int:
        """批量插入URL，返回实际插入的数量"""
        if not urls:
            return 0

        await self.client.execute_many("""
            INSERT INTO pages (url, content)
            VALUES ($1, '')
            ON CONFLICT (url) DO NOTHING
        """, [(url,) for url in urls])

        result = await self.client.fetch_one("""
            SELECT COUNT(*) as count FROM pages
            WHERE url = ANY($1) AND content = ''
        """, urls)

        return result['count'] if result else 0

    async def get_urls_batch(self, batch_size: int = 5) -> List[str]:
        """分布式安全URL获取 - 基于现有字段的优雅租约机制"""
        lock_id = 12345  # 爬虫专用锁ID

        async with self.client.pool.acquire() as conn:
            # 获取advisory lock确保分布式原子性
            await conn.execute("SELECT pg_advisory_lock($1)", lock_id)

            try:
                # 优雅租约：使用created_at作为优先级，最老的URL优先处理
                results = await conn.fetch("""
                    SELECT url FROM pages
                    WHERE content = ''
                    ORDER BY created_at ASC
                    LIMIT $1
                    FOR UPDATE SKIP LOCKED
                """, batch_size)

                return [row['url'] for row in results]

            finally:
                # 释放advisory lock
                await conn.execute("SELECT pg_advisory_unlock($1)", lock_id)

    async def update_pages_batch(self, url_content_pairs: List[Tuple[str, str]]) -> Tuple[int, int]:
        """批量更新页面内容 - 优雅现代精简"""
        if not url_content_pairs:
            return 0, 0

        # 分离有效内容和失败内容
        valid_content_pairs = [(url, content) for url, content in url_content_pairs if content.strip()]
        failed_urls = [url for url, content in url_content_pairs if not content.strip()]

        # 更新有效内容
        if valid_content_pairs:
            await self.client.execute_many("""
                UPDATE pages SET content = $2 WHERE url = $1
            """, valid_content_pairs)

        # 重置失败URL为空状态
        if failed_urls:
            await self.client.execute_many("""
                UPDATE pages SET content = '' WHERE url = $1
            """, [(url,) for url in failed_urls])

        return len(valid_content_pairs), len(failed_urls)

    async def delete_pages_batch(self, urls: List[str]) -> int:
        """批量删除无效页面及其chunks - 优雅现代精简"""
        if not urls:
            return 0

        # 级联删除：先删除chunks，再删除pages
        await self.client.execute_many("""
            DELETE FROM chunks WHERE url = $1
        """, [(url,) for url in urls])

        await self.client.execute_many("""
            DELETE FROM pages WHERE url = $1
        """, [(url,) for url in urls])

        return len(urls)

    # ============================================================================
    # 处理器业务逻辑
    # ============================================================================

    async def get_process_urls_batch(self, batch_size: int = 50) -> List[Tuple[str, str]]:
        """分布式安全获取未处理内容 - 基于现有字段的优雅设计"""
        lock_id = 54321  # 处理器专用锁ID

        async with self.client.pool.acquire() as conn:
            # 获取advisory lock确保分布式原子性
            await conn.execute("SELECT pg_advisory_lock($1)", lock_id)

            try:
                # 优雅设计：最新爬取的内容优先处理，确保新鲜度
                results = await conn.fetch("""
                    SELECT url, content FROM pages
                    WHERE processed_at IS NULL
                    AND content IS NOT NULL
                    AND content != ''
                    ORDER BY created_at DESC
                    LIMIT $1
                    FOR UPDATE SKIP LOCKED
                """, batch_size)

                return [(row['url'], row['content']) for row in results]

            finally:
                # 释放advisory lock
                await conn.execute("SELECT pg_advisory_unlock($1)", lock_id)

    async def mark_pages_processed(self, urls: List[str]) -> int:
        """标记页面为已处理 - embedding完成后调用"""
        if not urls:
            return 0

        await self.client.execute_many("""
            UPDATE pages SET processed_at = NOW() WHERE url = $1
        """, [(url,) for url in urls])

        return len(urls)
    
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

    # ============================================================================
    # 向量搜索业务逻辑
    # ============================================================================

    async def get_all_chunk_urls(self) -> List[Dict[str, Any]]:
        """获取所有chunk URLs"""
        return await self.client.fetch_all("""
            SELECT url
            FROM chunks
            ORDER BY url ASC
        """)

    async def delete_chunks_batch(self, urls: List[str]) -> None:
        """批量删除URL对应的chunks"""
        if not urls:
            return

        await self.client.execute_many("""
            DELETE FROM chunks WHERE url = $1
        """, [(url,) for url in urls])

    async def delete_chunks_by_url(self, url: str) -> None:
        """删除指定URL的所有chunks"""
        await self.client.execute_command(
            "DELETE FROM chunks WHERE url = $1", url
        )

