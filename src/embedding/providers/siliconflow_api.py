"""
SiliconFlow API Embedding Provider
SiliconFlow API嵌入提供者

High-performance API-based embedding provider using SiliconFlow.
基于SiliconFlow API的高性能嵌入提供者。
"""

import os
import requests
from typing import List

from ..core import EmbeddingProvider
from ..config import EmbeddingConfig


class SiliconFlowProvider(EmbeddingProvider):
    """SiliconFlow API embedding provider"""
    
    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self.api_key = os.getenv("SILICONFLOW_API_KEY", "")
        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY environment variable is required for API mode")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        from utils.logger import setup_logger
        logger = setup_logger(__name__)
        logger.info(f"✅ SiliconFlow API provider initialized with {self.config.model_name}")
    
    def encode_single(
        self,
        text: str,
        is_query: bool = False
    ) -> List[float]:
        """Encode single text to embedding vector via API (already normalized)"""
        try:
            response = self.session.post(
                self.config.api_base_url,
                json={
                    "model": self.config.model_name,
                    "input": text
                },
                timeout=self.config.api_timeout
            )
            response.raise_for_status()
            embedding = response.json()["data"][0]["embedding"]

            # API already returns normalized embeddings, no need to normalize again
            return embedding
        except Exception as e:
            raise RuntimeError(f"SiliconFlow API error: {e}")
    
    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension"""
        return self.config.embedding_dim
    
    @property
    def model_name(self) -> str:
        """Get model name"""
        return self.config.model_name
