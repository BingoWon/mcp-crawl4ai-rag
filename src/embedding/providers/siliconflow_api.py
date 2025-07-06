"""
SiliconFlow API Embedding Provider
SiliconFlow API嵌入提供者

High-performance API-based embedding provider using SiliconFlow.
基于SiliconFlow API的高性能嵌入提供者。
"""

import os
import requests
import torch
from typing import List, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        print(f"✅ SiliconFlow API provider initialized with {self.config.model_name}")
    
    def _encode_single_api(self, text: str) -> List[float]:
        """Encode single text via API"""
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
            return response.json()["data"][0]["embedding"]
        except Exception as e:
            raise RuntimeError(f"SiliconFlow API error: {e}")
    
    def encode(
        self, 
        texts: Union[str, List[str]], 
        is_query: bool = False,
        normalize: bool = True
    ) -> torch.Tensor:
        """Encode texts to embeddings tensor"""
        if isinstance(texts, str):
            texts = [texts]
        
        if not texts:
            return torch.empty(0, self.embedding_dim)
        
        # API doesn't distinguish between queries and documents
        embeddings = []
        
        # Use ThreadPoolExecutor for parallel API calls
        with ThreadPoolExecutor(max_workers=min(len(texts), 10)) as executor:
            future_to_text = {executor.submit(self._encode_single_api, text): text for text in texts}
            
            for future in as_completed(future_to_text):
                try:
                    embedding = future.result()
                    embeddings.append(embedding)
                except Exception as e:
                    text = future_to_text[future]
                    raise RuntimeError(f"Failed to encode text '{text[:50]}...': {e}")
        
        # Convert to tensor
        embeddings_tensor = torch.tensor(embeddings, dtype=torch.float32)
        
        # Normalize if requested
        if normalize:
            embeddings_tensor = torch.nn.functional.normalize(embeddings_tensor, p=2, dim=1)
        
        return embeddings_tensor
    
    def encode_batch(
        self,
        texts: List[str],
        is_query: bool = False,
        normalize: bool = True
    ) -> List[List[float]]:
        """Encode batch of texts to list of embeddings"""
        embeddings = self.encode(texts, is_query=is_query, normalize=normalize)
        return embeddings.tolist()
    
    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension"""
        return self.config.embedding_dim
    
    @property
    def model_name(self) -> str:
        """Get model name"""
        return self.config.model_name
