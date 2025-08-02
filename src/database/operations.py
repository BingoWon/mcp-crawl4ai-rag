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
                "INSERT INTO pages (url, crawl_count, content, last_crawled_at) VALUES ($1, 0, '', NULL) ON CONFLICT (url) DO NOTHING",
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
            INSERT INTO pages (url, crawl_count, content, last_crawled_at)
            VALUES ($1, 0, '', NULL)
            ON CONFLICT (url) DO NOTHING
        """, [(url,) for url in urls])

        result = await self.client.fetch_one("""
            SELECT COUNT(*) as count FROM pages
            WHERE url = ANY($1) AND crawl_count = 0 AND last_crawled_at IS NULL
        """, urls)

        return result['count'] if result else 0



    async def get_urls_batch(self, batch_size: int = 5) -> List[str]:
        """原子性获取批量待爬取URL - 分布式安全 + 强租约机制"""
        # 使用PostgreSQL advisory lock确保原子性
        lock_id = 12345  # 固定锁ID用于URL获取

        async with self.client.pool.acquire() as conn:
            # 获取advisory lock
            await conn.execute("SELECT pg_advisory_lock($1)", lock_id)

            try:
                # 在锁保护下获取URL并建立强租约（临时增加crawl_count）
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
                # 释放advisory lock
                await conn.execute("SELECT pg_advisory_unlock($1)", lock_id)

    async def update_pages_batch(self, url_content_pairs: List[Tuple[str, str]]) -> Tuple[int, int]:
        """批量选择性更新页面内容和爬取计数 - 全局最优解"""
        if not url_content_pairs:
            return 0, 0

        # 分离有效内容和空内容 - 优雅现代精简
        valid_content_pairs = [(url, content) for url, content in url_content_pairs if content.strip()]
        empty_content_urls = [url for url, content in url_content_pairs if not content.strip()]

        # 更新有效内容（不再增加crawl_count，租约已在get_pages_batch中建立）
        if valid_content_pairs:
            await self.client.execute_many("""
                UPDATE pages
                SET content = $2
                WHERE url = $1
            """, valid_content_pairs)

        # 空内容不需要额外更新（租约已在get_pages_batch中建立）

        return len(valid_content_pairs), len(empty_content_urls)

    # ============================================================================
    # 处理器业务逻辑
    # ============================================================================

    async def get_process_urls_batch(self, batch_size: int = 5) -> List[Tuple[str, str]]:
        """原子性获取批量待处理URL - 分布式安全 + 强租约机制"""
        lock_id = 12346  # 不同于crawler的锁ID，避免冲突

        async with self.client.pool.acquire() as conn:
            # 获取advisory lock
            await conn.execute("SELECT pg_advisory_lock($1)", lock_id)

            try:
                # 在锁保护下批量获取URL和内容，同时建立租约
                results = await conn.fetch("""
                    UPDATE pages
                    SET process_count = process_count + 1,
                        last_processed_at = NOW()
                    WHERE url IN (
                        SELECT url FROM pages
                        WHERE content != '' AND content IS NOT NULL
                        ORDER BY last_processed_at ASC NULLS FIRST
                        LIMIT $1
                        FOR UPDATE SKIP LOCKED
                    )
                    RETURNING url, content
                """, batch_size)

                return [(row['url'], row['content']) for row in results]

            finally:
                # 释放advisory lock
                await conn.execute("SELECT pg_advisory_unlock($1)", lock_id)
    
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
            SELECT url, created_at
            FROM chunks
            ORDER BY created_at DESC
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

