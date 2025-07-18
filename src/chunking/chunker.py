"""
Apple文档专用智能分块实现

=== CHUNKING 策略详细说明 ===

本模块实现五层优先级的智能分块策略，专门针对Apple开发者文档的结构特点设计：

【第一优先级：H1分割】
- 触发条件：文档中有多个 # H1 标题
- 处理逻辑：按 H1 分割 → _merge_sections_by_size(max_size=4096)
- 完全独立：与 Overview 和 H2/H3 分割无关

【第二优先级：通用H2分割】
- 触发条件：文档中有多个 ## H2 标题（≥2个）
- 处理逻辑：直接按 H2 标题分割，无特殊格式要求
- 适用范围：标准API文档、技术规范等常见格式
- 优势：无内容丢失，适用性广泛

【第三优先级：特殊H2分割】
- 触发条件：文档中有 "## Overview" 且在 Overview 后面还有其他 ## 标题
- 处理逻辑：
  1. title_part: 文档开头到第一个 ## 之前的内容
  2. overview: 完整的 ## Overview 内容（到下一个 ## 停止）
  3. h2_sections: Overview 后面的所有 ## 章节
  4. 最终chunks: 每个chunk = title_part + overview + 单个后续h2_section

【第四优先级：H3分割】
- 触发条件：文档长度 > 5000字符 且 不满足H1/H2分割条件
- 处理逻辑：
  1. title_part: 文档开头到第一个 ## 之前的内容
  2. overview: 通过 _extract_overview_for_h3() 提取，到第一个 ### 停止
  3. h3_sections: 所有 ### 章节，**无条件收集所有内容**
  4. 智能合并: 小于2048字符的H3章节自动与下一个H3合并
  5. 最终chunks: 每个chunk = title_part + overview + 单个h3_section

【第五优先级：完整内容】
- 触发条件：短文档（≤5000字符）或无有效标题结构
- 处理逻辑：返回完整文档内容作为单个chunk

=== 关键设计原则 ===

1. 语义完整性：每个chunk都包含完整的上下文（背景+概述+具体内容）
2. 结构化分割：优先按文档的层次结构进行分割
3. 自适应策略：根据文档特点自动选择最适合的分割方式
4. 智能合并：避免过小的chunks，确保内容的语义完整性
5. 内容完整性：确保所有内容都被正确处理，零丢失保证

=== 内容完整性保障 ===

**实时检测机制**：
- 自动比较原始内容与chunks总长度
- 超过5%内容丢失时发出错误警告
- 轻微调整（<5%）记录为信息日志

**H3分割修复**：
- 修复了条件收集缺陷，改为无条件全量收集
- 确保H3标题前的所有内容都被正确保留
- 彻底解决了内容丢失问题

"""

