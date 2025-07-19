"""
MCP Server for RAG Queries with Apple Documentation

This server provides a Model Context Protocol (MCP) tool for intelligent document retrieval
from Apple Developer Documentation using advanced RAG (Retrieval Augmented Generation) techniques.

Features:
- Vector similarity search using Qwen3-Embedding-4B on Apple Silicon MPS
- Hybrid search combining vector similarity and keyword matching
- Smart reranking with Qwen3-Reranker-4B for improved relevance
- MCP专用query embedding with SiliconFlow API for optimal consistency
- Optimized for Apple Developer Documentation content
- Elegant async architecture with lazy database initialization
- PostgreSQL vector storage with pgvector extension
- Comprehensive logging system for monitoring and debugging

Architecture:
- FastMCP 2.9.0 with Streamable HTTP transport
- Lazy DatabaseManager for optimal connection pool management
- Async-first design for high performance
- Type-safe implementation with comprehensive error handling
- Structured logging with INFO/DEBUG/ERROR levels
- MCP专用embedding optimization for query processing

Logging Features:
- Service lifecycle logging (startup, initialization, connections)
- RAG query processing flow tracking
- Database operations monitoring
- Error handling and exception tracking
- Performance metrics and result statistics
- Configurable log levels for development and production

Usage:
The server exposes a single MCP tool `perform_rag_query` that accepts:
- query: Natural language search query
- match_count: Number of results to return (default: 5)

Returns JSON with search results including URLs, content snippets, and similarity scores.

Logging Configuration:
Set log_level in mcp.run() to control verbosity:
- "debug": Detailed flow tracking and technical details
- "info": Important business events and service status
- "error": Error conditions and exceptions only
"""
from fastmcp import FastMCP
from typing import List, Dict, Any

from dotenv import load_dotenv
from pathlib import Path
import asyncio
import json
import os
import aiohttp

from local_reranker import create_reranker

from database import get_database_client as get_postgres_client, DatabaseOperations
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Load environment variables from the project root .env file
project_root = Path(__file__).resolve().parent.parent
dotenv_path = project_root / '.env'

# Force override of existing environment variables
load_dotenv(dotenv_path, override=True)

# Lazy initialization manager
class DatabaseManager:
    def __init__(self):
        self._operations = None
        self._lock = asyncio.Lock()

    async def get_operations(self):
        async with self._lock:
            if self._operations is None:
                logger.debug("🔗 Initializing database connection for MCP server")
                try:
                    client = await get_postgres_client()
                    self._operations = DatabaseOperations(client)
                    logger.info("✅ Database connection established successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to establish database connection: {e}")
                    raise
            return self._operations

# MCP专用硅基流动API配置
SILICONFLOW_API_URL = "https://api.siliconflow.cn/v1/embeddings"
MCP_EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-4B"


