"""
Database Module
数据库模块

Multi-mode database operations with PostgreSQL and HTTP API support.
支持PostgreSQL和HTTP API的多模式数据库操作。

Access Modes:
- local: Direct local PostgreSQL connection (本地直连)
- remote: HTTP API access (远程API访问)
- cloud: Cloud PostgreSQL connection (云端直连)
"""

from .client import DatabaseClient, create_database_client
from .http_client import HTTPDatabaseClient
from .config import DatabaseConfig, DatabaseAccessMode
from .operations import DatabaseOperations
from .utils import get_database_client, close_database_client

__all__ = [
    'DatabaseClient',
    'HTTPDatabaseClient',
    'create_database_client',
    'DatabaseConfig',
    'DatabaseAccessMode',
    'DatabaseOperations',
    'get_database_client',
    'close_database_client'
]
