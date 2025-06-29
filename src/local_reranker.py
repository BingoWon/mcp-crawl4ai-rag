#!/usr/bin/env python3
"""
Modern Qwen3 Embedding & Reranking implementation.
Complete local solution without LM Studio dependency.
"""

import torch
import torch.nn.functional as F
from typing import List, Tuple
from transformers import AutoTokenizer, AutoModelForCausalLM


class Qwen3Reranker:
    """
    High-performance Qwen3-Reranker-4B implementation with exact HuggingFace compatibility.
    Optimized for balance between performance and resource usage.
    """

    def __init__(self):
        # 写死所有参数，优化为 4B 模型
        self.model_path = "Qwen/Qwen3-Reranker-4B"
        self.device = self._auto_device()
        self.dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        self.max_length = 8192

        self._load_model()
        self._setup_tokens()

    def _auto_device(self) -> torch.device:
        """Auto-detect optimal device."""
        if torch.cuda.is_available():
            return torch.device("cuda")
        elif torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    def _load_model(self) -> None:
        """Load tokenizer and model with optimal settings."""
        print(f"🚀 Loading Qwen3-Reranker-4B on {self.device}...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            padding_side='left',
            trust_remote_code=True
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=self.dtype,
            low_cpu_mem_usage=True,
            trust_remote_code=True
        ).eval().to(self.device)

        print(f"✅ Qwen3-Reranker-4B loaded successfully on {self.device}")

    def _setup_tokens(self) -> None:
        """Setup token IDs and prompt templates."""
        self.token_false_id = self.tokenizer.convert_tokens_to_ids("no")
        self.token_true_id = self.tokenizer.convert_tokens_to_ids("yes")

        # Official HuggingFace prompt format
        system_prompt = "Judge whether the Document meets the requirements based on the Query and the Instruct provided. Note that the answer can only be \"yes\" or \"no\"."
        prefix = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n"
        suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

        self.prefix_tokens = self.tokenizer.encode(prefix, add_special_tokens=False)
        self.suffix_tokens = self.tokenizer.encode(suffix, add_special_tokens=False)

        print(f"📋 Token setup: yes={self.token_true_id}, no={self.token_false_id}")
    
    @staticmethod
    def _format_input(instruction: str, query: str, document: str) -> str:
        """Format input according to official Qwen3-Reranker specification."""
        return f"<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {document}"

    def _prepare_inputs(self, formatted_texts: List[str]) -> dict:
        """Tokenize and prepare inputs for model inference."""
        # Tokenize with truncation
        inputs = self.tokenizer(
            formatted_texts,
            padding=False,
            truncation='longest_first',
            return_attention_mask=False,
            max_length=self.max_length - len(self.prefix_tokens) - len(self.suffix_tokens)
        )

        # Add prefix and suffix tokens
        for i, input_ids in enumerate(inputs['input_ids']):
            inputs['input_ids'][i] = self.prefix_tokens + input_ids + self.suffix_tokens

        # Pad and convert to tensors
        inputs = self.tokenizer.pad(
            inputs,
            padding=True,
            return_tensors="pt",
            max_length=self.max_length
        )

        return {k: v.to(self.device) for k, v in inputs.items()}

    @torch.no_grad()
    def _compute_scores(self, inputs: dict) -> List[float]:
        """Compute relevance scores using official HuggingFace method."""
        outputs = self.model(**inputs)
        logits = outputs.logits[:, -1, :]  # Last token logits

        # Extract yes/no token probabilities
        yes_logits = logits[:, self.token_true_id]
        no_logits = logits[:, self.token_false_id]

        # Apply log_softmax and convert to probabilities
        stacked_logits = torch.stack([no_logits, yes_logits], dim=1)
        log_probs = torch.nn.functional.log_softmax(stacked_logits, dim=1)
        scores = log_probs[:, 1].exp()  # Probability of "yes"

        return scores.cpu().tolist()

    def predict(
        self,
        pairs: List[Tuple[str, str]],
        instruction: str = "Given a web search query, retrieve relevant passages that answer the query"
    ) -> List[float]:
        """
        Predict relevance scores for query-document pairs.

        Args:
            pairs: List of (query, document) tuples
            instruction: Task instruction for the reranker

        Returns:
            List of relevance scores (0.0 to 1.0)
        """
        if not pairs:
            return []

        # Format inputs
        formatted_texts = [
            self._format_input(instruction, query, doc)
            for query, doc in pairs
        ]

        # Prepare and run inference
        inputs = self._prepare_inputs(formatted_texts)
        scores = self._compute_scores(inputs)

        return scores


# Qwen3Embedder removed - use qwen3_embeddings.py instead

    @staticmethod
    def _last_token_pool(last_hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """Extract embeddings using last token pooling (official method)."""
        left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
        if left_padding:
            return last_hidden_states[:, -1]
        else:
            sequence_lengths = attention_mask.sum(dim=1) - 1
            batch_size = last_hidden_states.shape[0]
            return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]

    @staticmethod
    def _get_detailed_instruct(task_description: str, query: str) -> str:
        """Format query with instruction (official format)."""
        return f'Instruct: {task_description}\nQuery: {query}'

    @torch.no_grad()
    def encode(
        self,
        texts: List[str],
        instruction: str = "Given a web search query, retrieve relevant passages that answer the query",
        is_query: bool = False
    ) -> torch.Tensor:
        """
        Encode texts to embeddings using Qwen3-Embedding-4B.

        Args:
            texts: List of texts to encode
            instruction: Task instruction for queries
            is_query: Whether texts are queries (need instruction) or documents

        Returns:
            Normalized embeddings tensor
        """
        if not texts:
            return torch.empty(0, 2560, device=self.device)

        # Format queries with instruction, documents without
        if is_query:
            formatted_texts = [self._get_detailed_instruct(instruction, text) for text in texts]
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

        # Normalize (official recommendation)
        embeddings = F.normalize(embeddings, p=2, dim=1)

        return embeddings

    def similarity(self, query_embeddings: torch.Tensor, doc_embeddings: torch.Tensor) -> torch.Tensor:
        """Compute cosine similarity between queries and documents."""
        return query_embeddings @ doc_embeddings.T


# EmbeddingReranker removed - only using Qwen3-Reranker-4B


def create_reranker() -> 'Qwen3Reranker':
    """
    Create Qwen3-Reranker-4B instance.
    All parameters are hardcoded for simplicity.
    """
    try:
        return Qwen3Reranker()
    except Exception as e:
        print(f"❌ Qwen3-Reranker-4B unavailable: {e}")
        raise RuntimeError("Qwen3-Reranker-4B not available")


def main():
    """Test the Qwen3-Reranker implementation."""
    print("🚀 Testing Qwen3-Reranker-4B...")

    try:
        reranker = Qwen3Reranker()

        test_pairs = [
            ("What is machine learning?", "Machine learning is a subset of artificial intelligence."),
            ("What is machine learning?", "Python is a programming language."),
            ("What is machine learning?", "Deep learning uses neural networks.")
        ]

        scores = reranker.predict(test_pairs)

        print("\n📊 Results:")
        for i, ((_, doc), score) in enumerate(zip(test_pairs, scores)):
            print(f"{i+1}. Score: {score:.4f} | {doc[:60]}...")

        # Verify ranking quality
        best_score = max(scores)
        best_idx = scores.index(best_score)
        best_doc = test_pairs[best_idx][1]

        if "machine learning" in best_doc.lower():
            print(f"\n✅ Correct ranking! Best match: {best_doc}")
        else:
            print(f"\n⚠️  Unexpected ranking. Best match: {best_doc}")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
