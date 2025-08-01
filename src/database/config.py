"""
Database Configuration
数据库配置

Cloud database configuration for Apple RAG system.
Apple RAG 系统的云端数据库配置。

项目使用云端数据库 (CLOUD_DB_*) 参数。
"""

import os
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Cloud database configuration"""

    # Cloud database configuration (云端数据库配置)
    host: str = os.getenv('CLOUD_DB_HOST', '198.12.70.36')
    port: int = int(os.getenv('CLOUD_DB_PORT', '5432'))
    database: str = os.getenv('CLOUD_DB_DATABASE', 'apple_rag_db')
    user: str = os.getenv('CLOUD_DB_USER', 'apple_rag_user')
    password: str = os.getenv('CLOUD_DB_PASSWORD', 'PYuwnP39iLR2pLk')
    sslmode: str = os.getenv('CLOUD_DB_SSLMODE', 'disable')

    # Connection pool configuration
    min_pool_size: int = 2
    max_pool_size: int = 30
    command_timeout: int = 3600

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create database configuration from environment variables"""
        return cls()

    def to_dict(self) -> dict:
        """Convert to dictionary for asyncpg.create_pool"""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'min_size': self.min_pool_size,
            'max_size': self.max_pool_size,
            'command_timeout': self.command_timeout
        }

    def validate(self) -> None:
        """Validate configuration"""
        if not self.password:
            raise ValueError("Database password is required")
        if not self.database:
            raise ValueError("Database name is required")
