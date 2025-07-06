"""
Embedding Core
嵌入核心

Unified embedding interfaces and factory system.
统一的嵌入接口和工厂系统。
"""

from abc import ABC, abstractmethod
from typing import List, Union, Optional
import torch

from .config import EmbeddingConfig


class EmbeddingProvider(ABC):
    """Abstract base class for all embedding providers"""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
    
    @abstractmethod
    def encode(
        self, 
        texts: Union[str, List[str]], 
        is_query: bool = False,
        normalize: bool = True
    ) -> torch.Tensor:
        """
        Encode texts to embeddings
        
        Args:
            texts: Text(s) to encode
            is_query: Whether texts are queries (vs documents)
            normalize: Whether to L2 normalize embeddings
            
        Returns:
            Embeddings tensor [batch_size, embedding_dim]
        """
        pass
    
    @abstractmethod
    def encode_batch(
        self,
        texts: List[str],
        is_query: bool = False,
        normalize: bool = True
    ) -> List[List[float]]:
        """
        Encode batch of texts to list of embeddings
        
        Args:
            texts: List of texts to encode
            is_query: Whether texts are queries (vs documents)
            normalize: Whether to L2 normalize embeddings
            
        Returns:
            List of embedding vectors
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
    
    def encode_single(self, text: str, is_query: bool = False) -> List[float]:
        """Encode single text to embedding vector"""
        result = self.encode_batch([text], is_query=is_query)
        return result[0]
    
    def encode_queries(self, queries: List[str]) -> List[List[float]]:
        """Convenience method for encoding queries"""
        return self.encode_batch(queries, is_query=True)
    
    def encode_documents(self, documents: List[str]) -> List[List[float]]:
        """Convenience method for encoding documents"""
        return self.encode_batch(documents, is_query=False)
    
    def similarity(self, embeddings1: torch.Tensor, embeddings2: torch.Tensor) -> torch.Tensor:
        """Compute cosine similarity between embeddings"""
        return torch.mm(embeddings1, embeddings2.transpose(0, 1))


# Global embedding provider instance
_global_embedder: Optional[EmbeddingProvider] = None


def get_embedder(config: Optional[EmbeddingConfig] = None) -> EmbeddingProvider:
    """
    Get or create global embedding provider instance
    
    Args:
        config: Optional configuration, uses default if None
        
    Returns:
        Embedding provider instance
    """
    global _global_embedder
    
    if _global_embedder is None:
        if config is None:
            config = EmbeddingConfig()
        
        if config.provider == "api":
            from .providers import SiliconFlowProvider
            _global_embedder = SiliconFlowProvider(config)
        else:
            from .providers import LocalQwen3Provider
            _global_embedder = LocalQwen3Provider(config)
    
    return _global_embedder


def create_embeddings_batch(texts: List[str], is_query: bool = False) -> List[List[float]]:
    """
    Convenience function for batch embedding generation
    
    Args:
        texts: List of texts to encode
        is_query: Whether texts are queries
        
    Returns:
        List of embedding vectors
    """
    embedder = get_embedder()
    return embedder.encode_batch(texts, is_query=is_query)


def reset_embedder() -> None:
    """Reset global embedder instance (useful for testing)"""
    global _global_embedder
    _global_embedder = None
