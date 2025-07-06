"""
Embedding Providers
嵌入提供者

Collection of embedding provider implementations.
嵌入提供者实现集合。
"""

from .local_qwen3 import LocalQwen3Provider
from .siliconflow_api import SiliconFlowProvider

__all__ = [
    "LocalQwen3Provider",
    "SiliconFlowProvider"
]
