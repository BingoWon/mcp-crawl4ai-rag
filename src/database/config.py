"""
Database Configuration
数据库配置

PostgreSQL connection configuration and validation.
PostgreSQL连接配置和验证。
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class PostgreSQLConfig:
    """PostgreSQL connection configuration"""
    
    # Connection parameters
    host: str = os.getenv('POSTGRES_HOST', 'localhost')
    port: int = int(os.getenv('POSTGRES_PORT', '5432'))
    database: str = os.getenv('POSTGRES_DATABASE', 'crawl4ai_rag')
    user: str = os.getenv('POSTGRES_USER', os.getenv('USER', 'postgres'))
    password: str = os.getenv('POSTGRES_PASSWORD', '')
    sslmode: str = os.getenv('POSTGRES_SSLMODE', 'prefer')
    
    # Pool configuration
    min_pool_size: int = 2
    max_pool_size: int = 10
    command_timeout: int = 60
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.database:
            raise ValueError("Database name is required")
        
        if self.port <= 0 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535")
    
    @classmethod
    def from_env(cls) -> "PostgreSQLConfig":
        """Create configuration from environment variables"""
        return cls()
    
    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for asyncpg.create_pool"""
        config = {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'min_size': self.min_pool_size,
            'max_size': self.max_pool_size,
            'command_timeout': self.command_timeout
        }

        # Add SSL configuration if specified
        if self.sslmode and self.sslmode != 'disable':
            config['ssl'] = self.sslmode

        return config
