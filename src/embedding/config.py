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

    # Device configuration (hardcoded)
    device: str = "auto"
    dtype: str = "auto"

    # Performance configuration
    normalize_embeddings: bool = True

    # API configuration (for SiliconFlow)
    api_base_url: str = "https://api.siliconflow.cn/v1/embeddings"
    api_timeout: int = int(os.getenv("SILICONFLOW_TIMEOUT", "30"))
    
    def __post_init__(self):
        """Validate and optimize configuration"""
        if self.device == "auto":
            self.device = self._auto_detect_device()
        
        if self.dtype == "auto":
            self.dtype = self._auto_detect_dtype()
    
    def _auto_detect_device(self) -> str:
        """Auto-detect optimal device"""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    
    def _auto_detect_dtype(self) -> str:
        """Auto-detect optimal dtype based on device"""
        if self.device == "cuda":
            return "float16"
        return "float32"
    
    @classmethod
    def for_local(cls) -> "EmbeddingConfig":
        """Create configuration optimized for local inference"""
        return cls(provider="local")
    
    @classmethod
    def for_api(cls) -> "EmbeddingConfig":
        """Create configuration optimized for API usage"""
        return cls(provider="api")
    
    @property
    def torch_device(self) -> torch.device:
        """Get torch device object"""
        return torch.device(self.device)
    
    @property
    def torch_dtype(self) -> torch.dtype:
        """Get torch dtype object"""
        if self.dtype == "float16":
            return torch.float16
        elif self.dtype == "float32":
            return torch.float32
        elif self.dtype == "bfloat16":
            return torch.bfloat16
        else:
            return torch.float32
