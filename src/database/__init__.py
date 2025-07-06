"""
Database Module
数据库模块

Independent database operations with PostgreSQL support.
独立的数据库操作，支持PostgreSQL。
"""

from .client import PostgreSQLClient, PostgreSQLConfig
from .operations import DatabaseOperations
from .utils import get_database_client, close_database_client

__all__ = [
    'PostgreSQLClient',
    'PostgreSQLConfig', 
    'DatabaseOperations',
    'get_database_client',
    'close_database_client'
]
