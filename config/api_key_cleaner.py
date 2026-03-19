#!/usr/bin/env python3
"""
SiliconFlow API Key余额检查和清理工具

功能：
1. 读取config/api_keys.txt中的所有API keys
2. 通过SiliconFlow官方API获取每个key的余额信息
3. 删除余额为负数或无效的keys
4. 更新api_keys.txt文件，保留有效keys

API接口：
- 端点: GET /user/info
- 认证: Authorization: Bearer <api_key>
- 响应: data.balance (余额信息)
"""

import asyncio
import aiohttp
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# SiliconFlow API配置
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn"
USER_INFO_ENDPOINT = "/v1/user/info"  # 添加v1版本前缀
REQUEST_TIMEOUT = 10  # 秒


class APIKeyManager:
    """API Key管理器"""

    def __init__(self, keys_file: str = "config/api_keys.txt", max_concurrent: int = 100):
        """
        初始化 API Key 管理器

        Args:
            keys_file: API keys 文件路径
            max_concurrent: 最大并发数（默认100）
                - 设计原理：使用信号量控制并发，而非完全无限制
                - 技术权衡：100 是经过评估的最优值
                    * 太低（<50）：性能提升有限
                    * 太高（>200）：可能触发 API 限流（429错误）、耗尽系统资源
                    * 100：在性能和稳定性之间的最佳平衡点
                - 性能提升：相比串行延迟方案，10000个keys从83分钟降到1.7分钟（50倍提升）
        """
        self.keys_file = Path(keys_file)
        self.valid_keys = []
        self.invalid_keys = []
        self.max_concurrent = max_concurrent
        
    def load_keys(self) -> List[str]:
        """加载API keys从文件"""
        if not self.keys_file.exists():
            logger.error(f"❌ API keys文件不存在: {self.keys_file}")
            return []
        
        try:
            with open(self.keys_file, 'r', encoding='utf-8') as f:
                keys = [line.strip() for line in f if line.strip()]
            
            logger.info(f"📁 加载了 {len(keys)} 个API keys")
            return keys
            
        except Exception as e:
            logger.error(f"❌ 读取API keys文件失败: {e}")
            return []
    
    async def check_key_balance(self, session: aiohttp.ClientSession, 
                               api_key: str) -> Tuple[str, Optional[float], str]:
        """
        检查单个API key的余额
        
        Args:
            session: aiohttp会话
            api_key: API密钥
            
        Returns:
            (api_key, balance, status) - balance为None表示检查失败
        """
        url = f"{SILICONFLOW_BASE_URL}{USER_INFO_ENDPOINT}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with session.get(
                url, 
                headers=headers, 
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("status") and data.get("code") == 20000:
                        balance_str = data.get("data", {}).get("balance", "0")
                        try:
                            balance = float(balance_str)
                            status = "valid" if balance > 0 else "zero_balance"
                            return api_key, balance, status
                        except (ValueError, TypeError):
                            logger.warning(f"⚠️ 无法解析余额: {balance_str}")
                            return api_key, None, "parse_error"
                    else:
                        logger.warning(f"⚠️ API响应异常: {data}")
                        return api_key, None, "api_error"
                        
                elif response.status == 401:
                    logger.warning(f"🔑 API key无效或已过期")
                    return api_key, None, "unauthorized"
                    
                elif response.status == 429:
                    logger.warning(f"⏰ API调用频率限制")
                    return api_key, None, "rate_limited"
                    
                else:
                    error_text = await response.text()
                    logger.warning(f"⚠️ HTTP {response.status}: {error_text}")
                    return api_key, None, f"http_{response.status}"
                    
        except asyncio.TimeoutError:
            logger.warning(f"⏰ 请求超时")
            return api_key, None, "timeout"
            
        except Exception as e:
            logger.warning(f"❌ 请求异常: {e}")
            return api_key, None, "exception"
    
    async def check_all_keys(self, api_keys: List[str]) -> Dict[str, Dict]:
        """
        批量检查所有API keys - 使用信号量控制的高性能并发方案

        设计原理：
        1. 使用 asyncio.Semaphore 控制并发数，而非串行延迟
        2. 所有请求立即发起，但同时执行的数量受信号量限制
        3. 完成一个请求后，信号量自动释放，下一个请求立即开始

        性能对比（10000 keys）：
        - 旧方案（串行延迟0.5秒）：10000 * 0.5 = 5000秒 ≈ 83分钟
        - 新方案（并发100）：10000 / 100 * 1秒 ≈ 100秒 ≈ 1.7分钟
        - 性能提升：50倍

        为什么不完全无限制：
        - 系统限制：文件描述符上限（macOS ~10240）
        - 内存限制：10000并发 ≈ 1GB内存
        - API限制：SiliconFlow会触发429限流
        - 网络限制：DNS、TCP连接建立都有瓶颈

        Args:
            api_keys: API密钥列表

        Returns:
            检查结果字典
        """
        logger.info(f"🔍 开始检查 {len(api_keys)} 个API keys（并发数：{self.max_concurrent}）...")

        results = {}

        # 创建信号量控制并发数
        # 技术说明：Semaphore 是异步并发控制的最佳实践
        # - 比固定延迟更高效：请求完成即释放，无需等待固定时间
        # - 比完全无限制更稳定：避免资源耗尽和API限流
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # 创建HTTP会话
        # 连接池大小设置为并发数的1.5倍，留有余量
        connector = aiohttp.TCPConnector(limit=int(self.max_concurrent * 1.5))
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # 创建所有任务（立即创建，但执行受信号量控制）
            tasks = []
            for api_key in api_keys:
                task = self._check_with_semaphore(session, api_key, semaphore)
                tasks.append(task)

            # 并发执行所有检查
            # gather 会立即启动所有任务，但实际并发数由 semaphore 控制
            check_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for result in check_results:
                if isinstance(result, Exception):
                    logger.error(f"❌ 检查过程中出现异常: {result}")
                    continue

                api_key, balance, status = result
                # key_short = f"{api_key[:8]}...{api_key[-8:]}"
                key_short = f"{api_key}"

                results[api_key] = {
                    "balance": balance,
                    "status": status,
                    "key_short": key_short
                }

                # 记录结果
                if balance is not None:
                    if balance > 0:
                        logger.info(f"✅ {key_short}: ¥{balance:.2f} ({status})")
                        self.valid_keys.append(api_key)
                    else:
                        logger.warning(f"💸 {key_short}: ¥{balance:.2f} ({status})")
                        self.invalid_keys.append(api_key)
                else:
                    logger.error(f"❌ {key_short}: 检查失败 ({status})")
                    self.invalid_keys.append(api_key)

        return results

    async def _check_with_semaphore(self, session: aiohttp.ClientSession,
                                   api_key: str, semaphore: asyncio.Semaphore) -> Tuple[str, Optional[float], str]:
        """
        使用信号量控制的并发检查

        技术实现：
        1. async with semaphore: 获取信号量许可
        2. 如果已有 max_concurrent 个任务在执行，当前任务会等待
        3. 一旦有任务完成释放信号量，当前任务立即开始
        4. 执行完成后自动释放信号量（通过 context manager）

        这种方式比固定延迟更高效：
        - 固定延迟：必须等待固定时间，即使系统空闲
        - 信号量：系统空闲时立即执行，无需等待
        """
        async with semaphore:
            return await self.check_key_balance(session, api_key)
    
    def save_valid_keys(self) -> bool:
        """保存有效的API keys到文件"""
        if not self.valid_keys:
            logger.warning("⚠️ 没有有效的API keys可保存")
            return False
        
        try:
            # 写入有效keys
            with open(self.keys_file, 'w', encoding='utf-8') as f:
                for key in self.valid_keys:
                    f.write(f"{key}\n")
            
            logger.info(f"💾 已保存 {len(self.valid_keys)} 个有效API keys")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存API keys失败: {e}")
            return False
    
    def print_summary(self, results: Dict[str, Dict]):
        """打印检查结果摘要"""
        logger.info("=" * 60)
        logger.info("📊 API Keys检查结果摘要")
        logger.info("=" * 60)
        
        total_keys = len(results)
        valid_count = len(self.valid_keys)
        invalid_count = len(self.invalid_keys)
        
        logger.info(f"📈 总计: {total_keys} 个keys")
        logger.info(f"✅ 有效: {valid_count} 个keys ({valid_count/total_keys*100:.1f}%)")
        logger.info(f"❌ 无效: {invalid_count} 个keys ({invalid_count/total_keys*100:.1f}%)")
        
        # 统计余额
        valid_balances = [
            results[key]["balance"] for key in self.valid_keys 
            if results[key]["balance"] is not None
        ]
        
        if valid_balances:
            total_balance = sum(valid_balances)
            avg_balance = total_balance / len(valid_balances)
            logger.info(f"💰 总余额: ¥{total_balance:.2f}")
            logger.info(f"📊 平均余额: ¥{avg_balance:.2f}")
        
        # 状态分布
        status_counts = {}
        for result in results.values():
            status = result["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        logger.info("\n📋 状态分布:")
        for status, count in status_counts.items():
            logger.info(f"   {status}: {count} 个")


async def main():
    """主函数"""
    logger.info("🚀 开始API Keys余额检查和清理...")
    
    manager = APIKeyManager()
    
    # 加载API keys
    api_keys = manager.load_keys()
    if not api_keys:
        logger.error("❌ 没有找到API keys，退出")
        return
    
    # 检查所有keys
    results = await manager.check_all_keys(api_keys)
    
    # 打印摘要
    manager.print_summary(results)
    
    # 保存有效keys
    if manager.valid_keys:
        success = manager.save_valid_keys()
        if success:
            logger.info("🎉 API Keys清理完成！")
        else:
            logger.error("❌ 保存失败")
    else:
        logger.warning("⚠️ 没有有效的API keys，不更新文件")


if __name__ == "__main__":
    asyncio.run(main())
