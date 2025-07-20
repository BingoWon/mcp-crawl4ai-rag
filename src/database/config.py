"""
NEON Cloud Database Configuration
NEON云数据库配置

Cloud-native PostgreSQL configuration for NEON database.
面向NEON数据库的云原生PostgreSQL配置。
"""

import os
from dataclasses import dataclass


@dataclass
class NEONConfig:
    """NEON cloud database configuration"""

    # NEON cloud connection parameters
    host: str = os.getenv('NEON_HOST', 'ep-restless-breeze-aeg59cuv-pooler.c-2.us-east-2.aws.neon.tech')
    port: int = int(os.getenv('NEON_PORT', '5432'))
    database: str = os.getenv('NEON_DATABASE', 'neondb')
    user: str = os.getenv('NEON_USER', 'neondb_owner')
    password: str = os.getenv('NEON_PASSWORD', '')
    sslmode: str = 'require'  # NEON requires SSL

    # Cloud-optimized pool configuration
    min_pool_size: int = 2
    max_pool_size: int = 10
    command_timeout: int = 60

    def __post_init__(self):
        """Validate NEON configuration after initialization"""
        if not self.password:
            raise ValueError("NEON password is required")
        if not self.database:
            raise ValueError("NEON database name is required")

    @classmethod
    def from_env(cls) -> "NEONConfig":
        """Create NEON configuration from environment variables"""
        return cls()

    @property
    def connection_string(self) -> str:
        """Get NEON connection string with SSL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?sslmode={self.sslmode}"

    def to_dict(self) -> dict:
        """Convert to dictionary for asyncpg.create_pool with SSL"""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'ssl': self.sslmode,
            'min_size': self.min_pool_size,
            'max_size': self.max_pool_size,
            'command_timeout': self.command_timeout
        }
