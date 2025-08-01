"""
Database Configuration
数据库配置

Multi-mode database configuration for Apple RAG system.
Apple RAG 系统的多模式数据库配置。

支持三种访问模式：
- local: 本地直连（本机爬虫使用）
- remote: 远程API（其他机器爬虫使用）
- cloud: 云端直连（备用）
"""

import os
from dataclasses import dataclass
from enum import Enum


class DatabaseAccessMode(Enum):
    """数据库访问模式"""
    LOCAL = "local"      # 本地直连
    REMOTE = "remote"    # 远程API
    CLOUD = "cloud"      # 云端直连


@dataclass
class DatabaseConfig:
    """Multi-mode database configuration"""

    # Access mode
    access_mode: DatabaseAccessMode = DatabaseAccessMode.LOCAL

    # Local database configuration (本地直连)
    local_host: str = os.getenv('LOCAL_DB_HOST', 'localhost')
    local_port: int = int(os.getenv('LOCAL_DB_PORT', '6432'))
    local_database: str = os.getenv('LOCAL_DB_DATABASE', 'crawl4ai_rag')
    local_user: str = os.getenv('LOCAL_DB_USER', 'bingo')
    local_password: str = os.getenv('LOCAL_DB_PASSWORD', 'xRdtkHIa53nYMWJ')
    local_sslmode: str = os.getenv('LOCAL_DB_SSLMODE', 'disable')

    # Remote API configuration (远程API)
    remote_api_base_url: str = os.getenv('DB_API_BASE_URL', 'https://db.apple-rag.com')
    remote_api_timeout: int = int(os.getenv('REMOTE_DB_API_TIMEOUT', '30'))

    # API认证配置
    api_key: str = os.getenv('DATABASE_API_KEY', 'ZBYlBx77H9Sc87k')

    # Cloud database configuration (云端直连)
    cloud_host: str = os.getenv('CLOUD_DB_HOST', '198.12.70.36')
    cloud_port: int = int(os.getenv('CLOUD_DB_PORT', '5432'))
    cloud_database: str = os.getenv('CLOUD_DB_DATABASE', 'apple_rag_db')
    cloud_user: str = os.getenv('CLOUD_DB_USER', 'apple_rag_user')
    cloud_password: str = os.getenv('CLOUD_DB_PASSWORD', 'PYuwnP39iLR2pLk')
    cloud_sslmode: str = os.getenv('CLOUD_DB_SSLMODE', 'disable')

    # Connection pool configuration
    min_pool_size: int = 2
    max_pool_size: int = 30
    command_timeout: int = 3600  # 增加到1小时，支持大型迁移操作

    def __post_init__(self):
        """Initialize access mode from environment variable"""
        mode_str = os.getenv('DB_ACCESS_MODE', 'local').lower()
        try:
            self.access_mode = DatabaseAccessMode(mode_str)
        except ValueError:
            self.access_mode = DatabaseAccessMode.LOCAL

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create database configuration from environment variables"""
        return cls()

    @property
    def is_local_mode(self) -> bool:
        """Check if using local database mode"""
        return self.access_mode == DatabaseAccessMode.LOCAL

    @property
    def is_remote_mode(self) -> bool:
        """Check if using remote API mode"""
        return self.access_mode == DatabaseAccessMode.REMOTE

    @property
    def is_cloud_mode(self) -> bool:
        """Check if using cloud database mode"""
        return self.access_mode == DatabaseAccessMode.CLOUD

    @property
    def current_host(self) -> str:
        """Get current database host based on access mode"""
        if self.is_local_mode:
            return self.local_host
        elif self.is_cloud_mode:
            return self.cloud_host
        else:
            raise ValueError(f"Invalid access mode: {self.access_mode}")

    @property
    def current_port(self) -> int:
        """Get current database port based on access mode"""
        if self.is_local_mode:
            return self.local_port
        elif self.is_cloud_mode:
            return self.cloud_port
        else:
            raise ValueError(f"Invalid access mode: {self.access_mode}")

    @property
    def current_database(self) -> str:
        """Get current database name based on access mode"""
        if self.is_local_mode:
            return self.local_database
        elif self.is_cloud_mode:
            return self.cloud_database
        else:
            raise ValueError(f"Invalid access mode: {self.access_mode}")

    @property
    def current_user(self) -> str:
        """Get current database user based on access mode"""
        if self.is_local_mode:
            return self.local_user
        elif self.is_cloud_mode:
            return self.cloud_user
        else:
            raise ValueError(f"Invalid access mode: {self.access_mode}")

    @property
    def current_password(self) -> str:
        """Get current database password based on access mode"""
        if self.is_local_mode:
            return self.local_password
        elif self.is_cloud_mode:
            return self.cloud_password
        else:
            raise ValueError(f"Invalid access mode: {self.access_mode}")

    @property
    def current_sslmode(self) -> str:
        """Get current SSL mode based on access mode"""
        if self.is_local_mode:
            return self.local_sslmode
        elif self.is_cloud_mode:
            return self.cloud_sslmode
        else:
            raise ValueError(f"Invalid access mode: {self.access_mode}")

    @property
    def connection_string(self) -> str:
        """Get database connection string for current mode"""
        if self.is_remote_mode:
            return f"remote_api://{self.remote_api_base_url}"
        else:
            return f"postgresql://{self.current_user}:{self.current_password}@{self.current_host}:{self.current_port}/{self.current_database}"

    def to_dict(self) -> dict:
        """Convert to dictionary for asyncpg.create_pool"""
        if self.is_remote_mode:
            return {
                'api_base_url': self.remote_api_base_url,
                'timeout': self.remote_api_timeout
            }
        else:
            return {
                'host': self.current_host,
                'port': self.current_port,
                'database': self.current_database,
                'user': self.current_user,
                'password': self.current_password,
                'min_size': self.min_pool_size,
                'max_size': self.max_pool_size,
                'command_timeout': self.command_timeout
            }

    def validate(self) -> None:
        """Validate configuration based on access mode"""
        if self.is_remote_mode:
            if not self.remote_api_base_url:
                raise ValueError("Remote API base URL is required for remote mode")
        else:
            # For local mode, password can be empty (trust authentication)
            # For cloud mode, password is required
            if self.is_cloud_mode and not self.current_password:
                raise ValueError(f"Database password is required for {self.access_mode.value} mode")
            if not self.current_database:
                raise ValueError(f"Database name is required for {self.access_mode.value} mode")
