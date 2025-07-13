"""
Chunking Module
文本分块模块

Apple文档专用双井号分块模块。
Apple documentation specialized double-hash chunking module.
"""

from .chunker import SmartChunker, ChunkInfo, BreakPointType

__all__ = ['SmartChunker', 'ChunkInfo', 'BreakPointType']
