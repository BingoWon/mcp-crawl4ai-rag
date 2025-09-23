#!/usr/bin/env python3
"""
YouTube字幕处理器 - 完整流程实现

功能：
1. 从pages表读取YouTube字幕数据
2. 进行chunking分块处理
3. 批量embedding处理
4. 存储到chunks表
5. 更新pages表processed_at状态

处理单位：一个视频的所有chunks一起处理
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple


# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.database import create_database_client

from src.embedding import get_embedder
from src.embedding.providers import SiliconFlowProvider
from src.utils.logger import setup_logger
from youtube_chunker import YouTubeChunker

logger = setup_logger(__name__)


class YouTubeProcessor:
    """YouTube字幕完整处理器"""
    
    def __init__(self):
        self.db_client = None
        self.chunker = YouTubeChunker()
        
    async def initialize(self):
        """初始化数据库连接"""
        logger.info("🔗 初始化YouTube处理器...")
        self.db_client = create_database_client()
        await self.db_client.initialize()
        logger.info("✅ 数据库连接成功")
    
    async def get_unprocessed_youtube_videos(self, limit: int = 10) -> List[Tuple[str, Dict]]:
        """
        获取未处理的YouTube视频数据
        
        Args:
            limit: 获取数量限制
            
        Returns:
            List of (url, video_data) tuples
        """
        logger.info(f"📊 获取未处理的YouTube视频数据，限制: {limit}")
        
        query = """
            SELECT p.url, p.content
            FROM pages p
            LEFT JOIN chunks c ON p.url = c.url
            WHERE p.url LIKE 'https://www.youtube.com/watch?v=%'
            AND p.content IS NOT NULL
            AND p.content != ''
            AND c.url IS NULL
            ORDER BY p.created_at ASC
            LIMIT $1
        """
        
        records = await self.db_client.fetch_all(query, limit)
        
        results = []
        for record in records:
            try:
                video_data = json.loads(record['content'])
                results.append((record['url'], video_data))
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON解析失败 {record['url']}: {e}")
                continue
        
        logger.info(f"✅ 获取到 {len(results)} 个有效YouTube视频")
        return results

    async def _batch_embedding(self, chunks: List[Dict[str, str]]) -> List[List[float]]:
        """
        批量embedding处理 - 对 title + "\n\n" + content 做embedding

        Args:
            chunks: chunk字典列表，格式：[{"title": "标题", "content": "内容"}, ...]

        Returns:
            embedding列表，失败的为None
        """
        embedder = get_embedder()

        # 项目要求：永远不允许使用本地模型，只使用API
        if not isinstance(embedder, SiliconFlowProvider):
            raise RuntimeError("Only SiliconFlow API embedding is allowed, local models are prohibited")

        try:
            # 构建embedding文本：title + "\n\n" + content
            embedding_texts = []
            for chunk in chunks:
                embedding_text = f"{chunk['title']}\n\n{chunk['content']}"
                embedding_texts.append(embedding_text)

            logger.info(f"📝 构建embedding文本: {len(embedding_texts)} 个")

            # 使用批量API调用 - 单次API请求处理所有文本
            batch_embeddings = await embedder.encode_batch_concurrent(embedding_texts)
            logger.info(f"✅ 批量embedding完成: {len(batch_embeddings)} 个")
            return batch_embeddings
        except Exception as e:
            logger.error(f"❌ 批量embedding失败: {e}")
            # 返回None列表，让上层处理失败情况
            return [None] * len(chunks)

    async def process_single_video(self, url: str, video_data: Dict) -> Dict[str, Any]:
        """
        处理单个视频的完整流程
        
        Args:
            url: YouTube URL
            video_data: 视频数据 {"context": "标题", "content": "字幕"}
            
        Returns:
            处理结果统计
        """
        logger.info(f"🎬 开始处理视频: {video_data['context']}")
        
        try:
            # 1. Chunking分块
            chunks = self.chunker.chunk_youtube_subtitle(video_data)
            if not chunks:
                logger.warning(f"⚠️ 视频无有效chunks: {url}")
                return {"success": False, "error": "No valid chunks"}
            
            # 2. 转换为JSON字符串
            json_chunks = self.chunker.chunk_to_json_strings(chunks)
            logger.info(f"📦 生成 {len(json_chunks)} 个chunks")

            # 3. 批量embedding处理 - 对 title + "\n\n" + content 做embedding
            logger.info("🧠 开始embedding处理...")
            embeddings = await self._batch_embedding(chunks)
            
            # 过滤成功的embeddings
            valid_data = []
            for i, (json_chunk, embedding) in enumerate(zip(json_chunks, embeddings)):
                if embedding is not None:
                    valid_data.append({
                        "url": url,
                        "content": json_chunk,
                        "embedding": str(embedding)
                    })
                else:
                    logger.warning(f"⚠️ 跳过失败的chunk {i+1}")
            
            if not valid_data:
                logger.error(f"❌ 所有chunks embedding失败: {url}")
                return {"success": False, "error": "All embeddings failed"}
            
            # 4. 批量存储到chunks表
            logger.info(f"💾 存储 {len(valid_data)} 个chunks到数据库...")
            await self._store_chunks_batch(url, valid_data)

            logger.info(f"✅ 视频处理完成: {len(valid_data)} chunks")
            
            return {
                "success": True,
                "total_chunks": len(json_chunks),
                "valid_chunks": len(valid_data),
                "failed_chunks": len(json_chunks) - len(valid_data)
            }
            
        except Exception as e:
            logger.error(f"❌ 视频处理失败 {url}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _store_chunks_batch(self, url: str, chunk_data: List[Dict[str, Any]]):
        """
        批量存储chunks到数据库
        
        Args:
            url: YouTube URL
            chunk_data: chunk数据列表
        """
        # 先删除该URL的现有chunks（如果有）
        delete_query = "DELETE FROM chunks WHERE url = $1"
        await self.db_client.execute_command(delete_query, url)

        # 批量插入新chunks
        insert_query = """
            INSERT INTO chunks (url, content, embedding)
            VALUES ($1, $2, $3)
        """

        insert_data = [
            (item["url"], item["content"], item["embedding"])
            for item in chunk_data
        ]

        await self.db_client.execute_many(insert_query, insert_data)
        logger.info(f"💾 成功存储 {len(insert_data)} 个chunks")
    

    
    async def process_batch(self, batch_size: int = 5) -> Dict[str, Any]:
        """
        批量处理YouTube视频
        
        Args:
            batch_size: 批处理大小
            
        Returns:
            处理结果统计
        """
        logger.info(f"🚀 开始批量处理YouTube视频，批大小: {batch_size}")
        
        # 获取未处理的视频
        videos = await self.get_unprocessed_youtube_videos(batch_size)
        
        if not videos:
            logger.info("ℹ️ 没有未处理的YouTube视频")
            return {"total_videos": 0, "processed": 0, "failed": 0}
        
        # 处理统计
        total_videos = len(videos)
        processed_count = 0
        failed_count = 0
        total_chunks = 0
        
        logger.info(f"📊 开始处理 {total_videos} 个视频")
        
        for i, (url, video_data) in enumerate(videos, 1):
            logger.info(f"📹 处理进度: {i}/{total_videos}")
            
            result = await self.process_single_video(url, video_data)
            
            if result["success"]:
                processed_count += 1
                total_chunks += result["valid_chunks"]
                logger.info(f"✅ 视频 {i} 处理成功: {result['valid_chunks']} chunks")
            else:
                failed_count += 1
                logger.error(f"❌ 视频 {i} 处理失败: {result.get('error', 'Unknown error')}")
        
        # 最终统计
        stats = {
            "total_videos": total_videos,
            "processed": processed_count,
            "failed": failed_count,
            "total_chunks": total_chunks,
            "success_rate": processed_count / total_videos * 100 if total_videos > 0 else 0
        }
        
        logger.info("=" * 60)
        logger.info("📊 批量处理完成统计:")
        logger.info(f"   总视频数: {stats['total_videos']}")
        logger.info(f"   成功处理: {stats['processed']}")
        logger.info(f"   处理失败: {stats['failed']}")
        logger.info(f"   总chunks: {stats['total_chunks']}")
        logger.info(f"   成功率: {stats['success_rate']:.1f}%")
        
        return stats
    
    async def cleanup(self):
        """清理资源"""
        if self.db_client:
            await self.db_client.close()
            logger.info("🔒 数据库连接已关闭")


async def main():
    """主函数"""
    processor = YouTubeProcessor()
    
    try:
        await processor.initialize()
        
        # 处理1个视频作为测试
        result = await processor.process_batch(batch_size=1)
        
        if result["processed"] > 0:
            logger.info("🎉 YouTube字幕处理完成！")
        else:
            logger.warning("⚠️ 没有成功处理任何视频")
            
    except Exception as e:
        logger.error(f"❌ 处理过程中出现错误: {e}")
        
    finally:
        await processor.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
