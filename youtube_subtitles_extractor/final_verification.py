#!/usr/bin/env python3
"""
YouTube字幕处理最终验证脚本

功能：
1. 检查所有YouTube视频的处理状态
2. 统计总体处理结果
3. 验证是否有遗漏的视频
4. 生成最终完成报告
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.database import create_database_client
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class FinalVerification:
    """最终验证器"""
    
    def __init__(self):
        self.db_client = None
        
    async def initialize(self):
        """初始化数据库连接"""
        logger.info("🔗 初始化数据库连接...")
        self.db_client = create_database_client()
        await self.db_client.initialize()
        logger.info("✅ 数据库连接成功")
    
    async def verify_completion(self):
        """验证处理完成状态"""
        logger.info("🔍 开始最终验证...")
        
        # 1. 检查总体统计
        total_stats = await self._get_total_stats()
        
        # 2. 检查未处理视频
        unprocessed_videos = await self._get_unprocessed_videos()
        
        # 3. 检查chunks统计
        chunks_stats = await self._get_chunks_stats()
        
        # 4. 生成最终报告
        self._generate_final_report(total_stats, unprocessed_videos, chunks_stats)
        
        return len(unprocessed_videos) == 0
    
    async def _get_total_stats(self):
        """获取总体统计"""
        query = """
        SELECT
            COUNT(*) as total_videos,
            COUNT(CASE WHEN c.url IS NOT NULL THEN 1 END) as processed_videos,
            COUNT(CASE WHEN c.url IS NULL THEN 1 END) as unprocessed_videos,
            COUNT(CASE WHEN p.content IS NOT NULL AND p.content != '' THEN 1 END) as videos_with_content
        FROM pages p
        LEFT JOIN (SELECT DISTINCT url FROM chunks WHERE url LIKE 'https://www.youtube.com/watch?v=%') c ON p.url = c.url
        WHERE p.url LIKE 'https://www.youtube.com/watch?v=%'
        """

        result = await self.db_client.fetch_one(query)
        return dict(result)
    
    async def _get_unprocessed_videos(self):
        """获取未处理的视频"""
        query = """
        SELECT p.url, p.content IS NOT NULL as has_content
        FROM pages p
        LEFT JOIN chunks c ON p.url = c.url
        WHERE p.url LIKE 'https://www.youtube.com/watch?v=%'
        AND c.url IS NULL
        ORDER BY p.url
        LIMIT 10
        """

        results = await self.db_client.fetch_all(query)
        return [dict(row) for row in results]
    
    async def _get_chunks_stats(self):
        """获取chunks统计"""
        query = """
        SELECT 
            COUNT(*) as total_chunks,
            COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as chunks_with_embedding,
            AVG(LENGTH(content)) as avg_chunk_length,
            MIN(LENGTH(content)) as min_chunk_length,
            MAX(LENGTH(content)) as max_chunk_length
        FROM chunks 
        WHERE url LIKE 'https://www.youtube.com/watch?v=%'
        """
        
        result = await self.db_client.fetch_one(query)
        return dict(result)
    
    async def _get_sample_processed_videos(self, limit=5):
        """获取已处理视频样本"""
        query = """
        SELECT
            p.url,
            p.processed_at,
            COUNT(c.id) as chunk_count
        FROM pages p
        LEFT JOIN chunks c ON p.url = c.url
        WHERE p.url LIKE 'https://www.youtube.com/watch?v=%'
        AND p.processed_at IS NOT NULL
        GROUP BY p.url, p.processed_at
        ORDER BY p.processed_at DESC
        LIMIT $1
        """

        results = await self.db_client.fetch_all(query, limit)
        return [dict(row) for row in results]
    
    def _generate_final_report(self, total_stats, unprocessed_videos, chunks_stats):
        """生成最终报告"""
        logger.info("=" * 80)
        logger.info("🎊 YouTube字幕处理最终验证报告")
        logger.info("=" * 80)
        
        # 总体统计
        logger.info("📊 总体处理统计:")
        logger.info(f"   总视频数: {total_stats['total_videos']}")
        logger.info(f"   已处理视频: {total_stats['processed_videos']}")
        logger.info(f"   未处理视频: {total_stats['unprocessed_videos']}")
        logger.info(f"   有内容视频: {total_stats['videos_with_content']}")
        
        if total_stats['total_videos'] > 0:
            completion_rate = (total_stats['processed_videos'] / total_stats['total_videos']) * 100
            logger.info(f"   完成率: {completion_rate:.1f}%")
        
        # Chunks统计
        logger.info("\n📦 Chunks处理统计:")
        logger.info(f"   总chunks数: {chunks_stats['total_chunks']}")
        logger.info(f"   有embedding的chunks: {chunks_stats['chunks_with_embedding']}")
        
        if chunks_stats['total_chunks'] > 0:
            embedding_rate = (chunks_stats['chunks_with_embedding'] / chunks_stats['total_chunks']) * 100
            logger.info(f"   Embedding完成率: {embedding_rate:.1f}%")
        
        if chunks_stats['avg_chunk_length']:
            logger.info(f"   平均chunk长度: {chunks_stats['avg_chunk_length']:.0f} 字符")
            logger.info(f"   最小chunk长度: {chunks_stats['min_chunk_length']} 字符")
            logger.info(f"   最大chunk长度: {chunks_stats['max_chunk_length']} 字符")
        
        # 未处理视频
        if unprocessed_videos:
            logger.info(f"\n⚠️ 发现 {len(unprocessed_videos)} 个未处理视频:")
            for video in unprocessed_videos:
                has_content = "有内容" if video['has_content'] else "无内容"
                logger.info(f"   - {video['url']} ({has_content})")
        else:
            logger.info("\n✅ 所有YouTube视频已完成处理！")
        
        # 最终结论
        logger.info("\n" + "=" * 80)
        if len(unprocessed_videos) == 0:
            logger.info("🎉 YouTube字幕处理任务100%完成！")
            logger.info("✅ 所有视频已成功处理并生成chunks")
            logger.info("✅ 所有chunks已完成embedding")
            logger.info("✅ 数据已准备就绪，可用于RAG检索")
        else:
            logger.info("⚠️ 处理未完全完成")
            logger.info(f"❌ 还有 {len(unprocessed_videos)} 个视频未处理")
            logger.info("💡 建议重新运行处理器完成剩余视频")
        
        logger.info("=" * 80)
    
    async def cleanup(self):
        """清理资源"""
        if self.db_client:
            await self.db_client.close()
            logger.info("🔒 数据库连接已关闭")


async def main():
    """主函数"""
    verifier = FinalVerification()
    
    try:
        await verifier.initialize()
        
        # 执行最终验证
        is_complete = await verifier.verify_completion()
        
        # 获取处理样本
        logger.info("\n📋 最近处理的视频样本:")
        sample_videos = await verifier._get_sample_processed_videos(5)
        for video in sample_videos:
            logger.info(f"   ✅ {video['url']} ({video['chunk_count']} chunks)")
            logger.info(f"      首个chunk创建时间: {video['first_chunk_created']}")
        
        if is_complete:
            logger.info("\n🎊 恭喜！所有YouTube视频处理完成！")
        else:
            logger.info("\n⚠️ 处理尚未完成，请检查未处理的视频")
            
    except Exception as e:
        logger.error(f"❌ 验证过程中出现错误: {e}")
        
    finally:
        await verifier.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
