"""Apple文档专用双井号分块实现"""

from typing import List
from dataclasses import dataclass
from enum import Enum
from utils.logger import setup_logger

logger = setup_logger(__name__)


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
        """基于##双井号分割文本，每个chunk包含前置内容+Overview+当前章节"""
        logger.info(f"开始分块处理，文档长度: {len(text)} 字符")

        if not text:
            logger.warning("输入文档为空，返回空列表")
            return []

        # 提取第一部分（前置内容 + Overview）
        first_part = self._extract_first_part(text)
        logger.info(f"提取第一部分完成，长度: {len(first_part)} 字符")

        # 分割Overview后的双井号章节
        sections = self._split_sections_after_overview(text)
        logger.info(f"章节分割完成，发现 {len(sections)} 个章节")

        # 构建chunks：第一部分 + 每个章节
        chunks = []
        for i, section in enumerate(sections):
            if section.strip():
                chunk_content = self._build_chunk_content(first_part, section)
                chunks.append(ChunkInfo(
                    content=chunk_content,
                    start_pos=0,  # 新chunk不保留原始位置
                    end_pos=len(chunk_content),
                    break_type=BreakPointType.MARKDOWN_HEADER,
                    chunk_index=i
                ))

        logger.info(f"分块处理完成，生成 {len(chunks)} 个chunks")
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
            result = '\n'.join(first_part_lines)
            logger.debug(f"第一部分提取成功，包含 {len(first_part_lines)} 行")
            return result

        # 如果没有找到Overview，返回空字符串
        logger.warning("未找到Overview章节，第一部分为空")
        return ""

    def _split_sections_after_overview(self, text: str) -> List[str]:
        """从Overview后开始分割双井号章节"""
        lines = text.split('\n')
        sections = []
        current_section = []
        overview_passed = False

        for line in lines:
            if line.strip() == '## Overview':
                overview_passed = True
                continue
            elif overview_passed and line.startswith('## '):
                # 保存前一个章节
                if current_section:
                    sections.append('\n'.join(current_section))
                # 开始新章节
                current_section = [line]
            elif overview_passed and current_section:
                # 在Overview后且已经开始收集章节内容
                current_section.append(line)

        # 添加最后一个章节
        if current_section:
            sections.append('\n'.join(current_section))

        logger.debug(f"章节分割详情: {[section.split('\\n')[0] for section in sections]}")
        return sections

    def _build_chunk_content(self, first_part: str, section: str) -> str:
        """构建chunk内容：第一部分 + 当前章节"""
        parts = []

        if first_part:
            parts.append(first_part)

        if section:
            parts.append(section)

        return '\n\n'.join(parts)
