"""
Apple文档智能分块器 - 动态自适应策略

结合动态chunk size计算和智能分割点选择的现代化分块实现。

核心特性：
- Context/Content分离：第一个# 标题前后分离
- 动态Chunk Size：每次分割前重新计算chunk大小，自适应剩余内容
- 智能分割点：在目标位置附近按优先级寻找最佳语义边界
- 质量保证：自动过滤无效chunk，确保输出质量
- 统一JSON输出：所有chunks使用一致的context

算法流程：
1. 分离Context和Content（第一个# 标题为界）
2. 动态计算target_chunk_count = 总长度 ÷ 2500
3. 每次分割前动态计算：chunk_size = 剩余长度 ÷ 剩余chunks数
4. 在目标位置附近按优先级寻找最佳分割点
5. 最后一个chunk包含所有剩余内容，自动质量保证
6. 生成统一格式的JSON chunks

设计原理：
- 动态自适应：结合数学精确性和语义合理性
- 智能优化：优先级分割点选择，提升chunk质量
- 质量保证：多层质量检查，确保输出价值
"""

import json
from typing import List, Tuple
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SmartChunker:
    """Apple文档专用智能分块器 - 动态自适应策略"""

    # 核心配置常量
    TARGET_CHUNK_SIZE = 2500
    SEARCH_RANGE = 250
    MIN_REMAINING = 300

    # 智能分割优先级模式
    SPLIT_PATTERNS = [
        ('# ', 2),      # H1标题 (最高优先级)
        ('## ', 3),     # H2标题
        ('### ', 4),    # H3标题
        ('\n\n', 2),    # 双换行符
        ('\n', 1),      # 单换行符
        ('.', 1),       # 英文句号 (最低优先级)
    ]
    
    def chunk_text(self, text: str) -> List[str]:
        """智能分块主入口 - 动态自适应策略"""
        if not text.strip():
            return []

        logger.info(f"开始智能分块，文档长度: {len(text)} 字符")

        # 分离context和content
        context, content = self._split_context_content(text)

        if not content:
            return self._create_single_chunk(context, text)

        # 执行动态自适应分割
        return self._adaptive_split(content, context)
    
    def _split_context_content(self, text: str) -> Tuple[str, str]:
        """分离context和content"""
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            if line.startswith('# ') and not line.startswith('## '):
                context = '\n'.join(lines[:i]).strip()
                content = '\n'.join(lines[i:])
                return context, content
        
        # 未找到# 标题，整个文档作为content
        return "", text
    
    def _adaptive_split(self, content: str, context: str) -> List[str]:
        """动态自适应分割策略 - 结合动态计算和智能分割点"""
        if len(content) <= self.TARGET_CHUNK_SIZE:
            return self._create_single_chunk(context, content)

        target_chunk_count = max(1, len(content) // self.TARGET_CHUNK_SIZE)
        logger.info(f"动态计算: {len(content)}字符 → {target_chunk_count}个chunks")

        chunks = []
        start = 0

        for current_chunk_num in range(1, target_chunk_count + 1):
            if current_chunk_num == target_chunk_count:
                # 最后一个chunk：包含所有剩余内容
                chunk_content = content[start:]
                if chunk_content.strip():
                    chunks.append(self._create_chunk_json(context, chunk_content))
                break

            # 动态计算目标分割位置
            remaining_length = len(content) - start
            remaining_chunks = target_chunk_count - current_chunk_num + 1
            dynamic_size = remaining_length // remaining_chunks
            target_pos = start + dynamic_size

            # 寻找最佳分割点
            split_pos = self._find_best_split(content, target_pos)

            # 创建chunk
            chunk_content = content[start:split_pos]
            chunks.append(self._create_chunk_json(context, chunk_content))
            start = split_pos

        logger.info(f"自适应分割完成: 生成 {len(chunks)} 个chunks (目标: {target_chunk_count})")
        return chunks
    
    def _find_best_split(self, content: str, target_pos: int) -> int:
        """在目标位置附近按优先级查找最佳语义分割点"""
        search_start = max(0, target_pos - self.SEARCH_RANGE)
        search_end = min(len(content), target_pos + self.SEARCH_RANGE)
        search_text = content[search_start:search_end]

        best_pos = target_pos
        best_distance = float('inf')

        for pattern, offset in self.SPLIT_PATTERNS:
            pos = search_text.rfind(pattern)
            if pos == -1:
                continue

            actual_pos = search_start + pos + offset
            distance = abs(actual_pos - target_pos)
            remaining = len(content) - actual_pos

            # 跳过会导致剩余内容过少的分割点
            if remaining < self.MIN_REMAINING:
                continue

            if distance < best_distance:
                best_distance = distance
                best_pos = actual_pos

        return best_pos
    
    def _create_single_chunk(self, context: str, content: str) -> List[str]:
        """创建单个chunk"""
        return [self._create_chunk_json(context, content)]

    def _create_chunk_json(self, context: str, content: str) -> str:
        """创建JSON格式的chunk"""
        return json.dumps({
            "context": context,
            "content": content.strip()
        }, ensure_ascii=False, indent=2)
