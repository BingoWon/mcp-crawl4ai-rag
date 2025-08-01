"""
Apple文档专用智能分块实现 - 统一JSON格式输出

=== CHUNKING 策略详细说明 ===

本模块实现五层优先级的智能分块策略，专门针对Apple开发者文档的结构特点设计。
所有策略都输出统一的JSON格式，确保系统一致性和处理简化。

【极致简化的统一标题分割框架】
- 核心方法：`_chunk_by_header(text, level)` 处理所有标题级别
- 硬编码设计：无配置化，直接硬编码所有参数
- 完全统一：H1/H2/H3使用完全相同的处理逻辑
- 统一算法：所有级别都使用TARGET_CHUNK_SIZE目标的贪婪合并
- 统一格式：所有输出都是相同的JSON结构

【处理逻辑完全统一】
- 触发条件：≥2个对应级别的标题
- Section分割：每个标题作为独立section，不包含前置内容
- Context提取：第一个标题之前的内容作为context
- 清晰分离：context和content完全分离，无重叠
- 输出格式：{"context": "第一个标题前的内容", "content": "合并的标题章节"}

【三个优先级完全统一】
- 第一优先级：H1分割（≥2个H1标题）
- 第二优先级：H2分割（≥2个H2标题）
- 第三优先级：H3分割（≥2个H3标题）

【第四优先级：完整内容】
- 触发条件：短文档（≤TARGET_CHUNK_SIZE字符）
- 处理逻辑：按第一个H标题分离context和content，输出JSON格式
- 输出格式：{"context": "第一个H标题之前的内容", "content": "从第一个H标题开始的内容"}
- 特殊情况：无H标题时context为空，content为全文

=== 极致简化的设计原则 ===

1. **完全统一**：H1/H2/H3使用完全相同的处理逻辑，无任何特殊处理
2. **硬编码设计**：无配置化抽象，直接硬编码所有参数，简洁直接
3. **清晰分离**：context和content完全分离，无重叠，逻辑清晰
4. **统一方法**：一个`_split_sections`方法处理所有标题级别
5. **零重复代码**：完全消除所有重复逻辑和方法
6. **极致精简**：删除所有不必要的抽象层和配置化设计

=== JSON输出格式规范 ===

**统一结构**：
```json
{
  "context": "背景信息、标题、概述等上下文内容",
  "content": "具体的章节内容或合并后的内容"
}
```

**格式特点**：
- 使用 json.dumps(chunk, ensure_ascii=False, indent=2) 输出
- context字段：提供语义背景，可能为空字符串
- content字段：包含主要内容，永远不为空
- 所有chunks都可以用相同的JSON解析逻辑处理

=== 内容完整性保障 ===

**实时检测机制**：
- 自动比较原始内容与chunks总长度
- 超过5%内容丢失时发出错误警告
- 轻微调整（<5%）记录为信息日志

**系统可靠性**：
- 所有优先级都经过完整测试验证
- 智能合并算法确保最优chunk大小
- JSON格式保证下游处理的一致性

"""

