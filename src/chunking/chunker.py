"""Apple文档专用双井号分块实现"""

from typing import List
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SmartChunker:
    """Apple文档专用分块器 - 基于##双井号分割"""

    def __init__(self):
        pass

    def chunk_text(self, text: str) -> List[str]:
        """智能分层chunking：##优先 → ###长内容 → 完整短内容"""
        logger.info(f"开始智能分块处理，文档长度: {len(text)} 字符")

        if not text:
            return []

        title_part = self._extract_title_part(text)
        overview = self._extract_overview(text)

        # 第一优先级：检查是否有除Overview外的##标题
        h2_sections = self._split_h2_sections(text)
        if h2_sections:
            chunks = self._build_chunks_from_sections(title_part, overview, h2_sections)
            logger.info(f"##标题分块完成: {len(chunks)} chunks")
            return chunks

        # 第二/三优先级：基于内容长度决策
        content_length = len(text)
        if content_length > 5000:
            # 长内容：尝试###标题分割
            h3_sections = self._split_h3_sections(text)
            if h3_sections:
                chunks = self._build_chunks_from_sections(title_part, overview, h3_sections)
                logger.info(f"###标题分块完成: {len(chunks)} chunks (长内容)")
                return chunks

        # 短内容或无有效标题：返回完整内容
        chunk = text.strip()
        logger.info(f"完整内容分块: 1 chunk ({'短内容' if content_length <= 5000 else '无有效标题'})")
        return [chunk]

    def chunk_text_simple(self, text: str) -> List[str]:
        """简单分块接口，只返回文本内容"""
        return self.chunk_text(text)

    def _extract_title_part(self, text: str) -> str:
        """提取标题部分：从文档开始到第一个##章节"""
        lines = text.split('\n')

        for i, line in enumerate(lines):
            if line.startswith('## '):
                return '\n'.join(lines[:i])

        return text

    def _extract_overview(self, text: str) -> str:
        """提取Overview章节内容，如果不存在则返回空字符串"""
        lines = text.split('\n')
        overview_lines = []
        in_overview = False

        for line in lines:
            if line.strip() == '## Overview':
                in_overview = True
                overview_lines.append(line)
            elif in_overview and line.startswith('## '):
                break
            elif in_overview:
                overview_lines.append(line)

        return '\n'.join(overview_lines) if overview_lines else ""

    def _split_h2_sections(self, text: str) -> List[str]:
        """分割所有##章节，排除Overview章节"""
        lines = text.split('\n')
        sections = []
        current_section = []

        for line in lines:
            if line.startswith('## '):
                if line.strip() == '## Overview':
                    continue

                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            elif current_section:
                current_section.append(line)

        if current_section:
            sections.append('\n'.join(current_section))

        return sections

    def _split_h3_sections(self, text: str) -> List[str]:
        """分割所有###章节，排除Overview章节"""
        lines = text.split('\n')
        sections = []
        current_section = []

        for line in lines:
            if line.startswith('### '):
                if line.strip() == '### Overview':
                    continue

                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            elif current_section:
                current_section.append(line)

        if current_section:
            sections.append('\n'.join(current_section))

        return sections

    def _build_chunks_from_sections(self, title_part: str, overview: str, sections: List[str]) -> List[str]:
        """从sections构建chunks"""
        chunks = []
        for section in sections:
            if section.strip():
                chunk_content = self._build_chunk_content(title_part, overview, section)
                chunks.append(chunk_content)
        return chunks

    def _build_chunk_content(self, title_part: str, overview: str, section: str) -> str:
        """构建chunk内容：标题部分 + Overview(可选) + 当前章节"""
        parts = []

        if title_part:
            parts.append(title_part)

        if overview:
            parts.append(overview)

        if section:
            parts.append(section)

        return '\n\n'.join(parts)
