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
    
    def __init__(self, keys_file: str = "config/api_keys.txt"):
        self.keys_file = Path(keys_file)
        self.valid_keys = []
        self.invalid_keys = []
        
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
        批量检查所有API keys
        
        Args:
            api_keys: API密钥列表
            
        Returns:
            检查结果字典
        """
        logger.info(f"🔍 开始检查 {len(api_keys)} 个API keys...")
        
        results = {}
        
        # 创建HTTP会话
        connector = aiohttp.TCPConnector(limit=5)  # 限制并发连接数
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # 创建任务列表，添加延迟避免频率限制
            tasks = []
            for i, api_key in enumerate(api_keys):
                # 每个请求间隔0.5秒
                delay = i * 0.5
                task = self._delayed_check(session, api_key, delay)
                tasks.append(task)
            
            # 并发执行所有检查
            check_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for result in check_results:
                if isinstance(result, Exception):
                    logger.error(f"❌ 检查过程中出现异常: {result}")
                    continue
                
                api_key, balance, status = result
                key_short = f"{api_key[:8]}...{api_key[-8:]}"
                
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
    
    async def _delayed_check(self, session: aiohttp.ClientSession, 
                           api_key: str, delay: float) -> Tuple[str, Optional[float], str]:
        """带延迟的检查"""
        if delay > 0:
            await asyncio.sleep(delay)
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
