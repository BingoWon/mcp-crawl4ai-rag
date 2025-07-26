"""SiliconFlow API嵌入提供者 - 精简版"""

import os
import asyncio
import aiohttp
from typing import List
from ..core import EmbeddingProvider
from ..config import EmbeddingConfig


class SiliconFlowProvider(EmbeddingProvider):
    """SiliconFlow API embedding provider"""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self.api_key = os.getenv("SILICONFLOW_API_KEY", "")
        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY environment variable is required")

        from utils.logger import setup_logger
        self.logger = setup_logger(__name__)
        self.logger.info(f"✅ SiliconFlow API provider initialized with {config.model_name}")

    def encode_single(self, text: str, is_query: bool = False) -> List[float]:
        """单个文本编码"""
        return asyncio.run(self.encode_batch_concurrent([text]))[0]

    async def encode_batch_concurrent(self, texts: List[str]) -> List[List[float]]:
        """批量并发编码"""
        if not texts:
            return []

        self.logger.info(f"Batch encoding {len(texts)} texts")

        async def encode_text(session: aiohttp.ClientSession, text: str) -> List[float]:
            async with session.post(
                self.config.api_base_url,
                json={"model": self.config.model_name, "input": text},
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=self.config.api_timeout)
            ) as response:
                response.raise_for_status()
                return (await response.json())["data"][0]["embedding"]

        try:
            async with aiohttp.ClientSession() as session:
                embeddings = await asyncio.gather(*[encode_text(session, text) for text in texts])
            self.logger.info(f"✅ Batch encoded {len(embeddings)} embeddings")
            return embeddings
        except Exception as e:
            raise RuntimeError(f"SiliconFlow API error: {e}")

    @property
    def embedding_dim(self) -> int:
        return self.config.embedding_dim

    @property
    def model_name(self) -> str:
        return self.config.model_name
