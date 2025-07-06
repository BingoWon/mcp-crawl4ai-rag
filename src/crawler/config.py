"""
Crawler Configuration
爬虫配置模块

Provides configuration classes for the independent crawler.
为独立爬虫提供配置类。
"""

from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class CrawlerConfig:
    """Configuration for the independent crawler"""
    
    # Database configuration (PostgreSQL)
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_database: str = os.getenv("POSTGRES_DATABASE", "crawl4ai_rag")
    postgres_user: str = os.getenv("POSTGRES_USER", os.getenv("USER", "postgres"))
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")
    
    # Crawling parameters
    max_depth: int = 3
    max_concurrent: int = 10
    chunk_size: int = 5000
    
    # Apple extractor availability
    apple_extractor_available: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.postgres_database:
            raise ValueError("PostgreSQL database name must be provided")

        if self.postgres_port <= 0 or self.postgres_port > 65535:
            raise ValueError("PostgreSQL port must be between 1 and 65535")
    
    @classmethod
    def from_env(cls) -> "CrawlerConfig":
        """Create configuration from environment variables"""
        return cls()

    @property
    def postgres_config_dict(self) -> dict:
        """Get PostgreSQL configuration as dictionary"""
        return {
            'host': self.postgres_host,
            'port': self.postgres_port,
            'database': self.postgres_database,
            'user': self.postgres_user,
            'password': self.postgres_password
        }
    
    @classmethod
    def with_params(cls, max_depth: int = 3, max_concurrent: int = 10, chunk_size: int = 5000) -> "CrawlerConfig":
        """Create configuration with custom parameters"""
        return cls(
            max_depth=max_depth,
            max_concurrent=max_concurrent,
            chunk_size=chunk_size
        )
