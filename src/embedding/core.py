"""
Embedding Core
嵌入核心

Process-safe unified embedding interfaces and factory system.
进程安全的统一嵌入接口和工厂系统。
"""

import os
import threading
from abc import ABC, abstractmethod
from typing import List, Optional

from .config import EmbeddingConfig


class EmbeddingProvider(ABC):
    """Abstract base class for all embedding providers"""

    def __init__(self, config: EmbeddingConfig):
        self.config = config

    @abstractmethod
    def encode_single(
        self,
        text: str,
        is_query: bool = False
    ) -> List[float]:
        """
        Encode single text to embedding with L2 normalization

        Args:
            text: Text to encode
            is_query: Whether text is a query (vs document)

        Returns:
            L2 normalized embedding vector as list of floats
        """
        pass
    
    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Get embedding dimension"""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get model name"""
        pass


# Process-safe global embedding provider instance
_global_embedder: Optional[EmbeddingProvider] = None
_embedder_lock = threading.Lock()
_current_pid = None


def get_embedder(config: Optional[EmbeddingConfig] = None) -> EmbeddingProvider:
    """
    Get or create process-safe global embedding provider instance

    Args:
        config: Optional configuration, uses default if None

    Returns:
        Embedding provider instance
    """
    global _global_embedder, _current_pid

    # Check if we're in a different process (after fork)
    current_pid = os.getpid()

    with _embedder_lock:
        if _global_embedder is None or _current_pid != current_pid:
            # Set TOKENIZERS_PARALLELISM to prevent fork conflicts
            os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

            _current_pid = current_pid
            if config is None:
                config = EmbeddingConfig()

            if config.provider == "api":
                from .providers import SiliconFlowProvider
                _global_embedder = SiliconFlowProvider(config)
            else:
                from .providers import LocalQwen3Provider
                _global_embedder = LocalQwen3Provider(config)

    return _global_embedder


def reset_embedder() -> None:
    """Reset the global embedder instance (for testing only)"""
    global _global_embedder, _current_pid
    with _embedder_lock:
        _global_embedder = None
        _current_pid = None


def create_embedding(text: str, is_query: bool = False) -> List[float]:
    """
    Create L2 normalized embedding for single text

    Args:
        text: Text to encode
        is_query: Whether text is a query

    Returns:
        L2 normalized embedding vector as list of floats
    """
    embedder = get_embedder()
    return embedder.encode_single(text, is_query=is_query)


def reset_embedder() -> None:
    """Reset global embedder instance (useful for testing)"""
    global _global_embedder
    _global_embedder = None
