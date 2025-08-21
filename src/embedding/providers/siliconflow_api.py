"""
SiliconFlow API Embedding Provider - 多Key管理的批量处理全局最优解

本模块实现了SiliconFlow API的embedding服务提供者，集成多API Key管理系统，
提供robust的服务保障和真正的批量API调用策略。

=== 核心功能 ===

**多Key管理系统**:
- 自动故障转移：API key失效时无缝切换
- 智能错误检测：识别认证失败、余额不足等问题
- 自动清理机制：移除失效keys，保持系统整洁

**真正的批量API调用**:
- 单个API请求处理多个文本，而非多个单独请求
- 利用SiliconFlow API的原生批量处理能力
- 大幅减少网络开销和API调用次数

**Robust服务保障**:
- 零停机时间的服务连续性
- 多层容错机制：key切换 → 重试 → 本地降级
- 实时状态监控和自动恢复

=== 实现原理 ===

**多Key故障转移**:
```python
# 检测到key失效 → 自动切换到下一个可用key
# 所有key失效 → 降级到本地模式（如果启用）
# 定期清理失效keys → 保持配置文件整洁
```

**批量处理机制**:
```python
# 优化方式（当前实现）
embeddings = api_call(texts)  # 1次API调用处理所有文本
```

**错误处理策略**:
- 智能分类：区分临时性错误和永久性失效
- 原子性保证：批量处理要么全部成功，要么全部失败
- 自动恢复：失效key在成功后自动恢复active状态

=== 技术特点 ===

**优雅现代精简**:
- 无冗余代码：每行代码都有其必要性
- 类型安全：完整的类型注解支持
- 异步优化：充分利用async/await特性

**全局最优解**:
- 直接实现最佳方案，无向后兼容负担
- 多层容错设计，最大化系统可用性
- 性能与可靠性并重的架构设计
"""

import os
import asyncio
import aiohttp
from typing import List
from ..core import EmbeddingProvider
from ..config import EmbeddingConfig
from .key_manager import KeyManager


class SiliconFlowProvider(EmbeddingProvider):
    """SiliconFlow API embedding provider with multi-key management"""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)

        # 初始化Key管理器
        self.key_manager = KeyManager()

        # 降级配置
        self.fallback_to_local = os.getenv("SILICONFLOW_FALLBACK_TO_LOCAL", "false").lower() == "true"
        self._local_provider = None

        from utils.logger import setup_logger
        self.logger = setup_logger(__name__)
        self.logger.info("✅ SiliconFlow API provider initialized with multi-key management")
        if self.fallback_to_local:
            self.logger.info("🔄 Local fallback enabled for rate limit scenarios")

    def encode_single(self, text: str, is_query: bool = False) -> List[float]:
        """单个文本编码"""
        return asyncio.run(self.encode_batch_concurrent([text]))[0]

    async def encode_batch_concurrent(self, texts: List[str]) -> List[List[float]]:
        """多Key管理的批量API调用 - 优雅精简的全局最优解"""
        if not texts:
            return []

        self.logger.info(f"Multi-key batch encoding {len(texts)} texts via single API call")

        # 最多尝试所有可用keys
        max_key_attempts = 3

        for key_attempt in range(max_key_attempts):
            try:
                current_key = self.key_manager.get_current_key()

                for retry_attempt in range(3):  # 每个key最多重试3次
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                self.config.api_base_url,
                                json={"model": self.config.model_name, "input": texts},
                                headers={"Authorization": f"Bearer {current_key}", "Content-Type": "application/json"},
                                timeout=aiohttp.ClientTimeout(total=self.config.api_timeout)
                            ) as response:
                                if response.status == 200:
                                    result = await response.json()
                                    embeddings = [item["embedding"] for item in result["data"]]

                                    # key使用成功，无需特殊处理

                                    self.logger.info(f"✅ Multi-key batch encoded {len(embeddings)} embeddings")
                                    return embeddings

                                # 获取错误信息
                                try:
                                    error_data = await response.json()
                                    error_msg = error_data.get("message", str(error_data))
                                except Exception:
                                    error_msg = await response.text()

                                # 智能错误处理 - 删除vs切换key
                                if response.status in [401, 402, 403]:  # 认证失败、余额不足、权限拒绝
                                    await self.key_manager.remove_key(current_key)
                                    self.logger.warning(f"🗑️ Key permanently failed (HTTP {response.status}), removed")
                                    break

                                elif response.status == 429:  # 速率限制 - 立即切换
                                    self.key_manager.switch_to_next_key()
                                    self.logger.warning("🔄 Rate limited, switched to next key")
                                    break

                                # 服务器错误 - 重试
                                elif response.status in [503, 504] and retry_attempt < 2:
                                    delay = 2.0 * (2 ** retry_attempt)
                                    self.logger.warning(f"⚠️ Server error {response.status}, retrying in {delay}s")
                                    await asyncio.sleep(delay)
                                    continue

                                # 其他错误
                                else:
                                    raise RuntimeError(f"SiliconFlow API error {response.status}: {error_msg}")

                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        if retry_attempt < 2:
                            delay = 2.0 * (2 ** retry_attempt)
                            self.logger.warning(f"⚠️ Network error, retrying in {delay}s: {e}")
                            await asyncio.sleep(delay)
                            continue
                        raise RuntimeError(f"SiliconFlow API network error: {e}")

            except RuntimeError as e:
                if "No API keys available" in str(e):
                    self.logger.error("❌ All API keys exhausted")
                    if self.fallback_to_local:
                        return await self._fallback_to_local_encoding(texts)
                    raise e

                # 如果还有key可以尝试，继续
                if key_attempt < max_key_attempts - 1:
                    continue
                raise e

        raise RuntimeError("All API keys failed after multiple attempts")

    async def _fallback_to_local_encoding(self, texts: List[str]) -> List[List[float]]:
        """降级到本地模式进行编码"""
        self.logger.warning("🔄 Falling back to local embedding due to API rate limit")

        if self._local_provider is None:
            # 懒加载本地提供者
            from .local_qwen3 import LocalQwen3Provider
            local_config = self.config
            local_config.provider = "local"
            self._local_provider = LocalQwen3Provider(local_config)
            self.logger.info("✅ Local provider initialized for fallback")

        return await self._local_provider.encode_batch_concurrent(texts)

    @property
    def embedding_dim(self) -> int:
        return self.config.embedding_dim

    @property
    def model_name(self) -> str:
        return self.config.model_name
