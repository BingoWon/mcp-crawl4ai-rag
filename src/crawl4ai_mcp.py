"""
MCP Server for RAG Queries with Apple Documentation

This server provides a Model Context Protocol (MCP) tool for intelligent document retrieval
from Apple Developer Documentation using advanced RAG (Retrieval Augmented Generation) techniques.

Features:
- Vector similarity search using Qwen3-Embedding-4B on Apple Silicon MPS
- Hybrid search combining vector similarity and keyword matching
- Smart reranking with Qwen3-Reranker-4B for improved relevance
- Optimized for Apple Developer Documentation content
- Elegant async architecture with lazy database initialization
- PostgreSQL vector storage with pgvector extension

Architecture:
- FastMCP 2.9.0 with Streamable HTTP transport
- Lazy DatabaseManager for optimal connection pool management
- Async-first design for high performance
- Type-safe implementation with comprehensive error handling

Usage:
The server exposes a single MCP tool `perform_rag_query` that accepts:
- query: Natural language search query
- match_count: Number of results to return (default: 5)

Returns JSON with search results including URLs, content snippets, and similarity scores.
"""
from fastmcp import FastMCP
from typing import List, Dict, Any

from dotenv import load_dotenv
from pathlib import Path
import asyncio
import json
import os

from local_reranker import create_reranker
from embedding import create_embedding

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
                client = await get_postgres_client()
                self._operations = DatabaseOperations(client)
            return self._operations

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

    try:
        # Extract content and create query-document pairs
        pairs = [(query, result.get(content_key, "")) for result in results]

        # Get relevance scores
        scores = model.predict(pairs)

        # Add scores and sort by relevance
        for i, result in enumerate(results):
            result["rerank_score"] = float(scores[i])

        return sorted(results, key=lambda x: x.get("rerank_score", 0), reverse=True)

    except Exception as e:
        logger.error(f"Reranking error: {e}")
        return results

# Search functions moved from utils.py

async def _search_documents_async(
    query: str,
    match_count: int = 10
) -> List[Dict[str, Any]]:
    """Search for documents using vector similarity."""
    # Create embedding for the query
    query_embedding = create_embedding(query)

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
    try:
        # Use lazy database operations
        operations = await db_manager.get_operations()

        # Check if hybrid search is enabled
        use_hybrid_search = os.getenv("USE_HYBRID_SEARCH", "false") == "true"

        if use_hybrid_search:
            # Hybrid search: combine vector and keyword search

            # 1. Get vector search results
            vector_results = await search_documents(
                query=query,
                match_count=match_count * 2
            )

            # 2. Get keyword search results using database operations
            keyword_results = await operations.search_documents_keyword(
                query=query,
                match_count=match_count * 2
            )

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
            results = rerank_results(reranking_model, query, results, content_key="content")

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

        return json.dumps({
            "success": True,
            "query": query,
            "search_mode": "hybrid" if use_hybrid_search else "vector",
            "reranking_applied": use_reranking and reranking_model is not None,
            "results": formatted_results,
            "count": len(formatted_results)
        }, indent=2)
    except Exception as e:
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
    # Run the MCP server with Streamable HTTP transport
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=4200,
        path="/mcp",
        log_level="debug"
    )