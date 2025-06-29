#!/usr/bin/env python3
"""Qwen3-Embedding-4B Provider: local transformers and Silicon Flow API modes."""

import os
import requests
from typing import List, Union
import torch


class LocalQwen3Embedder:
    def __init__(self):
        from qwen3_embeddings import Qwen3Embedder
        self._embedder = Qwen3Embedder()

    def encode(self, texts: Union[str, List[str]], is_query: bool = False) -> torch.Tensor:
        return self._embedder.encode(texts, is_query=is_query)

    def encode_single(self, text: str, is_query: bool = False) -> List[float]:
        return self.encode([text], is_query=is_query)[0].cpu().tolist()

    @property
    def embedding_dim(self) -> int:
        return 2560


class SiliconFlowEmbedder:
    def __init__(self):
        self.api_key = os.getenv("SILICONFLOW_API_KEY", "")
        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY required")

    def encode(self, texts: Union[str, List[str]], is_query: bool = False) -> torch.Tensor:
        if isinstance(texts, str):
            texts = [texts]
        embeddings = [self.encode_single(text) for text in texts]
        return torch.tensor(embeddings, dtype=torch.float32)

    def encode_single(self, text: str, is_query: bool = False) -> List[float]:
        response = requests.post(
            "https://api.siliconflow.cn/v1/embeddings",
            json={"model": "Qwen/Qwen3-Embedding-4B", "input": text},
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()["data"][0]["embedding"]
        raise ValueError(f"API failed: {response.status_code}")

    @property
    def embedding_dim(self) -> int:
        return 2560


def create_embedder():
    mode = os.getenv("EMBEDDING_MODE", "local")
    if mode == "api":
        return SiliconFlowEmbedder()
    return LocalQwen3Embedder()