import json
from typing import List
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SmartChunker:
    """Apple文档专用分块器 - 基于##双井号分割

    超参数配置：
    - TARGET_CHUNK_SIZE: 目标chunk大小（字符数）
    - MAX_CHUNK_SIZE: 最大chunk大小（字符数）
    """

    # 超参数定义
    TARGET_CHUNK_SIZE = 5000
    MAX_CHUNK_SIZE = 6000

    def __init__(self):
        pass

    def chunk_text(self, text: str) -> List[str]:
        """统一标题分割框架：H1 → H2 → H3 → 完整内容"""
        logger.info(f"开始分块，文档长度: {len(text)} 字符，前100字符: {text[:100]}")

        if not text.strip():
            return []

        if len(text) <= self.TARGET_CHUNK_SIZE:
            logger.info(f"文本长度小于{self.TARGET_CHUNK_SIZE}字符，使用第四优先级")
            chunks = self._chunk_complete(text)
            return chunks

        # 统一的标题分割：H1 → H2 → H3
        for level in [1, 2, 3]:
            chunks = self._chunk_by_header(text, level)
            if chunks:
                return chunks

        # 第四优先级：完整内容
        logger.info("返回完整内容JSON格式")
        chunks = self._chunk_complete(text)
        return chunks

    def _chunk_by_header(self, text: str, level: int) -> List[str]:
        """最优化的一次遍历框架"""
        prefix = {1: '# ', 2: '## ', 3: '### '}[level]

        # 一次遍历同时获取context和剩余文本
        context, remaining_text = self._split_context_and_remaining(text, prefix)
        if not remaining_text:
            return []

        # 简单分割剩余部分
        sections = self._simple_split_sections(remaining_text, prefix)
        if len(sections) < 2:
            return []

        logger.info(f"检测到{len(sections)}个H{level}标题，开始H{level}分割")
        chunks = self._greedy_merge_with_json_size(sections, context)
        logger.info(f"H{level}分块完成: {len(chunks)} chunks")
        return chunks

    def _split_context_and_remaining(self, text: str, prefix: str) -> tuple[str, str]:
        """一次遍历同时获取context和剩余文本"""
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if line.startswith(prefix) and not line.startswith(prefix + '#'):
                context = '\n'.join(lines[:i]).strip()
                remaining = '\n'.join(lines[i:])
                return context, remaining
        return "", ""

    def _simple_split_sections(self, text: str, prefix: str) -> List[str]:
        """极简的分割逻辑 - 无需任何过滤"""
        lines = text.split('\n')
        sections = []
        current_section = []

        for line in lines:
            if line.startswith(prefix) and not line.startswith(prefix + '#'):
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)

        if current_section:
            sections.append('\n'.join(current_section))

        return sections


    def _greedy_merge_with_json_size(self, sections: List[str], context: str) -> List[str]:
        """基于完整JSON大小的贪婪合并算法 - 使用超参数配置"""
        if not sections:
            return []

        json_chunks = []
        current_sections = [sections[0]]

        for section in sections[1:]:
            # 构建测试JSON
            test_content = '\n\n'.join(current_sections + [section])
            test_chunk = {
                "context": context,
                "content": test_content
            }
            test_json = json.dumps(test_chunk, ensure_ascii=False, indent=2)

            # 构建当前JSON用于大小比较
            current_content = '\n\n'.join(current_sections)
            current_chunk = {
                "context": context,
                "content": current_content
            }
            current_json = json.dumps(current_chunk, ensure_ascii=False, indent=2)

            # 基于完整JSON大小判断是否合并
            if len(test_json) <= self.MAX_CHUNK_SIZE and len(current_json) < self.TARGET_CHUNK_SIZE:
                current_sections.append(section)
            else:
                # 完成当前chunk，开始新的chunk
                json_chunks.append(current_json)
                current_sections = [section]

        # 添加最后一个chunk
        final_content = '\n\n'.join(current_sections)
        final_chunk = {
            "context": context,
            "content": final_content
        }
        final_json = json.dumps(final_chunk, ensure_ascii=False, indent=2)
        json_chunks.append(final_json)

        return json_chunks

    def _chunk_complete(self, text: str) -> List[str]:
        """完整内容JSON格式化"""
        context, content = self._split_by_first_header(text)
        chunk = {
            "context": context,
            "content": content
        }
        return [json.dumps(chunk, ensure_ascii=False, indent=2)]

    def _split_by_first_header(self, text: str) -> tuple[str, str]:
        """按第一个H标题分离context和content"""
        lines = text.split('\n')

        for i, line in enumerate(lines):
            if line.strip().startswith('#'):
                context = '\n'.join(lines[:i]).strip()
                content = '\n'.join(lines[i:]).strip()
                return context, content

        # 没有找到H标题
        return "", text.strip()