"""
MCP server for web crawling with Crawl4AI.

This server provides tools to crawl websites using Crawl4AI, automatically detecting
the appropriate crawl method based on URL type (sitemap, txt file, or regular webpage).
Provides advanced RAG capabilities with vector search, hybrid search, and reranking.
"""
from mcp.server.fastmcp import FastMCP, Context
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from xml.etree import ElementTree
from dotenv import load_dotenv
# Removed Supabase import - using PostgreSQL instead
from pathlib import Path
import requests
import asyncio
import json
import os

from local_reranker import create_reranker

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
# Import embedding functions
from embedding import create_embedding

from database import get_database_client as get_postgres_client, DatabaseOperations
from utils.logger import setup_logger

logger = setup_logger(__name__)


# Load environment variables from the project root .env file
project_root = Path(__file__).resolve().parent.parent
dotenv_path = project_root / '.env'

# Force override of existing environment variables
load_dotenv(dotenv_path, override=True)





# Create a dataclass for our application context
@dataclass
class Crawl4AIContext:
    """Context for the Crawl4AI MCP server."""
    crawler: AsyncWebCrawler
    db_client: Any  # PostgreSQL client
    db_operations: Any  # Database operations
    reranking_model: Optional[Any] = None

@asynccontextmanager
async def crawl4ai_lifespan(server: FastMCP) -> AsyncIterator[Crawl4AIContext]:
    """
    Manages the Crawl4AI client lifecycle.
    
    Args:
        server: The FastMCP server instance
        
    Yields:
        Crawl4AIContext: The context containing the Crawl4AI crawler and Supabase client
    """
    # Create browser configuration
    browser_config = BrowserConfig(
        headless=True,
        verbose=False
    )
    
    # Initialize the crawler
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.__aenter__()
    
    # Initialize PostgreSQL client
    db_client = await get_postgres_client()
    db_operations = DatabaseOperations(db_client)
    
    # Initialize smart reranker if enabled
    reranking_model = None
    if os.getenv("USE_RERANKING", "false") == "true":
        reranking_model = create_reranker()
        logger.info("✅ Reranker initialized successfully")
    

    
    try:
        yield Crawl4AIContext(
            crawler=crawler,
            db_client=db_client,
            db_operations=db_operations,
            reranking_model=reranking_model
        )
    finally:
        # Clean up all components
        await crawler.__aexit__(None, None, None)

# Initialize FastMCP server
mcp = FastMCP(
    "mcp-crawl4ai-rag",
    description="MCP server for RAG and web crawling with Crawl4AI",
    lifespan=crawl4ai_lifespan,
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT") or "8051")
)

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
    client,
    query: str,
    match_count: int = 10
) -> List[Dict[str, Any]]:
    """Search for documents using vector similarity."""
    # Create embedding for the query
    query_embedding = create_embedding(query)

    # Execute the search using the match_crawled_pages function
    result = await client.call_function('match_crawled_pages',
                                      query_embedding,
                                      match_count)
    return result

def search_documents(client, query, match_count=10):
    """Synchronous wrapper for search_documents."""
    import asyncio
    return asyncio.run(_search_documents_async(client, query, match_count))



def parse_sitemap(sitemap_url: str) -> List[str]:
    """
    Parse a sitemap and extract URLs.
    
    Args:
        sitemap_url: URL of the sitemap
        
    Returns:
        List of URLs found in the sitemap
    """
    resp = requests.get(sitemap_url)
    urls = []

    if resp.status_code == 200:
        try:
            tree = ElementTree.fromstring(resp.content)
            urls = [loc.text for loc in tree.findall('.//{*}loc')]
        except Exception as e:
            logger.error(f"Error parsing sitemap XML: {e}")

    return urls




@mcp.tool()
async def perform_rag_query(ctx: Context, query: str, match_count: int = 5) -> str:
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
        # Get the database operations from the context
        db_operations = ctx.request_context.lifespan_context.db_operations

        # Check if hybrid search is enabled
        use_hybrid_search = os.getenv("USE_HYBRID_SEARCH", "false") == "true"

        if use_hybrid_search:
            # Hybrid search: combine vector and keyword search

            # 1. Get vector search results
            vector_results = search_documents(
                client=ctx.request_context.lifespan_context.db_client,
                query=query,
                match_count=match_count * 2
            )

            # 2. Get keyword search results using database operations
            keyword_results = await db_operations.search_documents_keyword(
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
            results = search_documents(
                client=ctx.request_context.lifespan_context.db_client,
                query=query,
                match_count=match_count
            )

        # Apply reranking if enabled
        use_reranking = os.getenv("USE_RERANKING", "false") == "true"
        if use_reranking and ctx.request_context.lifespan_context.reranking_model:
            results = rerank_results(ctx.request_context.lifespan_context.reranking_model, query, results, content_key="content")

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
            "reranking_applied": use_reranking and ctx.request_context.lifespan_context.reranking_model is not None,
            "results": formatted_results,
            "count": len(formatted_results)
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "query": query,
            "error": str(e)
        }, indent=2)




async def crawl_markdown_file(crawler: AsyncWebCrawler, url: str) -> List[Dict[str, Any]]:
    """
    Crawl a .txt or markdown file.
    
    Args:
        crawler: AsyncWebCrawler instance
        url: URL of the file
        
    Returns:
        List of dictionaries with URL and markdown content
    """
    crawl_config = CrawlerRunConfig()

    result = await crawler.arun(url=url, config=crawl_config)
    if result.success and result.markdown:
        return [{'url': url, 'markdown': result.markdown}]
    else:
        logger.error(f"Failed to crawl {url}: {result.error_message}")
        return []


async def main():
    transport = os.getenv("TRANSPORT", "sse")
    if transport == 'sse':
        # Run the MCP server with sse transport
        await mcp.run_sse_async()
    else:
        # Run the MCP server with stdio transport
        await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())