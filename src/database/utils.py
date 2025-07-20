"""
NEON Cloud Database Utilities
NEON云数据库工具

Global NEON database client management and utility functions.
全局NEON数据库客户端管理和工具函数。
"""

from typing import Optional
from .client import NEONClient
from .config import NEONConfig
from .operations import DatabaseOperations


# ============================================================================
# GLOBAL NEON CLIENT MANAGEMENT
# ============================================================================

_database_client: Optional[NEONClient] = None
_database_operations: Optional[DatabaseOperations] = None


async def get_database_client() -> NEONClient:
    """Get or create the global NEON client instance"""
    global _database_client
    if _database_client is None:
        config = NEONConfig.from_env()
        _database_client = NEONClient(config)
        await _database_client.initialize()
    return _database_client


async def get_database_operations() -> DatabaseOperations:
    """Get or create the global database operations instance"""
    global _database_operations
    if _database_operations is None:
        client = await get_database_client()
        _database_operations = DatabaseOperations(client)
    return _database_operations


async def close_database_client() -> None:
    """Close the global database client"""
    global _database_client, _database_operations
    if _database_client:
        await _database_client.close()
        _database_client = None
        _database_operations = None








async def _search_documents_async(client, query, match_count=10):
    """Backward compatibility function for document search"""
    ops = await get_database_operations()

    # Use keyword search
    return await ops.search_documents_keyword(query, match_count)





# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def check_database_connection() -> bool:
    """Check if database connection is working"""
    try:
        client = await get_database_client()
        await client.fetch_val("SELECT 1")
        return True
    except Exception as e:
        from utils.logger import setup_logger
        logger = setup_logger(__name__)
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def get_database_stats() -> dict:
    """Get database statistics"""
    try:
        client = await get_database_client()
        
        chunks_count = await client.fetch_val("SELECT COUNT(*) FROM chunks")
        pages_count = await client.fetch_val("SELECT COUNT(*) FROM pages")

        return {
            'chunks': chunks_count,
            'pages': pages_count,
            'total_records': chunks_count
        }
    except Exception as e:
        from utils.logger import setup_logger
        logger = setup_logger(__name__)
        logger.error(f"❌ Failed to get database stats: {e}")
        return {}


async def cleanup_database() -> None:
    """Clean up database resources"""
    await close_database_client()
