#!/usr/bin/env python3
"""
Modern Qwen3-Embedding-4B implementation.
Replaces LM Studio embedding with superior local model.
"""

import torch
import torch.nn.functional as F
from typing import List, Optional, Union
from transformers import AutoTokenizer, AutoModel


class Qwen3Embedder:
    """
    High-performance Qwen3-Embedding-4B implementation.
    State-of-the-art multilingual embedding model.
    """
    
    def __init__(self):
        """
        Initialize Qwen3-Embedding-4B with hardcoded optimal parameters.
        """
        # 写死所有参数
        self.model_path = "Qwen/Qwen3-Embedding-4B"
        self.device = self._auto_device()
        self.max_length = 8192
        self.embedding_dim = None  # Use full 2560 dimensions

        self._load_model()
        print(f"✅ Qwen3-Embedding-4B loaded on {self.device}")
    
    def _auto_device(self) -> torch.device:
        """Auto-detect optimal device."""
        if torch.cuda.is_available():
            return torch.device("cuda")
        elif torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    
    def _load_model(self) -> None:
        """Load Qwen3-Embedding model with optimal settings."""
        print(f"🚀 Loading Qwen3-Embedding-4B on {self.device}...")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            padding_side='right',  # 使用 right padding 确保与 API 一致
            trust_remote_code=True
        )
        
        dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        self.model = AutoModel.from_pretrained(
            self.model_path,
            torch_dtype=dtype,
            trust_remote_code=True
        ).eval().to(self.device)
    
    @staticmethod
    def _last_token_pool(last_hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """Extract embeddings using last token pooling (standardized method)."""
        # 使用标准化的 last token pooling，与 API 保持一致
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]
    
    @staticmethod
    def get_detailed_instruct(task_description: str, query: str) -> str:
        """Format query with instruction (official Qwen3 format)."""
        return f'Instruct: {task_description}\nQuery: {query}'
    
    @torch.no_grad()
    def encode(
        self,
        texts: Union[str, List[str]],
        instruction: str = "Given a web search query, retrieve relevant passages that answer the query",
        is_query: bool = False,
        normalize: bool = True
    ) -> torch.Tensor:
        """
        Encode texts to embeddings using Qwen3-Embedding-4B.
        
        Args:
            texts: Text(s) to encode
            instruction: Task instruction for queries
            is_query: Whether texts are queries (need instruction) or documents
            normalize: Whether to L2 normalize embeddings
            
        Returns:
            Embeddings tensor [batch_size, embedding_dim]
        """
        if isinstance(texts, str):
            texts = [texts]
        
        if not texts:
            dim = self.embedding_dim or 2560
            return torch.empty(0, dim, device=self.device)
        
        # Format queries with instruction, documents without
        if is_query:
            formatted_texts = [self.get_detailed_instruct(instruction, text) for text in texts]
        else:
            formatted_texts = texts
        
        # Tokenize
        batch_dict = self.tokenizer(
            formatted_texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt"
        )
        batch_dict = {k: v.to(self.device) for k, v in batch_dict.items()}
        
        # Get embeddings
        outputs = self.model(**batch_dict)
        embeddings = self._last_token_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
        
        # Custom dimension support (MRL - Matryoshka Representation Learning)
        if self.embedding_dim and self.embedding_dim < embeddings.size(-1):
            embeddings = embeddings[:, :self.embedding_dim]
        
        # Normalize (recommended for similarity tasks)
        if normalize:
            embeddings = F.normalize(embeddings, p=2, dim=1)
        
        return embeddings
    
    def similarity(self, embeddings1: torch.Tensor, embeddings2: torch.Tensor) -> torch.Tensor:
        """Compute cosine similarity between two sets of embeddings."""
        return embeddings1 @ embeddings2.T
    
    def encode_queries(self, queries: List[str], instruction: str = None) -> torch.Tensor:
        """Convenience method for encoding queries with instruction."""
        if instruction is None:
            instruction = "Given a web search query, retrieve relevant passages that answer the query"
        return self.encode(queries, instruction=instruction, is_query=True)
    
    def encode_documents(self, documents: List[str]) -> torch.Tensor:
        """Convenience method for encoding documents without instruction."""
        return self.encode(documents, is_query=False)


def create_embedder() -> Qwen3Embedder:
    """
    Factory function to create Qwen3-Embedder instance.
    All parameters are hardcoded for simplicity.

    Returns:
        Configured Qwen3Embedder instance with optimal settings
    """
    return Qwen3Embedder()


def main():
    """Test Qwen3-Embedding implementation."""
    print("🚀 Testing Qwen3-Embedding-4B...")
    
    try:
        embedder = create_embedder()
        
        # Test data
        queries = ["What is machine learning?", "Explain quantum computing"]
        documents = [
            "Machine learning is a subset of artificial intelligence.",
            "Quantum computing uses quantum mechanics for computation.",
            "Python is a programming language."
        ]
        
        # Encode
        query_embeddings = embedder.encode_queries(queries)
        doc_embeddings = embedder.encode_documents(documents)
        
        # Compute similarities
        similarities = embedder.similarity(query_embeddings, doc_embeddings)
        
        print(f"\n📊 Results:")
        print(f"Query embeddings shape: {query_embeddings.shape}")
        print(f"Document embeddings shape: {doc_embeddings.shape}")
        print(f"Similarities shape: {similarities.shape}")
        
        print(f"\nSimilarity matrix:")
        for i, query in enumerate(queries):
            print(f"\nQuery: {query}")
            for j, doc in enumerate(documents):
                sim = similarities[i, j].item()
                print(f"  Doc {j+1}: {sim:.4f} | {doc[:40]}...")
        
        print(f"\n✅ Qwen3-Embedding-4B working perfectly!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
