"""
Local Qwen3 Embedding Provider
本地Qwen3嵌入提供者

High-performance local Qwen3-Embedding-4B implementation.
高性能本地Qwen3-Embedding-4B实现。
"""

import torch
import torch.nn.functional as F
from typing import List
from transformers import AutoTokenizer, AutoModel

from ..core import EmbeddingProvider
from ..config import EmbeddingConfig
from utils.logger import setup_logger

logger = setup_logger(__name__)


class LocalQwen3Provider(EmbeddingProvider):
    """High-performance local Qwen3-Embedding-4B provider"""
    
    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self.model = None
        self.tokenizer = None
        self.total_tokens = 0
        self._load_model()
        logger.info(f"✅ {self.config.model_name} loaded on Apple Silicon MPS")
    
    def _load_model(self) -> None:
        """Load Qwen3-Embedding model with optimal settings"""
        logger.info(f"🚀 Loading {self.config.model_name} on Apple Silicon MPS...")
        
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

    def _update_token_stats(self, token_count: int) -> None:
        """Update token statistics and log progress"""
        self.total_tokens += token_count
        tokens_m = self.total_tokens / 1_000_000
        logger.info(f"📊 Embedding: {tokens_m:.3f}M tokens, ¥{tokens_m * 0.14:.4f}")
    
    @torch.no_grad()
    def encode_single(
        self,
        text: str,
        is_query: bool = False
    ) -> List[float]:
        """Encode single text to embedding vector with L2 normalization"""
        # Format query with instruction if needed
        formatted_text = self._format_query(text) if is_query else text

        # Tokenize
        batch_dict = self.tokenizer(
            [formatted_text],
            padding=True,
            truncation=True,
            max_length=self.config.max_length,
            return_tensors="pt"
        )

        # 统计token数量
        self._update_token_stats(batch_dict['input_ids'].shape[1])

        batch_dict = {k: v.to(self.config.torch_device) for k, v in batch_dict.items()}

        # Get embeddings
        outputs = self.model(**batch_dict)
        embeddings = self._last_token_pool(outputs.last_hidden_state, batch_dict['attention_mask'])

        # Clean up intermediate tensors to free MPS memory
        del batch_dict, outputs

        # Always normalize embeddings for consistency with API
        embeddings = F.normalize(embeddings, p=2, dim=1)

        # Convert to list and return single embedding
        result = embeddings.cpu().tolist()[0]
        del embeddings

        return result

    
    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension"""
        return self.config.embedding_dim
    
    @property
    def model_name(self) -> str:
        """Get model name"""
        return self.config.model_name
