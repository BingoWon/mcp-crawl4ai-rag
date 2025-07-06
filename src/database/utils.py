"""
Database Utilities
数据库工具

Global database client management and utility functions.
全局数据库客户端管理和工具函数。
"""

from typing import Optional
from .client import PostgreSQLClient
from .config import PostgreSQLConfig
from .operations import DatabaseOperations


# ============================================================================
# GLOBAL CLIENT MANAGEMENT
# ============================================================================

_database_client: Optional[PostgreSQLClient] = None
_database_operations: Optional[DatabaseOperations] = None


async def get_database_client() -> PostgreSQLClient:
    """Get or create the global PostgreSQL client instance"""
    global _database_client
    if _database_client is None:
        config = PostgreSQLConfig.from_env()
        _database_client = PostgreSQLClient(config)
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


# ============================================================================
# BACKWARD COMPATIBILITY FUNCTIONS
# ============================================================================

async def add_documents_to_database(client, urls, chunk_numbers, contents, metadatas, url_to_full_document, batch_size=20):
    """Backward compatibility function for adding documents"""
    # Convert to new format
    data = []
    for i in range(len(urls)):
        data.append({
            'url': urls[i],
            'chunk_number': chunk_numbers[i],
            'content': contents[i],
            'metadata': metadatas[i],
            'source_id': metadatas[i].get('source', ''),
            'embedding': None  # Will be set by caller
        })
    
    # Use new operations
    ops = await get_database_operations()
    await ops.insert_crawled_pages(data)


async def add_code_examples_to_database(client, urls, chunk_numbers, code_examples, summaries, metadatas, batch_size=20):
    """Backward compatibility function for adding code examples"""
    # Convert to new format
    data = []
    for i in range(len(urls)):
        data.append({
            'url': urls[i],
            'chunk_number': chunk_numbers[i],
            'content': code_examples[i],
            'summary': summaries[i],
            'metadata': metadatas[i],
            'source_id': metadatas[i].get('source', ''),
            'embedding': None  # Will be set by caller
        })
    
    # Use new operations
    ops = await get_database_operations()
    await ops.insert_code_examples(data)


async def _search_documents_async(client, query, match_count=10, filter_metadata=None):
    """Backward compatibility function for document search"""
    ops = await get_database_operations()
    
    # For now, use keyword search (vector search requires embedding)
    source_filter = filter_metadata.get('source') if filter_metadata else None
    return await ops.search_documents_keyword(query, match_count, source_filter)


async def _search_code_examples_async(client, query, match_count=10, filter_metadata=None, source_id=None):
    """Backward compatibility function for code examples search"""
    ops = await get_database_operations()
    
    # Use source_id parameter or extract from filter_metadata
    source_filter = source_id or (filter_metadata.get('source') if filter_metadata else None)
    return await ops.search_code_examples_keyword(query, match_count, source_filter)


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
        print(f"❌ Database connection failed: {e}")
        return False


async def get_database_stats() -> dict:
    """Get database statistics"""
    try:
        client = await get_database_client()
        
        crawled_pages_count = await client.fetch_val("SELECT COUNT(*) FROM crawled_pages")
        code_examples_count = await client.fetch_val("SELECT COUNT(*) FROM code_examples")
        sources_count = await client.fetch_val("SELECT COUNT(*) FROM sources")
        
        return {
            'crawled_pages': crawled_pages_count,
            'code_examples': code_examples_count,
            'sources': sources_count,
            'total_records': crawled_pages_count + code_examples_count
        }
    except Exception as e:
        print(f"❌ Failed to get database stats: {e}")
        return {}


async def cleanup_database() -> None:
    """Clean up database resources"""
    await close_database_client()