from typing import List
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SmartChunker:
    """Apple文档专用分块器 - 基于##双井号分割"""

    def __init__(self):
        pass

    def chunk_text(self, text: str) -> List[str]:
        """智能分层chunking：H1优先 → 通用H2 → 特殊H2 → H3 → 完整内容"""
        logger.info(f"开始分块，文档长度: {len(text)} 字符，前100字符: {text[:100]}")

        if not text:
            return []

        if len(text) <= 5000:
            logger.info("文本长度小于5000字符，直接返回完整内容")
            chunks = [text]
            self._validate_content_integrity(text, chunks)
            return chunks

        # 第一优先级：H1分割 - 检查是否有多个H1标题
        h1_sections = self._split_h1_sections(text)
        if len(h1_sections) > 1:
            logger.info(f"检测到多个H1标题，进行H1分割: {len(h1_sections)} 个章节")
            merged_sections = self._merge_sections_by_size(h1_sections)
            logger.info(f"H1分块完成: {len(merged_sections)} chunks")
            self._validate_content_integrity(text, merged_sections)
            return merged_sections

        # 第二优先级：通用H2分割 - 有多个H2标题时使用
        h2_chunks = self._chunk_by_h2_general(text)
        if h2_chunks:
            self._validate_content_integrity(text, h2_chunks)
            return h2_chunks

        # 第三优先级：特殊H2分割 - Overview格式的H2分割
        overview_h2_chunks = self._chunk_by_h2_after_overview(text)
        if overview_h2_chunks:
            self._validate_content_integrity(text, overview_h2_chunks)
            return overview_h2_chunks

        # 第四优先级：H3分割 - 长文档且无有效H2结构时使用
        logger.info("开始第四优先级：H3分割")
        h3_sections = self._split_h3_sections(text)
        if h3_sections:
            title_part = self._extract_title_part(text)
            overview = self._extract_overview_for_h3(text)
            chunks = self._build_chunks_from_sections(title_part, overview, h3_sections)
            logger.info(f"H3分块完成: {len(chunks)} chunks")
            self._validate_content_integrity(text, chunks)
            return chunks

        # 第五优先级：完整内容
        logger.info("返回完整内容作为单个chunk")
        chunks = [text.strip()]
        self._validate_content_integrity(text, chunks)
        return chunks

    def _split_h1_sections(self, text: str) -> List[str]:
        """按H1标题分割文档，确保H1数量等于chunk数量"""
        lines = text.split('\n')
        sections = []
        current_section = []
        first_h1_found = False

        for line in lines:
            if line.startswith('# ') and not line.startswith('## '):
                if first_h1_found:  # 不是第一个H1，保存前一个section
                    sections.append('\n'.join(current_section))
                    current_section = [line]
                else:  # 第一个H1，将之前的内容也包含进来
                    current_section.append(line)
                    first_h1_found = True
            else:
                current_section.append(line)

        if current_section:
            sections.append('\n'.join(current_section))

        return sections

    def _validate_content_integrity(self, original: str, chunks: List[str]) -> None:
        """验证内容完整性，检测内容丢失并报警"""
        original_length = len(original)
        chunks_length = sum(len(chunk) for chunk in chunks)

        if chunks_length > original_length:
            # 内容重复（正常情况，因为有前缀重复）
            return

        loss_count = original_length - chunks_length
        if loss_count > 0:
            loss_ratio = loss_count / original_length
            if loss_ratio > 0.05:  # 超过5%内容丢失
                logger.error(f"⚠️ 内容丢失警告: 丢失{loss_count}字符 ({loss_ratio:.1%})")
            else:
                logger.info(f"轻微内容调整: {loss_count}字符 ({loss_ratio:.1%})")

    def _extract_title_part(self, text: str) -> str:
        """提取标题部分：从文档开始到第一个##章节"""
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('## '):
                return '\n'.join(lines[:i])
        return text

    def _chunk_by_h2_after_overview(self, text: str) -> List[str]:
        """基于Overview后的H2章节进行分块"""
        if not text:
            return []

        lines = text.split('\n')

        # 检查是否有Overview且后续有H2标题
        overview_found = False
        has_subsequent_h2 = False
        for line in lines:
            if line.strip() == '## Overview':
                overview_found = True
            elif overview_found and line.startswith('## '):
                has_subsequent_h2 = True
                break

        if not (overview_found and has_subsequent_h2):
            return []  # 不满足H2分块条件，返回空列表让其他策略处理

        logger.info("检测到Overview且后续有H2标题，开始H2分割")

        # 提取title_part（到第一个##之前）
        title_part = ""
        for i, line in enumerate(lines):
            if line.startswith('## '):
                title_part = '\n'.join(lines[:i])
                break

        # 提取完整Overview内容
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
        overview = '\n'.join(overview_lines)

        # 提取Overview后的H2章节
        h2_sections = []
        current_section = []
        overview_passed = False

        for line in lines:
            if line.strip() == '## Overview':
                overview_passed = False
                continue
            elif line.startswith('## ') and not overview_passed:
                overview_passed = True
                current_section = [line]
            elif line.startswith('## ') and overview_passed:
                if current_section:
                    h2_sections.append('\n'.join(current_section))
                current_section = [line]
            elif overview_passed and current_section:
                current_section.append(line)

        if current_section:
            h2_sections.append('\n'.join(current_section))

        if not h2_sections:
            logger.info("未找到Overview后的H2章节，返回完整内容")
            return [text]

        # 合并小章节
        logger.info(f"合并小章节前: {len(h2_sections)} 个章节")
        h2_sections = self._merge_sections_by_size(h2_sections)

        # 构建前缀内容
        prefix_parts = [p for p in [title_part, overview] if p]
        prefix_content = '\n\n'.join(prefix_parts)

        # 构建chunks
        chunks = []
        for section in h2_sections:
            if section.strip():
                chunk = f"{prefix_content}\n\n{section}" if prefix_content else section
                chunks.append(chunk)

        logger.info(f"H2分块完成: {len(chunks)} chunks")
        return chunks

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

    def _chunk_by_h2_general(self, text: str) -> List[str]:
        """通用H2分割：不依赖Overview，直接按H2标题分割"""
        if not text:
            return []

        # 检查是否有多个H2标题
        h2_count = text.count('\n## ') + (1 if text.startswith('## ') else 0)
        if h2_count < 2:
            return []

        logger.info(f"检测到{h2_count}个H2标题，开始通用H2分割")

        lines = text.split('\n')
        sections = []
        current_section = []

        for line in lines:
            if line.startswith('## '):  # 遇到H2标题
                if current_section:  # 保存前一个章节
                    sections.append('\n'.join(current_section))
                current_section = [line]  # 开始新章节
            else:  # 收集当前章节的内容
                current_section.append(line)

        if current_section:  # 保存最后一个章节
            sections.append('\n'.join(current_section))

        if not sections:
            return []

        # 合并小章节
        sections = self._merge_sections_by_size(sections)
        logger.info(f"通用H2分块完成: {len(sections)} chunks")
        return sections

    def _split_h3_sections(self, text: str) -> List[str]:
        """分割所有###章节并合并小章节，确保无内容丢失"""
        lines = text.split('\n')
        sections = []
        current_section = []

        for line in lines:
            if line.startswith('### '):  # 遇到H3标题
                if current_section:  # 保存前一个章节
                    sections.append('\n'.join(current_section))
                current_section = [line]  # 开始新章节
            else:  # 无条件收集所有内容
                current_section.append(line)

        if current_section:  # 保存最后一个章节
            sections.append('\n'.join(current_section))

        return self._merge_sections_by_size(sections)

    def _merge_sections_by_size(self, sections: List[str], threshold: int = 2048, max_size: int = 4096) -> List[str]:
        """按大小合并章节：小于阈值的章节与下一个章节合并"""
        if not sections:
            return sections

        merged = []
        i = 0

        while i < len(sections):
            current = sections[i]

            # 如果当前章节小于阈值且不是最后一个章节
            if len(current) < threshold and i + 1 < len(sections):
                next_section = sections[i + 1]
                merged_section = current + '\n\n' + next_section

                # 检查合并后是否超过最大大小限制
                if len(merged_section) <= max_size:
                    merged.append(merged_section)
                    i += 2  # 跳过下一个章节
                else:
                    # 合并后过大，保持原状
                    merged.append(current)
                    i += 1
            else:
                merged.append(current)
                i += 1

        return merged

    def _build_chunks_from_sections(self, title_part: str, overview: str, sections: List[str]) -> List[str]:
        """从sections构建chunks（用于H3分块）"""
        chunks = []
        for section in sections:
            if section.strip():
                parts = [p for p in [title_part, overview, section] if p]
                chunks.append('\n\n'.join(parts))
        return chunks