async def create_mcp_query_embedding(query: str) -> List[float]:
    """
    MCP专用query embedding - 仅使用硅基流动API

    专门为MCP RAG查询优化的embedding函数，强制使用硅基流动API，
    确保query embedding的一致性和性能。其他embedding操作保持现有逻辑。

    Args:
        query: 查询字符串

    Returns:
        L2标准化的embedding向量
    """
    # 输入验证
    if not query or not query.strip():
        logger.error("❌ Empty query provided for MCP embedding")
        raise ValueError("Query cannot be empty for embedding generation")

    query = query.strip()
    logger.debug(f"🔍 Creating MCP query embedding for: {query[:50]}...")

    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        logger.error("❌ SILICONFLOW_API_KEY not found for MCP query embedding")
        raise ValueError("SILICONFLOW_API_KEY is required for MCP query embedding")

    payload = {
        "model": MCP_EMBEDDING_MODEL,
        "input": query,
        "encoding_format": "float"
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(SILICONFLOW_API_URL, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ SiliconFlow API error {response.status}: {error_text}")
                    raise RuntimeError(f"SiliconFlow API error {response.status}: {error_text}")

                result = await response.json()
                embedding = result["data"][0]["embedding"]

                # L2标准化
                import math
                norm = math.sqrt(sum(x * x for x in embedding))
                normalized_embedding = [x / norm for x in embedding] if norm > 0 else embedding

                logger.debug(f"✅ MCP query embedding created successfully, dimension: {len(normalized_embedding)}")
                return normalized_embedding

    except Exception as e:
        logger.error(f"❌ Failed to create MCP query embedding: {e}")
        raise


# Global managers
db_manager = DatabaseManager()
reranking_model = None

# Initialize FastMCP server
mcp = FastMCP("mcp-rag-server")

def rerank_results(model: Any, query: str, results: List[Dict[str, Any]], content_key: str = "content") -> List[Dict[str, Any]]:
    """
    Rerank search results using Qwen3-Reranker-4B.

    Args:
        model: The Qwen3-Reranker model instance
        query: The search query
        results: List of search results
        content_key: The key in each result dict that contains the text content

    Returns:
        Reranked list of results sorted by relevance
    """
    if not model or not results:
        return results

    logger.debug(f"🔄 Reranking {len(results)} results for query: {query[:30]}...")

    try:
        # Extract content and create query-document pairs
        pairs = [(query, result.get(content_key, "")) for result in results]

        # Get relevance scores
        scores = model.predict(pairs)

        # Add scores and sort by relevance
        for i, result in enumerate(results):
            result["rerank_score"] = float(scores[i])

        reranked_results = sorted(results, key=lambda x: x.get("rerank_score", 0), reverse=True)
        logger.debug(f"✅ Reranking completed, top score: {reranked_results[0].get('rerank_score', 0):.4f}")
        return reranked_results

    except Exception as e:
        logger.error(f"❌ Reranking error: {e}")
        return results

# Search functions moved from utils.py

async def _search_documents_async(
    query: str,
    match_count: int = 10
) -> List[Dict[str, Any]]:
    """Search for documents using vector similarity."""
    # Create embedding for the query using MCP专用硅基流动API
    query_embedding = await create_mcp_query_embedding(query)

    # Use lazy database operations
    operations = await db_manager.get_operations()
    return await operations.search_documents_vector(query_embedding, match_count)

async def search_documents(query, match_count=10):
    """Asynchronous search for documents using vector similarity."""
    return await _search_documents_async(query, match_count)


@mcp.tool
async def perform_rag_query(query: str, match_count: int = 5) -> str:
    """
    Perform a RAG (Retrieval Augmented Generation) query on the stored content.

    This tool searches the vector database for content relevant to the query and returns
    the matching documents.

    Args:
        ctx: The MCP server provided context
        query: The search query
        match_count: Maximum number of results to return (default: 5)

    Returns:
        JSON string with the search results
    """
    # 输入验证 - 全局最优解
    if not query or not query.strip():
        logger.warning("⚠️ Empty query received")
        return json.dumps({
            "success": False,
            "query": query,
            "error": "Query cannot be empty. Please provide a search query to find relevant Apple Developer Documentation.",
            "suggestion": "Try searching for topics like 'SwiftUI navigation', 'iOS app development', or 'Apple API documentation'."
        }, indent=2)

    # 标准化查询字符串
    query = query.strip()

    logger.info(f"🔍 RAG query received: '{query}' (match_count: {match_count})")

    try:
        # Use lazy database operations
        operations = await db_manager.get_operations()

        # Check if hybrid search is enabled
        use_hybrid_search = os.getenv("USE_HYBRID_SEARCH", "false") == "true"
        logger.debug(f"🔧 Search mode: {'hybrid' if use_hybrid_search else 'vector'}")

        if use_hybrid_search:
            # Hybrid search: combine vector and keyword search
            logger.debug("🔀 Performing hybrid search (vector + keyword)")

            # 1. Get vector search results
            vector_results = await search_documents(
                query=query,
                match_count=match_count * 2
            )
            logger.debug(f"📊 Vector search found {len(vector_results)} results")

            # 2. Get keyword search results using database operations
            keyword_results = await operations.search_documents_keyword(
                query=query,
                match_count=match_count * 2
            )
            logger.debug(f"🔤 Keyword search found {len(keyword_results)} results")

            # 3. Combine results with preference for items appearing in both
            seen_ids = set()
            combined_results = []

            # First, add items that appear in both searches (highest priority)
            vector_ids = {r.get('id') for r in vector_results if r.get('id')}
            for kr in keyword_results:
                if kr['id'] in vector_ids and kr['id'] not in seen_ids:
                    # Find the vector result to get similarity score
                    for vr in vector_results:
                        if vr.get('id') == kr['id']:
                            # Boost similarity score for items in both results
                            vr['similarity'] = min(1.0, vr.get('similarity', 0) * 1.2)
                            combined_results.append(vr)
                            seen_ids.add(kr['id'])
                            break

            # Then add remaining vector results
            for vr in vector_results:
                if vr.get('id') and vr['id'] not in seen_ids and len(combined_results) < match_count:
                    combined_results.append(vr)
                    seen_ids.add(vr['id'])

            # Finally, add pure keyword matches if we still need more results
            for kr in keyword_results:
                if kr['id'] not in seen_ids and len(combined_results) < match_count:
                    # Convert keyword result to match vector result format
                    combined_results.append({
                        'id': kr['id'],
                        'url': kr['url'],
                        'content': kr['content'],
                        'similarity': 0.5  # Default similarity for keyword-only matches
                    })
                    seen_ids.add(kr['id'])

            # Use combined results
            results = combined_results[:match_count]

        else:
            # Standard vector search only
            results = await search_documents(
                query=query,
                match_count=match_count
            )

        # Apply reranking if enabled
        use_reranking = os.getenv("USE_RERANKING", "false") == "true"
        if use_reranking and reranking_model:
            logger.debug("🎯 Applying smart reranking")
            results = rerank_results(reranking_model, query, results, content_key="content")
        elif use_reranking:
            logger.debug("⚠️ Reranking enabled but model not available")

        logger.debug(f"📋 Formatting {len(results)} final results")

        # Format the results
        formatted_results = []
        for result in results:
            formatted_result = {
                "url": result.get("url"),
                "content": result.get("content"),
                "similarity": result.get("similarity")
            }
            # Include rerank score if available
            if "rerank_score" in result:
                formatted_result["rerank_score"] = result["rerank_score"]
            formatted_results.append(formatted_result)

        logger.info(f"✅ RAG query completed successfully: {len(formatted_results)} results returned")

        return json.dumps({
            "success": True,
            "query": query,
            "search_mode": "hybrid" if use_hybrid_search else "vector",
            "reranking_applied": use_reranking and reranking_model is not None,
            "results": formatted_results,
            "count": len(formatted_results)
        }, indent=2)
    except Exception as e:
        logger.error(f"❌ RAG query failed for '{query}': {e}")
        return json.dumps({
            "success": False,
            "query": query,
            "error": str(e)
        }, indent=2)

# Initialize resources at module level
# Initialize reranker if enabled
if os.getenv("USE_RERANKING", "false") == "true":
    reranking_model = create_reranker()
    logger.info("✅ Reranker initialized successfully")

if __name__ == "__main__":
    logger.info("🚀 Starting MCP RAG Server")
    logger.info("📡 Transport: HTTP (FastMCP 2.9.0)")
    logger.info("🌐 Endpoint: http://127.0.0.1:4200/mcp")

    # Run the MCP server with Streamable HTTP transport
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=4200,
        path="/mcp",
        log_level="debug"
    )