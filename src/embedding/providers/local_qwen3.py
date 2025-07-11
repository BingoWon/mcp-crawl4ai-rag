"""
Local Qwen3 Embedding Provider
本地Qwen3嵌入提供者

High-performance local Qwen3-Embedding-4B implementation.
高性能本地Qwen3-Embedding-4B实现。
"""

import torch
import torch.nn.functional as F
from typing import List, Union
from transformers import AutoTokenizer, AutoModel

from ..core import EmbeddingProvider
from ..config import EmbeddingConfig


class LocalQwen3Provider(EmbeddingProvider):
    """High-performance local Qwen3-Embedding-4B provider"""
    
    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self.model = None
        self.tokenizer = None
        self._load_model()
        print(f"✅ Qwen3-Embedding-4B loaded on {config.device}")
    
    def _load_model(self) -> None:
        """Load Qwen3-Embedding model with optimal settings"""
        print(f"🚀 Loading {self.config.model_name} on {self.config.device}...")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name,
            padding_side='right',
            trust_remote_code=True
        )
        
        self.model = AutoModel.from_pretrained(
            self.config.model_name,
            torch_dtype=self.config.torch_dtype,
            trust_remote_code=True
        ).eval().to(self.config.torch_device)
    
    @staticmethod
    def _last_token_pool(last_hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """Extract embeddings using last token pooling"""
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]
    
    @staticmethod
    def _format_query(query: str, instruction: str = "Given a web search query, retrieve relevant passages that answer the query") -> str:
        """Format query with instruction (official Qwen3 format)"""
        return f'Instruct: {instruction}\nQuery: {query}'
    
    @torch.no_grad()
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
            return torch.empty(0, self.embedding_dim, device=self.config.torch_device)
        
        # Format queries with instruction, documents without
        if is_query:
            formatted_texts = [self._format_query(text) for text in texts]
        else:
            formatted_texts = texts
        
        # Tokenize
        batch_dict = self.tokenizer(
            formatted_texts,
            padding=True,
            truncation=True,
            max_length=self.config.max_length,
            return_tensors="pt"
        )
        batch_dict = {k: v.to(self.config.torch_device) for k, v in batch_dict.items()}
        
        # Get embeddings
        outputs = self.model(**batch_dict)
        embeddings = self._last_token_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
        
        # Normalize if requested
        if normalize:
            embeddings = F.normalize(embeddings, p=2, dim=1)
        
        return embeddings
    
    def encode_batch(
        self,
        texts: List[str],
        is_query: bool = False,
        normalize: bool = True
    ) -> List[List[float]]:
        """Encode batch of texts to list of embeddings"""
        embeddings = self.encode(texts, is_query=is_query, normalize=normalize)
        return embeddings.cpu().tolist()
    
    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension"""
        return self.config.embedding_dim
    
    @property
    def model_name(self) -> str:
        """Get model name"""
        return self.config.model_name
