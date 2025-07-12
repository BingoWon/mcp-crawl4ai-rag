"""Smart text chunking implementation."""

from typing import List, Tuple
from .strategy import ChunkInfo, BreakPointType, ChunkingStrategy


class SmartChunker:
    def __init__(self, chunk_size: int = ChunkingStrategy.DEFAULT_CHUNK_SIZE):
        self.chunk_size = chunk_size
    
    def chunk_text(self, text: str) -> List[ChunkInfo]:
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        chunk_index = 0
        
        while start < text_length:
            remaining_length = text_length - start

            # 如果剩余文本长度 <= chunk_size * 1.2，直接作为最后一个块
            # 提供宽容度，避免产生很小的残留块
            if remaining_length <= self.chunk_size * 1.2:
                end = text_length
                break_type = BreakPointType.FORCE
            else:
                # 否则寻找最佳分割点
                end = start + self.chunk_size
                end, break_type = self._find_best_break_point(text, start, end)

            # 提取块内容
            chunk_content = text[start:end].strip()
            if chunk_content:
                chunks.append(ChunkInfo(
                    content=chunk_content,
                    start_pos=start,
                    end_pos=end,
                    break_type=break_type,
                    chunk_index=chunk_index
                ))
                chunk_index += 1

            start = end
        
        return chunks
    
    def chunk_text_simple(self, text: str) -> List[str]:
        """简单分块，只返回文本内容（兼容原有接口）
        
        Args:
            text: 要分割的文本
            
        Returns:
            文本块列表
        """
        chunk_infos = self.chunk_text(text)
        return [chunk.content for chunk in chunk_infos]
    
    def _find_best_break_point(self, text: str, start: int, end: int) -> Tuple[int, BreakPointType]:
        # 优先级1: Markdown 标题 (仅 ##)
        pos = text.rfind('\n## ', start, end)
        if pos > start:
            return pos + 1, BreakPointType.MARKDOWN_HEADER

        # 优先级2: 段落分隔符 (\n\n)
        pos = text.rfind('\n\n', start, end)
        if pos > start:
            return pos + 2, BreakPointType.PARAGRAPH

        # 优先级3: 换行符 (\n)
        pos = text.rfind('\n', start, end)
        if pos > start:
            return pos + 1, BreakPointType.NEWLINE

        # 优先级4: 句子结尾 (. ! ?)
        for punct in ['. ', '! ', '? ']:
            pos = text.rfind(punct, start, end)
            if pos > start:
                return pos + 2, BreakPointType.SENTENCE

        # 兜底: 强制分割
        return end, BreakPointType.FORCE
