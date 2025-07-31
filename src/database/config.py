"""
Database Configuration
数据库配置

PostgreSQL database configuration for Apple RAG system.
Apple RAG 系统的 PostgreSQL 数据库配置。
"""

import os
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """PostgreSQL database configuration"""

    # Database connection parameters
    host: str = os.getenv('DB_HOST', 'localhost')
    port: int = int(os.getenv('DB_PORT', '5432'))
    database: str = os.getenv('DB_DATABASE', 'apple_rag_db')
    user: str = os.getenv('DB_USER', 'apple_rag_user')
    password: str = os.getenv('DB_PASSWORD', '')
    sslmode: str = os.getenv('DB_SSLMODE', 'disable')

    # Connection pool configuration
    min_pool_size: int = 2
    max_pool_size: int = 10
    command_timeout: int = 3600  # 增加到1小时，支持大型迁移操作

    def __post_init__(self):
        """Validate database configuration after initialization"""
        if not self.password:
            raise ValueError("Database password is required")
        if not self.database:
            raise ValueError("Database name is required")

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create database configuration from environment variables"""
        return cls()

    @property
    def connection_string(self) -> str:
        """Get database connection string"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

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
