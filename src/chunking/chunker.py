"""
Apple文档专用智能分块实现

=== CHUNKING 策略详细说明 ===

本模块实现三层优先级的智能分块策略，专门针对Apple开发者文档的结构特点设计：

【第一优先级：H2分割】
- 触发条件：存在除 "## Overview" 外的其他 ## 标题
- 处理逻辑：
  1. title_part: 文档开头到第一个 ## 之前的内容
  2. overview: 通过 _extract_overview_for_h2() 提取，到下一个 ## 停止
  3. h2_sections: 除 Overview 外的所有 ## 章节
  4. 最终chunks: 每个chunk = title_part + overview + 单个h2_section

【第二优先级：H3分割】
- 触发条件：文档长度 > 5000字符 且 没有其他H2标题（通常只有 ## Overview）
- 处理逻辑：
  1. title_part: 文档开头到第一个 ## 之前的内容
  2. overview: 通过 _extract_overview_for_h3() 提取，到第一个 ### 停止
  3. h3_sections: 所有 ### 章节（包括 Overview 内的 ###）
  4. 智能合并: 小于256字符的H3章节自动与下一个H3合并
  5. 最终chunks: 每个chunk = title_part + overview + 单个h3_section

【第三优先级：完整内容】
- 触发条件：短文档（≤5000字符）或无有效标题结构
- 处理逻辑：返回完整文档内容作为单个chunk

=== 关键设计原则 ===

1. 语义完整性：每个chunk都包含完整的上下文（背景+概述+具体内容）
2. 结构化分割：优先按文档的层次结构进行分割
3. 自适应策略：根据文档特点自动选择最适合的分割方式
4. 智能合并：避免过小的chunks，确保内容的语义完整性
5. 内容无丢失：确保所有内容都被正确处理，无遗漏

=== H3章节智能合并策略 ===

**合并条件**：H3章节内容少于256字符
**合并方式**：与下一个H3章节合并为单个chunk
**优化效果**：
- 消除过小的chunks，提高检索效果
- 保持相关内容的语义连贯性
- 平衡chunk大小分布，优化整体质量

=== Overview 处理差异 ===

- H2分割时：Overview 包含到下一个 ## 之前的所有内容（可能包含 ### 内容）
- H3分割时：Overview 只包含到第一个 ### 之前的纯概述内容
- 这种差异确保了不同分割策略下的语义一致性

"""

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
        
        if len(text) <= 2048:
            return [text]

        # 提取文档标题部分（到第一个 ## 之前）
        title_part = self._extract_title_part(text)

        # 第一优先级：H2分割 - 检查是否有除Overview外的其他##标题
        h2_sections = self._split_h2_sections(text)
        if len(h2_sections) > 1:
            # H2分割时：Overview 包含到下一个 ## 之前的所有内容
            overview = self._extract_overview_for_h2(text)
            # 如果overview长度大于文档长度的一半 且 小于7000字符，则不进行分块
            if (len(text) // 2) < len(overview) < 7000:
                return [text]
            
            chunks = self._build_chunks_from_sections(title_part, overview, h2_sections)
            logger.info(f"##标题分块完成: {len(chunks)} chunks")
            return chunks

        # 第二优先级：H3分割 - 长文档且无其他H2标题时使用
        if len(text) > 5000:
            h3_sections = self._split_h3_sections(text)
            if h3_sections:
                # H3分割时：Overview 只包含到第一个 ### 之前的纯概述内容
                overview = self._extract_overview_for_h3(text)
                chunks = self._build_chunks_from_sections(title_part, overview, h3_sections)
                logger.info(f"###标题分块完成: {len(chunks)} chunks (长内容)")
                return chunks

        # 第三优先级：完整内容 - 短文档或无有效标题结构
        chunk = text.strip()
        logger.info(f"完整内容分块: 1 chunk ({'短内容' if len(text) <= 5000 else '无有效标题'})")
        return [chunk]



    def _extract_title_part(self, text: str) -> str:
        """提取标题部分：从文档开始到第一个##章节"""
        lines = text.split('\n')

        for i, line in enumerate(lines):
            if line.startswith('## '):  # 遇到第一个H2标题时停止
                return '\n'.join(lines[:i])

        return text  # 如果没有H2标题，返回整个文档

    def _extract_overview_for_h2(self, text: str) -> str:
        """H2分割时的Overview提取：到下一个##停止"""
        lines = text.split('\n')
        overview_lines = []
        in_overview = False

        for line in lines:
            if line.strip() == '## Overview':  # 找到Overview开始
                in_overview = True
                overview_lines.append(line)
            elif in_overview and line.startswith('## '):  # 遇到下一个H2时停止
                break
            elif in_overview:
                overview_lines.append(line)

        return '\n'.join(overview_lines) if overview_lines else ""

    def _extract_overview_for_h3(self, text: str) -> str:
        """H3分割时的Overview提取：到###停止或文档末尾"""
        lines = text.split('\n')
        overview_lines = []
        in_overview = False

        for line in lines:
            if line.strip() == '## Overview':  # 找到Overview开始
                in_overview = True
                overview_lines.append(line)
            elif in_overview and line.startswith('### '):  # 遇到第一个H3时停止
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
                if line.strip() == '## Overview':  # 跳过Overview章节
                    continue

                if current_section:  # 保存前一个章节
                    sections.append('\n'.join(current_section))
                current_section = [line]  # 开始新章节
            elif current_section:  # 收集当前章节的内容
                current_section.append(line)

        if current_section:  # 保存最后一个章节
            sections.append('\n'.join(current_section))

        return sections

    def _split_h3_sections(self, text: str) -> List[str]:
        """分割所有###章节（包括Overview内的H3）并合并小章节"""
        lines = text.split('\n')
        sections = []
        current_section = []

        for line in lines:
            if line.startswith('### '):  # 遇到H3标题
                if current_section:  # 保存前一个章节
                    sections.append('\n'.join(current_section))
                current_section = [line]  # 开始新章节
            elif current_section:  # 收集当前章节的内容
                current_section.append(line)

        if current_section:  # 保存最后一个章节
            sections.append('\n'.join(current_section))

        return self._merge_small_sections(sections)

    def _merge_small_sections(self, sections: List[str]) -> List[str]:
        """合并小于256字符的H3章节"""
        if not sections:
            return sections

        merged = []
        i = 0

        while i < len(sections):
            current = sections[i]

            # 如果当前章节小于256字符且不是最后一个章节
            if len(current) < 256 and i + 1 < len(sections):
                # 与下一个章节合并
                next_section = sections[i + 1]
                merged_section = current + '\n\n' + next_section
                merged.append(merged_section)
                i += 2  # 跳过下一个章节
            else:
                merged.append(current)
                i += 1

        return merged

    def _build_chunks_from_sections(self, title_part: str, overview: str, sections: List[str]) -> List[str]:
        """从sections构建chunks"""
        chunks = []
        for section in sections:
            if section.strip():  # 跳过空章节
                # 每个chunk = 标题部分 + 概述部分 + 具体章节
                chunk_content = self._build_chunk_content(title_part, overview, section)
                chunks.append(chunk_content)
        return chunks

    def _build_chunk_content(self, title_part: str, overview: str, section: str) -> str:
        """构建chunk内容：标题部分 + Overview(可选) + 当前章节"""
        parts = []

        if title_part:  # 添加标题部分（文档背景）
            parts.append(title_part)

        if overview:  # 添加概述部分（上下文信息）
            parts.append(overview)

        if section:  # 添加具体章节（主要内容）
            parts.append(section)

        return '\n\n'.join(parts)  # 用双换行分隔各部分
