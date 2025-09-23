#!/usr/bin/env python3
"""
YouTube字幕专用分块器 - 真正动态自适应策略

核心算法：
1. 动态计算目标chunk数量：target_chunk_count = 总长度 ÷ 2500
2. 每次分割前重新计算：dynamic_size = 剩余长度 ÷ 剩余chunks数
3. 在目标位置附近寻找最近的英文句号（.）作为分割点
4. JSON包装：{"title": "视频标题", "content": "chunk内容"}
5. 真正自适应：每个chunk大小根据剩余内容动态调整
"""

import json
from pathlib import Path
from typing import List, Dict, Any


class YouTubeChunker:
    """YouTube字幕专用分块器 - 智能分割控制"""

    # 核心配置常量
    TARGET_CHUNK_SIZE = 2500
    MAX_CHUNK_SIZE = 3000
    SEARCH_RANGE = 250

    def __init__(self):
        pass
    
    def chunk_youtube_subtitle(self, video_data: Dict[str, str]) -> List[Dict[str, str]]:
        """
        对YouTube字幕进行分块 - 真正动态自适应策略

        核心特性：
        - 每次分割前重新计算剩余长度和剩余chunks数
        - 动态调整chunk大小以实现均匀分布
        - 保持句号(.)分割点的语义完整性

        Args:
            video_data: {"context": "视频标题", "content": "完整字幕"}

        Returns:
            List of chunks: [{"title": "标题", "content": "分块内容"}, ...]
        """
        context = video_data["context"]
        content = video_data["content"]

        if not content.strip():
            return []

        # 智能分割控制：小于MAX_CHUNK_SIZE不需要分割
        total_length = len(content)
        if total_length <= self.MAX_CHUNK_SIZE:
            return [{
                "title": context,
                "content": content
            }]

        # 动态计算目标chunk数量 - 使用四舍五入确保合理分割
        # 例如：4900长度 ÷ 2500 = 1.96 → round(1.96) = 2个chunks
        # 避免整数除法向下取整导致的chunk过大问题
        target_chunk_count = max(1, round(total_length / self.TARGET_CHUNK_SIZE))



        chunks = []
        position = 0
        current_chunk_index = 0

        while position < len(content) and current_chunk_index < target_chunk_count:
            # 真正的动态自适应：每次重新计算剩余长度和chunk大小
            remaining_length = len(content) - position
            remaining_chunks = target_chunk_count - current_chunk_index
            dynamic_chunk_size = remaining_length // remaining_chunks

            # 计算这个chunk的结束位置
            chunk_end = self._find_chunk_end(content, position, dynamic_chunk_size, current_chunk_index, target_chunk_count)

            # 提取chunk内容
            chunk_content = content[position:chunk_end].strip()

            if chunk_content:  # 只有非空内容才添加
                chunk = {
                    "title": context,
                    "content": chunk_content
                }
                chunks.append(chunk)

            # 移动到下一个位置
            position = chunk_end
            current_chunk_index += 1

        return chunks
    
    def _find_chunk_end(self, content: str, start_pos: int, dynamic_chunk_size: int,
                        current_chunk_index: int, target_chunk_count: int) -> int:
        """
        找到chunk的结束位置 - 最后chunk特殊处理 + 最近句号策略

        Args:
            content: 完整内容
            start_pos: 开始位置
            dynamic_chunk_size: 动态自适应计算的chunk大小
            current_chunk_index: 当前chunk索引
            target_chunk_count: 目标chunk数量

        Returns:
            chunk结束位置
        """
        # 如果是最后一个chunk，直接返回内容结尾
        if current_chunk_index == target_chunk_count - 1:
            return len(content)

        # 如果剩余内容不足MAX_CHUNK_SIZE字符，直接返回结尾
        remaining_content_length = len(content) - start_pos
        if remaining_content_length <= self.MAX_CHUNK_SIZE:
            return len(content)

        target_pos = start_pos + dynamic_chunk_size

        # 智能搜索：在SEARCH_RANGE范围内寻找最佳句号分割点
        search_start = max(start_pos, target_pos - self.SEARCH_RANGE)
        search_end = min(len(content), target_pos + self.SEARCH_RANGE)

        best_pos = target_pos
        best_distance = float('inf')

        # 在搜索范围内寻找句号
        for i in range(search_start, search_end):
            if content[i] == '.':
                split_pos = i + 1  # 包含句号
                distance = abs(split_pos - target_pos)

                # 选择距离目标位置最近的句号
                if distance < best_distance:
                    best_distance = distance
                    best_pos = split_pos

        # 如果找到了句号分割点，使用它；否则使用目标位置
        if best_distance < float('inf'):
            return best_pos
        else:
            return min(target_pos, len(content))
    
    def chunk_to_json_strings(self, chunks: List[Dict[str, str]]) -> List[str]:
        """
        将chunks转换为JSON字符串列表（与现有chunks表格式一致）
        
        Args:
            chunks: chunk字典列表
            
        Returns:
            JSON字符串列表
        """
        json_strings = []
        for chunk in chunks:
            json_str = json.dumps(chunk, ensure_ascii=False, indent=2)
            json_strings.append(json_str)
        
        return json_strings
    
    def analyze_chunks(self, chunks: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        分析chunks的统计信息
        
        Args:
            chunks: chunk列表
            
        Returns:
            统计信息字典
        """
        if not chunks:
            return {"total_chunks": 0}
        
        lengths = [len(chunk["content"]) for chunk in chunks]
        
        stats = {
            "total_chunks": len(chunks),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "avg_length": sum(lengths) / len(lengths),
            "total_length": sum(lengths),
            "title": chunks[0]["title"]  # 所有chunks的title应该相同
        }
        
        return stats


def test_youtube_chunker():
    """测试YouTube分块器 - 扩大测试范围"""
    print("🧪 开始测试YouTube字幕分块器...")
    print("=" * 60)

    chunker = YouTubeChunker()

    # 扫描所有JSON文件进行测试
    subtitles_dir = Path("subtitles")
    all_files = list(subtitles_dir.glob("*.json"))

    # 选择不同长度的测试文件（最多测试15个）
    test_files = sorted(all_files)[:15]

    print(f"📁 找到 {len(all_files)} 个JSON文件，测试前 {len(test_files)} 个")
    print("=" * 60)

    # 全局统计数据
    all_chunks_data = []
    total_videos = 0
    total_chunks = 0

    for test_file in test_files:
        file_path = test_file  # test_files已经是Path对象

        if not file_path.exists():
            print(f"⚠️ 文件不存在: {test_file.name}")
            continue
        
        print(f"\n📁 测试文件: {test_file.name}")
        print("-" * 40)
        
        try:
            # 读取原始数据
            with open(file_path, 'r', encoding='utf-8') as f:
                video_data = json.load(f)
            
            original_length = len(video_data["content"])
            print(f"📊 原始长度: {original_length:,} 字符")
            print(f"📋 视频标题: {video_data['context']}")
            
            # 进行分块
            chunks = chunker.chunk_youtube_subtitle(video_data)
            
            # 分析结果
            stats = chunker.analyze_chunks(chunks)
            
            print(f"📈 分块结果:")
            print(f"   总块数: {stats['total_chunks']}")
            print(f"   最小长度: {stats['min_length']:,} 字符")
            print(f"   最大长度: {stats['max_length']:,} 字符")
            print(f"   平均长度: {stats['avg_length']:.0f} 字符")
            print(f"   总长度: {stats['total_length']:,} 字符")
            
            # 验证内容完整性
            total_chunked = sum(len(chunk["content"]) for chunk in chunks)
            loss_ratio = (original_length - total_chunked) / original_length * 100
            print(f"   内容损失: {loss_ratio:.2f}%")

            # 收集完整JSON chunk长度数据
            json_chunks = chunker.chunk_to_json_strings(chunks)
            json_lengths = [len(json_str) for json_str in json_chunks]
            all_chunks_data.extend(json_lengths)
            total_videos += 1
            total_chunks += len(chunks)

            # 显示完整JSON chunk长度分布
            print(f"   JSON长度分布: {min(json_lengths)}-{max(json_lengths)} 字符")

            # 显示详细分解（仅前3个视频）
            if total_videos <= 3:
                print(f"   详细分解:")
                for i, (chunk, json_str) in enumerate(zip(chunks[:2], json_chunks[:2])):
                    content_len = len(chunk["content"])
                    title_len = len(chunk["title"])
                    json_len = len(json_str)
                    overhead = json_len - content_len - title_len
                    print(f"     Chunk {i+1}: content={content_len}, title={title_len}, JSON总长={json_len}, 开销={overhead}")

            # 保存测试结果（只保存前3个文件的详细结果）
            if total_videos <= 3:
                output_file = Path(f"test_chunks_{test_file.name}")

                with open(output_file, 'w', encoding='utf-8') as f:
                    for i, json_chunk in enumerate(json_chunks):
                        f.write(f"=== Chunk {i+1} ===\n")
                        f.write(json_chunk)
                        f.write("\n\n")

                print(f"💾 测试结果已保存: {output_file}")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")

    # 全局统计分析
    print("\n" + "=" * 60)
    print("📊 全局测试统计")
    print("=" * 60)

    if all_chunks_data:
        print(f"📈 总体数据:")
        print(f"   测试视频数: {total_videos}")
        print(f"   总chunk数: {total_chunks}")
        print(f"   平均每视频: {total_chunks/total_videos:.1f} chunks")

        print(f"\n📏 完整JSON Chunk大小统计:")
        print(f"   全局最小: {min(all_chunks_data):,} 字符")
        print(f"   全局最大: {max(all_chunks_data):,} 字符")
        print(f"   全局平均: {sum(all_chunks_data)/len(all_chunks_data):.0f} 字符")
        print(f"   全局中位数: {sorted(all_chunks_data)[len(all_chunks_data)//2]:,} 字符")

        # 长度分布统计
        ranges = [
            (0, 1000), (1000, 2000), (2000, 2500),
            (2500, 3000), (3000, 4000), (4000, 10000)
        ]
        print(f"\n📊 长度分布:")
        for min_len, max_len in ranges:
            count = sum(1 for l in all_chunks_data if min_len <= l < max_len)
            if count > 0:
                percentage = count / len(all_chunks_data) * 100
                print(f"   {min_len:,}-{max_len:,}: {count:3d} 个 ({percentage:.1f}%)")

    print("\n" + "=" * 60)
    print("✅ 扩大测试完成！")


def main():
    """主函数"""
    test_youtube_chunker()


if __name__ == "__main__":
    main()
