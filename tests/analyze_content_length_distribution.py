#!/usr/bin/env python3
"""
Content Length Distribution Analyzer
分析chunks表中content字段长度分布的可视化工具

功能：
- 查询数据库chunks表
- 分析content字段长度分布
- 生成直方图和统计图表
- 保存分析结果
"""

import asyncio
import sys
import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
load_dotenv(project_root / ".env")

from src.database import create_database_client
from src.utils.logger import setup_logger

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

logger = setup_logger(__name__)


class ContentLengthAnalyzer:
    """Content长度分布分析器"""
    
    def __init__(self):
        self.db_client = None
        self.content_lengths = []
        self.stats = {}
        
    async def initialize(self):
        """初始化数据库连接"""
        logger.info("🔗 初始化数据库连接...")
        self.db_client = create_database_client()
        await self.db_client.initialize()
        logger.info("✅ 数据库连接成功")
        
    async def fetch_content_lengths(self):
        """获取所有chunks的content长度"""
        logger.info("📊 查询chunks表content长度...")
        
        # 查询所有chunks的content长度
        query = """
        SELECT 
            LENGTH(content) as content_length,
            url,
            SUBSTRING(content, 1, 100) as content_preview
        FROM chunks 
        WHERE content IS NOT NULL AND content != ''
        ORDER BY LENGTH(content) DESC
        """
        
        results = await self.db_client.fetch_all(query)
        logger.info(f"📈 获取到 {len(results)} 条记录")
        
        # 提取长度数据
        self.content_lengths = [row['content_length'] for row in results]
        
        # 保存详细数据用于分析
        self.detailed_data = results
        
        return results
        
    def calculate_statistics(self):
        """计算统计信息"""
        if not self.content_lengths:
            logger.warning("⚠️ 没有数据可供分析")
            return
            
        lengths = np.array(self.content_lengths)
        
        self.stats = {
            'total_count': len(lengths),
            'min_length': int(np.min(lengths)),
            'max_length': int(np.max(lengths)),
            'mean_length': float(np.mean(lengths)),
            'median_length': float(np.median(lengths)),
            'std_length': float(np.std(lengths)),
            'q25': float(np.percentile(lengths, 25)),
            'q75': float(np.percentile(lengths, 75)),
            'q90': float(np.percentile(lengths, 90)),
            'q95': float(np.percentile(lengths, 95)),
            'q99': float(np.percentile(lengths, 99))
        }
        
        logger.info("📊 统计信息计算完成")
        
    def create_visualizations(self):
        """创建可视化图表"""
        if not self.content_lengths:
            logger.warning("⚠️ 没有数据可供可视化")
            return
            
        # 创建图表目录
        output_dir = Path(__file__).parent / "content_analysis_output"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. 基础直方图
        self._create_histogram(output_dir, timestamp)
        
        # 2. 箱线图
        self._create_boxplot(output_dir, timestamp)
        
        # 3. 累积分布图
        self._create_cumulative_distribution(output_dir, timestamp)
        
        # 4. 分段统计图
        self._create_length_segments_chart(output_dir, timestamp)
        
        logger.info(f"📈 图表已保存到: {output_dir}")
        
    def _create_histogram(self, output_dir, timestamp):
        """创建直方图"""
        plt.figure(figsize=(12, 8))
        
        # 使用合适的bins数量
        bins = min(50, len(set(self.content_lengths)))
        
        plt.hist(self.content_lengths, bins=bins, alpha=0.7, color='skyblue', edgecolor='black')
        plt.title(f'Content Length Distribution\n总记录数: {self.stats["total_count"]}', fontsize=16)
        plt.xlabel('Content Length (characters)', fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # 添加统计信息
        stats_text = f"""统计信息:
平均值: {self.stats['mean_length']:.0f}
中位数: {self.stats['median_length']:.0f}
标准差: {self.stats['std_length']:.0f}
最小值: {self.stats['min_length']}
最大值: {self.stats['max_length']}"""
        
        plt.text(0.7, 0.7, stats_text, transform=plt.gca().transAxes, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8),
                fontsize=10, verticalalignment='top')
        
        plt.tight_layout()
        plt.savefig(output_dir / f"content_length_histogram_{timestamp}.png", dpi=300, bbox_inches='tight')
        plt.close()
        
    def _create_boxplot(self, output_dir, timestamp):
        """创建箱线图"""
        plt.figure(figsize=(10, 6))
        
        box_plot = plt.boxplot(self.content_lengths, vert=True, patch_artist=True)
        box_plot['boxes'][0].set_facecolor('lightblue')
        
        plt.title('Content Length Box Plot', fontsize=16)
        plt.ylabel('Content Length (characters)', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # 添加四分位数标注
        quartiles_text = f"""四分位数:
Q1 (25%): {self.stats['q25']:.0f}
Q2 (50%): {self.stats['median_length']:.0f}
Q3 (75%): {self.stats['q75']:.0f}
Q90: {self.stats['q90']:.0f}
Q95: {self.stats['q95']:.0f}
Q99: {self.stats['q99']:.0f}"""
        
        plt.text(1.1, 0.5, quartiles_text, transform=plt.gca().transAxes,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8),
                fontsize=10, verticalalignment='center')
        
        plt.tight_layout()
        plt.savefig(output_dir / f"content_length_boxplot_{timestamp}.png", dpi=300, bbox_inches='tight')
        plt.close()
        
    def _create_cumulative_distribution(self, output_dir, timestamp):
        """创建累积分布图"""
        plt.figure(figsize=(12, 8))
        
        sorted_lengths = np.sort(self.content_lengths)
        cumulative_prob = np.arange(1, len(sorted_lengths) + 1) / len(sorted_lengths)
        
        plt.plot(sorted_lengths, cumulative_prob, linewidth=2, color='darkblue')
        plt.title('Cumulative Distribution of Content Lengths', fontsize=16)
        plt.xlabel('Content Length (characters)', fontsize=12)
        plt.ylabel('Cumulative Probability', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # 添加关键百分位数线
        percentiles = [25, 50, 75, 90, 95, 99]
        colors = ['red', 'orange', 'green', 'purple', 'brown', 'pink']
        
        for p, color in zip(percentiles, colors):
            value = np.percentile(self.content_lengths, p)
            plt.axvline(x=value, color=color, linestyle='--', alpha=0.7, 
                       label=f'P{p}: {value:.0f}')
        
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / f"content_length_cumulative_{timestamp}.png", dpi=300, bbox_inches='tight')
        plt.close()
        
    def _create_length_segments_chart(self, output_dir, timestamp):
        """创建长度分段统计图"""
        plt.figure(figsize=(12, 8))
        
        # 定义长度区间
        segments = [
            (0, 500, "Very Short (0-500)"),
            (501, 1000, "Short (501-1000)"),
            (1001, 2000, "Medium (1001-2000)"),
            (2001, 3000, "Long (2001-3000)"),
            (3001, 4000, "Long+ (3001-4000)"),
            (4001, 5000, "Very Long (4001-5000)"),
            (5001, 10000, "Very Long+ (5001-10000)"),
            (10001, float('inf'), "Extremely Long (10000+)")
        ]
        
        segment_counts = []
        segment_labels = []
        
        for min_len, max_len, label in segments:
            if max_len == float('inf'):
                count = sum(1 for length in self.content_lengths if length >= min_len)
            else:
                count = sum(1 for length in self.content_lengths 
                           if min_len <= length <= max_len)
            segment_counts.append(count)
            segment_labels.append(f"{label}\n({count} chunks)")
        
        # 创建饼图
        plt.subplot(1, 2, 1)
        colors = plt.cm.Set3(np.linspace(0, 1, len(segment_counts)))
        plt.pie(segment_counts, labels=segment_labels, autopct='%1.1f%%', 
                colors=colors, startangle=90)
        plt.title('Content Length Distribution by Segments', fontsize=14)
        
        # 创建柱状图
        plt.subplot(1, 2, 2)
        bars = plt.bar(range(len(segment_counts)), segment_counts, color=colors)
        plt.title('Content Length Segments Count', fontsize=14)
        plt.xlabel('Length Segments', fontsize=12)
        plt.ylabel('Count', fontsize=12)
        plt.xticks(range(len(segment_labels)), 
                  [label.split('\n')[0] for label in segment_labels], 
                  rotation=45, ha='right')
        
        # 添加数值标签
        for bar, count in zip(bars, segment_counts):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(segment_counts)*0.01,
                    str(count), ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(output_dir / f"content_length_segments_{timestamp}.png", dpi=300, bbox_inches='tight')
        plt.close()
        
    def save_analysis_report(self):
        """保存分析报告"""
        output_dir = Path(__file__).parent / "content_analysis_output"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_dir / f"content_analysis_report_{timestamp}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("Content Length Distribution Analysis Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("基础统计信息:\n")
            f.write("-" * 20 + "\n")
            for key, value in self.stats.items():
                if isinstance(value, float):
                    f.write(f"{key}: {value:.2f}\n")
                else:
                    f.write(f"{key}: {value}\n")

            f.write("\n百分位数解释:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Q25 ({self.stats['q25']:.0f}): 25%的chunks长度 ≤ {self.stats['q25']:.0f}字符\n")
            f.write(f"Q75 ({self.stats['q75']:.0f}): 75%的chunks长度 ≤ {self.stats['q75']:.0f}字符\n")
            f.write(f"Q90 ({self.stats['q90']:.0f}): 90%的chunks长度 ≤ {self.stats['q90']:.0f}字符\n")
            f.write(f"Q95 ({self.stats['q95']:.0f}): 95%的chunks长度 ≤ {self.stats['q95']:.0f}字符\n")
            f.write(f"Q99 ({self.stats['q99']:.0f}): 99%的chunks长度 ≤ {self.stats['q99']:.0f}字符\n")
            f.write("说明: Q25-Q75区间包含50%的数据，是核心分布区\n")
            
            f.write("\n长度分段统计:\n")
            f.write("-" * 20 + "\n")
            segments = [
                (0, 500, "Very Short"),
                (501, 1000, "Short"),
                (1001, 2000, "Medium"),
                (2001, 3000, "Long"),
                (3001, 4000, "Long+"),
                (4001, 5000, "Very Long"),
                (5001, 10000, "Very Long+"),
                (10001, float('inf'), "Extremely Long")
            ]
            
            total_chunks = len(self.content_lengths)
            for min_len, max_len, label in segments:
                if max_len == float('inf'):
                    count = sum(1 for length in self.content_lengths if length >= min_len)
                    percentage = (count / total_chunks) * 100
                    f.write(f"{label} ({min_len}+): {count} chunks ({percentage:.2f}%)\n")
                else:
                    count = sum(1 for length in self.content_lengths
                               if min_len <= length <= max_len)
                    percentage = (count / total_chunks) * 100
                    f.write(f"{label} ({min_len}-{max_len}): {count} chunks ({percentage:.2f}%)\n")
            
            # 添加最长和最短的几个示例
            f.write("\n最长内容示例 (前5个):\n")
            f.write("-" * 30 + "\n")
            sorted_data = sorted(self.detailed_data, key=lambda x: x['content_length'], reverse=True)
            for i, item in enumerate(sorted_data[:5]):
                f.write(f"{i+1}. 长度: {item['content_length']}, URL: {item['url']}\n")
                f.write(f"   预览: {item['content_preview']}...\n\n")
            
            f.write("\n最短内容示例 (前5个):\n")
            f.write("-" * 30 + "\n")
            for i, item in enumerate(sorted_data[-5:]):
                f.write(f"{i+1}. 长度: {item['content_length']}, URL: {item['url']}\n")
                f.write(f"   预览: {item['content_preview']}...\n\n")
        
        logger.info(f"📄 分析报告已保存: {report_file}")
        
    async def run_analysis(self):
        """运行完整分析流程"""
        try:
            await self.initialize()
            await self.fetch_content_lengths()
            self.calculate_statistics()
            self.create_visualizations()
            self.save_analysis_report()
            
            logger.info("✅ Content长度分布分析完成")
            
        except Exception as e:
            logger.error(f"❌ 分析过程中出现错误: {e}")
            raise
        finally:
            if self.db_client:
                await self.db_client.close()


async def main():
    """主函数"""
    logger.info("🚀 开始Content长度分布分析...")
    
    analyzer = ContentLengthAnalyzer()
    await analyzer.run_analysis()
    
    logger.info("🎉 分析完成！")


if __name__ == "__main__":
    asyncio.run(main())
