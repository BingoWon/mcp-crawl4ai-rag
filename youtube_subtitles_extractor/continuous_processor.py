#!/usr/bin/env python3
"""
YouTube字幕连续批量处理器

功能：
- 持续处理所有未处理的YouTube视频
- 每批处理20个视频
- 实时统计和进度汇报
- 自动停止当没有更多视频需要处理时
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from youtube_processor import YouTubeProcessor
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ContinuousYouTubeProcessor:
    """连续YouTube处理器"""
    
    def __init__(self, batch_size: int = 20):
        self.batch_size = batch_size
        self.total_processed = 0
        self.total_chunks = 0
        self.total_failed = 0
        self.start_time = None
        
    async def run_continuous_processing(self):
        """运行连续处理"""
        logger.info("🚀 开始YouTube字幕连续批量处理...")
        logger.info(f"📊 批处理大小: {self.batch_size}")
        
        self.start_time = datetime.now()
        batch_number = 1
        
        while True:
            logger.info("=" * 80)
            logger.info(f"🔄 开始第 {batch_number} 批处理...")
            
            processor = YouTubeProcessor()
            
            try:
                await processor.initialize()
                
                # 处理一批视频
                result = await processor.process_batch(self.batch_size)
                
                # 更新统计
                self.total_processed += result["processed"]
                self.total_chunks += result["total_chunks"]
                self.total_failed += result["failed"]
                
                # 汇报批次结果
                logger.info(f"📊 第 {batch_number} 批完成:")
                logger.info(f"   本批处理: {result['processed']}/{result['total_videos']}")
                logger.info(f"   本批chunks: {result['total_chunks']}")
                logger.info(f"   本批成功率: {result['success_rate']:.1f}%")
                
                # 汇报累计统计
                elapsed_time = datetime.now() - self.start_time
                logger.info(f"📈 累计统计:")
                logger.info(f"   总处理视频: {self.total_processed}")
                logger.info(f"   总chunks: {self.total_chunks}")
                logger.info(f"   总失败: {self.total_failed}")
                logger.info(f"   运行时间: {elapsed_time}")
                
                # 检查是否还有更多视频需要处理
                if result["total_videos"] == 0:
                    logger.info("🎉 所有YouTube视频处理完成！")
                    break
                elif result["total_videos"] < self.batch_size:
                    logger.info(f"📊 最后一批，只有 {result['total_videos']} 个视频")
                
                batch_number += 1
                
            except Exception as e:
                logger.error(f"❌ 第 {batch_number} 批处理失败: {e}")
                self.total_failed += self.batch_size
                
            finally:
                await processor.cleanup()
        
        # 最终统计
        self._print_final_summary()
    
    def _print_final_summary(self):
        """打印最终统计摘要"""
        total_time = datetime.now() - self.start_time
        
        logger.info("=" * 80)
        logger.info("🎊 YouTube字幕批量处理最终统计")
        logger.info("=" * 80)
        
        logger.info(f"📊 处理结果:")
        logger.info(f"   成功处理视频: {self.total_processed}")
        logger.info(f"   失败视频: {self.total_failed}")
        logger.info(f"   总chunks生成: {self.total_chunks}")
        
        if self.total_processed > 0:
            logger.info(f"   平均每视频chunks: {self.total_chunks / self.total_processed:.1f}")
            success_rate = self.total_processed / (self.total_processed + self.total_failed) * 100
            logger.info(f"   总体成功率: {success_rate:.1f}%")
        
        logger.info(f"⏱️ 时间统计:")
        logger.info(f"   总运行时间: {total_time}")
        
        if self.total_processed > 0:
            avg_time_per_video = total_time.total_seconds() / self.total_processed
            logger.info(f"   平均每视频处理时间: {avg_time_per_video:.1f}秒")
        
        logger.info("🎉 批量处理任务完成！")


async def main():
    """主函数"""
    processor = ContinuousYouTubeProcessor(batch_size=20)
    await processor.run_continuous_processing()


if __name__ == "__main__":
    asyncio.run(main())
