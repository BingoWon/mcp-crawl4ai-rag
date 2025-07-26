"""
Embedding Configuration
嵌入配置

Configuration management from environment variables.
从环境变量读取配置管理。
"""

import os
from dataclasses import dataclass
from typing import Literal
import torch


@dataclass
class EmbeddingConfig:
    """Embedding configuration from environment variables"""

    # Provider selection
    provider: Literal["local", "api"] = os.getenv("EMBEDDING_MODE", "local")

    # Model configuration
    model_name: str = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-4B")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "2560"))
    max_length: int = int(os.getenv("EMBEDDING_MAX_LENGTH", "8192"))

    # Apple Silicon MPS configuration (hardcoded)
    device: str = "mps"
    dtype: str = "float32"

    # Performance configuration
    normalize_embeddings: bool = True

    # API configuration (for SiliconFlow)
    api_base_url: str = os.getenv("SILICONFLOW_API_BASE_URL", "https://api.siliconflow.cn/v1/embeddings")
    api_timeout: int = int(os.getenv("SILICONFLOW_TIMEOUT", "30"))
    
    def __post_init__(self):
        """Apple Silicon optimized configuration"""
        pass
    
    @classmethod
    def for_local(cls) -> "EmbeddingConfig":
        """Create Apple Silicon optimized local configuration"""
        return cls(provider="local")

    @classmethod
    def for_api(cls) -> "EmbeddingConfig":
        """Create API configuration"""
        return cls(provider="api")
    
    @property
    def torch_device(self) -> torch.device:
        """Get torch device object"""
        return torch.device(self.device)
    
    @property
    def torch_dtype(self) -> torch.dtype:
        """Get Apple Silicon optimized torch dtype"""
        return torch.float32
