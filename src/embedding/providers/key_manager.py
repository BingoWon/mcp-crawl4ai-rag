"""
API Key管理器 - 最巧妙精简有效的实现

一个文本文件，每行一个key，失效就删除。
没有复杂的JSON，没有状态跟踪，没有冗余功能。
"""

from pathlib import Path
from typing import List
import aiofiles
from threading import Lock


class KeyManager:
    """API Key管理器 - 优雅现代精简的全局最优解"""

    def __init__(self, keys_file: str = "config/api_keys.txt"):
        self.keys_file = Path(keys_file)
        self._lock = Lock()
        self._current_index = 0

        # 确保文件存在
        if not self.keys_file.exists():
            self.keys_file.parent.mkdir(parents=True, exist_ok=True)
            self.keys_file.write_text("")
    
    def get_current_key(self) -> str:
        """获取当前索引的key"""
        with self._lock:
            if not self.keys_file.exists():
                raise RuntimeError("No API keys file found")

            keys = self._read_keys()
            if not keys:
                raise RuntimeError("No API keys available")

            # 确保索引有效
            if self._current_index >= len(keys):
                self._current_index = 0

            return keys[self._current_index]
    
    def _read_keys(self) -> List[str]:
        """读取所有keys"""
        try:
            content = self.keys_file.read_text().strip()
            if not content:
                return []
            return [key.strip() for key in content.split('\n') if key.strip()]
        except Exception:
            return []
    
    def switch_to_next_key(self) -> str:
        """切换到下一个可用key"""
        with self._lock:
            keys = self._read_keys()
            if not keys:
                raise RuntimeError("No API keys available")

            # 切换到下一个key
            self._current_index = (self._current_index + 1) % len(keys)

            current_key = keys[self._current_index]
            print(f"🔄 Switched to next key: {current_key[:20]}...")
            return current_key

    async def remove_key(self, key: str) -> bool:
        """删除失效的key"""
        with self._lock:
            keys = self._read_keys()
            if key not in keys:
                return False

            # 获取要删除的key的索引
            key_index = keys.index(key)

            # 删除失效key
            keys.remove(key)

            # 调整当前索引
            if key_index <= self._current_index and self._current_index > 0:
                self._current_index -= 1
            elif self._current_index >= len(keys) and len(keys) > 0:
                self._current_index = 0

            # 写回文件
            async with aiofiles.open(self.keys_file, 'w') as f:
                await f.write('\n'.join(keys))

            print(f"🗑️ Removed failed key: {key[:20]}...")
            return True
    
    def get_stats(self) -> dict:
        """获取简单统计"""
        with self._lock:
            keys = self._read_keys()
            return {"total_keys": len(keys)}
    
    async def add_key(self, key: str) -> None:
        """添加新key"""
        with self._lock:
            keys = self._read_keys()
            if key not in keys:
                keys.append(key)
                async with aiofiles.open(self.keys_file, 'w') as f:
                    await f.write('\n'.join(keys))
