#!/usr/bin/env python3
"""
测试API keys加载和SiliconFlow API调用
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.embedding import get_embedder
from src.embedding.providers import SiliconFlowProvider
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def test_api_keys():
    """测试API keys加载和调用"""
    logger.info("🧪 开始测试API keys...")
    
    # 1. 测试embedder获取
    embedder = get_embedder()
    logger.info(f"📊 Embedder类型: {type(embedder)}")
    
    if not isinstance(embedder, SiliconFlowProvider):
        logger.error("❌ Embedder不是SiliconFlowProvider类型")
        return
    
    # 2. 测试key管理器
    key_manager = embedder.key_manager
    logger.info(f"📊 Key管理器: {type(key_manager)}")
    
    # 3. 测试key加载
    try:
        current_key = key_manager.get_current_key()
        logger.info(f"✅ 当前key: {current_key[:8]}...{current_key[-8:]}")
    except Exception as e:
        logger.error(f"❌ 获取当前key失败: {e}")

        # 检查KeyManager的文件路径
        logger.info(f"📁 KeyManager文件路径: {key_manager.keys_file}")
        logger.info(f"📁 文件是否存在: {key_manager.keys_file.exists()}")

        # 直接测试_read_keys方法
        keys = key_manager._read_keys()
        logger.info(f"📊 _read_keys返回: {len(keys)} 个keys")
        if keys:
            logger.info(f"📊 第一个key: {keys[0][:8]}...{keys[0][-8:]}")

        # 检查文件内容
        keys_file = Path("../config/api_keys.txt")
        if keys_file.exists():
            with open(keys_file, 'r') as f:
                content = f.read()
                logger.info(f"📁 Keys文件内容长度: {len(content)}")
                logger.info(f"📁 Keys文件前100字符: {content[:100]}")
        else:
            logger.error(f"❌ Keys文件不存在: {keys_file}")
        return
    
    # 4. 测试简单API调用
    test_texts = ["Hello world", "Test embedding"]
    
    try:
        logger.info("🚀 开始测试API调用...")
        embeddings = await embedder.encode_batch_concurrent(test_texts)
        logger.info(f"✅ API调用成功，获得 {len(embeddings)} 个embeddings")
        logger.info(f"📊 第一个embedding维度: {len(embeddings[0])}")
        
    except Exception as e:
        logger.error(f"❌ API调用失败: {e}")


async def main():
    """主函数"""
    await test_api_keys()


if __name__ == "__main__":
    asyncio.run(main())
