"""Apple文档专用双井号分块实现"""

from typing import List
from dataclasses import dataclass
from enum import Enum


class BreakPointType(Enum):
    """分割点类型 - 简化为只支持双井号分割"""
    MARKDOWN_HEADER = "markdown_header"  # Markdown 双井号标题 (##)


@dataclass
class ChunkInfo:
    """Chunk 信息"""
    content: str
    start_pos: int
    end_pos: int
    break_type: BreakPointType
    chunk_index: int


class SmartChunker:
    """Apple文档专用分块器 - 基于##双井号分割"""

    def __init__(self):
        """初始化分块器 - 不再需要chunk_size参数"""
        pass

    def chunk_text(self, text: str) -> List[ChunkInfo]:
        """基于##双井号分割文本，每个chunk包含大标题+Overview+当前章节"""
        if not text:
            return []

        # 提取大标题区域和Overview
        title_section, overview = self._extract_title_and_overview(text)

        # 按##分割章节
        sections = self._split_by_double_hash(text)

        # 构建chunks
        chunks = []
        for i, section in enumerate(sections):
            if section.strip():
                chunk_content = self._build_chunk_content(title_section, overview, section)
                chunks.append(ChunkInfo(
                    content=chunk_content,
                    start_pos=0,  # 新chunk不保留原始位置
                    end_pos=len(chunk_content),
                    break_type=BreakPointType.MARKDOWN_HEADER,
                    chunk_index=i
                ))

        return chunks

    def chunk_text_simple(self, text: str) -> List[str]:
        """简单分块接口，只返回文本内容"""
        chunk_infos = self.chunk_text(text)
        return [chunk.content for chunk in chunk_infos]

    def _extract_first_part(self, text: str) -> str:
        """提取第一部分：从文档开始到Overview结束的所有内容"""
        lines = text.split('\n')

        # 查找Overview结束位置
        overview_end = -1
        overview_found = False

        for i, line in enumerate(lines):
            if line.strip() == '## Overview':
                overview_found = True
            elif overview_found and line.startswith('## ') and line.strip() != '## Overview':
                overview_end = i
                break

        # 如果找到Overview，提取到Overview结束的内容
        if overview_found:
            if overview_end >= 0:
                first_part_lines = lines[:overview_end]
            else:
                # 如果没有找到Overview后的其他章节，取到文档结尾
                first_part_lines = lines
            return '\n'.join(first_part_lines)

        # 如果没有找到Overview，返回空字符串
        return ""

    def _split_by_double_hash(self, text: str) -> List[str]:
        """按##双井号分割文本，跳过Overview"""
        sections = []
        lines = text.split('\n')
        current_section = []
        in_overview = False

        for line in lines:
            if line.startswith('## '):
                if line.strip() == '## Overview':
                    in_overview = True
                    if current_section:
                        sections.append('\n'.join(current_section))
                        current_section = []
                    continue
                else:
                    in_overview = False
                    if current_section:
                        sections.append('\n'.join(current_section))
                    current_section = [line]
            elif not in_overview and current_section:
                current_section.append(line)

        # 添加最后一个section
        if current_section:
            sections.append('\n'.join(current_section))

        return sections

    def _build_chunk_content(self, title_section: str, overview: str, section: str) -> str:
        """构建chunk内容：大标题区域 + Overview + 当前章节"""
        parts = []

        if title_section:
            parts.append(title_section)

        if overview:
            parts.append(overview)

        if section:
            parts.append(section)

        return '\n\n'.join(parts)
