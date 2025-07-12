"""
Chunking Strategy Definitions
分块策略定义

Defines the chunking strategies and their explanations.
定义分块策略及其说明。
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum


class BreakPointType(Enum):
    """分割点类型"""
    MARKDOWN_HEADER = "markdown_header"  # Markdown 标题 (## ### ####)
    PARAGRAPH = "paragraph"              # 段落分隔符 (\n\n)
    NEWLINE = "newline"                  # 单行换行符 (\n)
    SENTENCE = "sentence"                # 句子结尾 (. ! ?)
    FORCE = "force"                      # 强制分割


@dataclass
class ChunkInfo:
    """Chunk 信息"""
    content: str
    start_pos: int
    end_pos: int
    break_type: BreakPointType
    chunk_index: int


@dataclass
class ChunkingStrategy:
    """分块策略配置和说明"""
    
    # 默认配置
    DEFAULT_CHUNK_SIZE = 5000
    
    # 策略说明
    STRATEGY_DESCRIPTION = {
        "title": "智能文本分块策略",
        "description": "基于内容结构的优先级分块算法，确保语义完整性",
        "priorities": [
            {
                "level": 1,
                "type": "Markdown 标题",
                "pattern": "##",
                "description": "优先在 Markdown 二级标题处分割，保持文档逻辑结构完整"
            },
            {
                "level": 2,
                "type": "段落分隔符",
                "pattern": "\\n\\n",
                "description": "在段落边界分割，保持段落完整性"
            },
            {
                "level": 3,
                "type": "换行符",
                "pattern": "\\n",
                "description": "在行边界分割，适合代码和列表内容"
            },
            {
                "level": 4,
                "type": "句子结尾",
                "pattern": ". ! ?",
                "description": "在句子边界分割，保持句子完整性"
            },
            {
                "level": 5,
                "type": "强制分割",
                "pattern": "字符位置",
                "description": "当无法找到合适分割点时的兜底策略"
            }
        ]
    }
    
    @classmethod
    def get_strategy_info(cls) -> Dict[str, Any]:
        """获取策略信息"""
        return cls.STRATEGY_DESCRIPTION
    
    @classmethod
    def get_break_point_colors(cls) -> Dict[BreakPointType, str]:
        """获取不同分割点类型的颜色配置"""
        return {
            BreakPointType.PARAGRAPH: "#e3f2fd",  # 浅蓝色
            BreakPointType.NEWLINE: "#f3e5f5",    # 浅紫色
            BreakPointType.SENTENCE: "#e8f5e8",   # 浅绿色
            BreakPointType.FORCE: "#fff3e0"       # 浅橙色
        }
