"""
Unified Embedding Module
统一嵌入模块

Modern, elegant embedding architecture with no redundancy.
现代化、优雅的嵌入架构，无任何冗余。
"""

from .core import EmbeddingProvider, get_embedder, create_embedding, reset_embedder
from .config import EmbeddingConfig
from .providers import LocalQwen3Provider, SiliconFlowProvider

__all__ = [
    "EmbeddingProvider",
    "EmbeddingConfig",
    "LocalQwen3Provider",
    "SiliconFlowProvider",
    "get_embedder",
    "create_embedding",
    "reset_embedder"
]
