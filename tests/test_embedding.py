import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from embedding import EmbeddingConfig, LocalQwen3Provider, SiliconFlowProvider, reset_embedder


def test_local_provider():
    """Test local Qwen3 provider"""
    reset_embedder()
    config = EmbeddingConfig.for_local()
    provider = LocalQwen3Provider(config)

    # Test single encoding
    embedding = provider.encode_single("Hello world")
    assert len(embedding) == 2560

    # Test multiple single encodings
    embedding1 = provider.encode_single("Hello")
    embedding2 = provider.encode_single("World")
    assert len(embedding1) == 2560
    assert len(embedding2) == 2560

    print("✅ Local provider tests passed")
    return provider


def test_api_provider():
    """Test SiliconFlow API provider"""
    if not os.getenv("SILICONFLOW_API_KEY"):
        print("⚠️ Skipping API tests - no API key")
        return None

    reset_embedder()
    config = EmbeddingConfig.for_api()
    provider = SiliconFlowProvider(config)

    # Test single encoding
    embedding = provider.encode_single("Hello world")
    assert len(embedding) == 2560

    # Test multiple single encodings
    embedding1 = provider.encode_single("Hello")
    embedding2 = provider.encode_single("World")
    assert len(embedding1) == 2560
    assert len(embedding2) == 2560

    print("✅ API provider tests passed")
    return provider


def test_consistency():
    """Test consistency between providers"""
    local_provider = test_local_provider()
    api_provider = test_api_provider()

    if api_provider is None:
        print("⚠️ Skipping consistency test - no API provider")
        return

    # Test same text with both providers
    text = "Test consistency"
    local_embedding = local_provider.encode_single(text)
    api_embedding = api_provider.encode_single(text)

    # Both should have same dimension
    assert len(local_embedding) == len(api_embedding) == 2560

    # Calculate similarity (should be high for same model)
    import torch
    local_tensor = torch.tensor([local_embedding])
    api_tensor = torch.tensor([api_embedding])
    similarity = torch.cosine_similarity(local_tensor, api_tensor).item()

    print(f"✅ Consistency test passed - similarity: {similarity:.4f}")
    assert similarity > 0.9  # Should be very similar


if __name__ == "__main__":
    test_local_provider()
    test_api_provider()
    test_consistency()
    print("✅ All embedding tests passed")
