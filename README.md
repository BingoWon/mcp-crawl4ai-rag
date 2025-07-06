<h1 align="center">Crawl4AI RAG MCP Server</h1>

<p align="center">
  <em>Web Crawling and RAG Capabilities for AI Agents and AI Coding Assistants</em>
</p>

A powerful implementation of the [Model Context Protocol (MCP)](https://modelcontextprotocol.io) integrated with [Crawl4AI](https://crawl4ai.com) and PostgreSQL for providing AI agents and AI coding assistants with advanced web crawling and RAG capabilities.

With this MCP server, you can <b>scrape anything</b> and then <b>use that knowledge anywhere</b> for RAG.

The primary goal is to bring this MCP server into [Archon](https://github.com/coleam00/Archon) as I evolve it to be more of a knowledge engine for AI coding assistants to build AI agents. This first version of the Crawl4AI/RAG MCP server will be improved upon greatly soon, especially making it more configurable so you can use different embedding models and run everything locally with Ollama.

Consider this GitHub repository a testbed, hence why I haven't been super actively address issues and pull requests yet. I certainly will though as I bring this into Archon V2!

## Overview

This MCP server provides tools that enable AI agents to crawl websites, store content in a vector database (PostgreSQL with pgvector), and perform RAG over the crawled content. It follows the best practices for building MCP servers based on the [Mem0 MCP server template](https://github.com/coleam00/mcp-mem0/) I provided on my channel previously.

The server includes several advanced RAG strategies that can be enabled to enhance retrieval quality:
- **Contextual Embeddings** for enriched semantic understanding
- **Hybrid Search** combining vector and keyword search
- **Reranking** for improved result relevance using cross-encoder models


See the [Configuration section](#configuration) below for details on how to enable and configure these strategies.

## Vision

The Crawl4AI RAG MCP server is just the beginning. Here's where we're headed:

1. **Integration with Archon**: Building this system directly into [Archon](https://github.com/coleam00/Archon) to create a comprehensive knowledge engine for AI coding assistants to build better AI agents.

2. **Multiple Embedding Models**: Expanding beyond OpenAI to support a variety of embedding models, including the ability to run everything locally with Ollama for complete control and privacy.

3. **Advanced RAG Strategies**: Implementing sophisticated retrieval techniques like contextual retrieval, late chunking, and others to move beyond basic "naive lookups" and significantly enhance the power and precision of the RAG system, especially as it integrates with Archon.

4. **Enhanced Chunking Strategy**: Implementing a Context 7-inspired chunking approach that focuses on examples and creates distinct, semantically meaningful sections for each chunk, improving retrieval precision.

5. **Performance Optimization**: Increasing crawling and indexing speed to make it more realistic to "quickly" index new documentation to then leverage it within the same prompt in an AI coding assistant.

## Features

- **Smart URL Detection**: Automatically detects and handles different URL types (regular webpages, sitemaps, text files)
- **Recursive Crawling**: Follows internal links to discover content
- **Parallel Processing**: Efficiently crawls multiple pages simultaneously
- **Content Chunking**: Intelligently splits content by headers and size for better processing
- **Vector Search**: Performs RAG over crawled content, optionally filtering by data source for precision
- **Source Retrieval**: Retrieve sources available for filtering to guide the RAG process

## Tools

The server provides essential web crawling and search tools:

### Core Tools (Always Available)

1. **`get_available_sources`**: Get a list of all available sources (domains) in the database
2. **`perform_rag_query`**: Search for relevant content using semantic search with optional source filtering





## Prerequisites

- [Docker/Docker Desktop](https://www.docker.com/products/docker-desktop/) if running the MCP server as a container (recommended)
- [Python 3.12+](https://www.python.org/downloads/) if running the MCP server directly through uv
- [PostgreSQL](https://postgresql.org/) with [pgvector](https://github.com/pgvector/pgvector) (database for RAG)
- [OpenAI API key](https://platform.openai.com/api-keys) (for generating embeddings)


## Installation

### Using Docker (Recommended)

1. Clone this repository:
   ```bash
   git clone https://github.com/coleam00/mcp-crawl4ai-rag.git
   cd mcp-crawl4ai-rag
   ```

2. Build the Docker image:
   ```bash
   docker build -t mcp/crawl4ai-rag --build-arg PORT=8051 .
   ```

3. Create a `.env` file based on the configuration section below

### Using uv directly (no Docker)

1. Clone this repository:
   ```bash
   git clone https://github.com/coleam00/mcp-crawl4ai-rag.git
   cd mcp-crawl4ai-rag
   ```

2. Install uv if you don't have it:
   ```bash
   pip install uv
   ```

3. Create and activate a virtual environment:
   ```bash
   uv venv
   .venv\Scripts\activate
   # on Mac/Linux: source .venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   uv pip install -e .
   crawl4ai-setup
   ```

5. Create a `.env` file based on the configuration section below

## Database Setup

Before running the server, you need to set up PostgreSQL with the pgvector extension:

1. Install PostgreSQL and the pgvector extension on your system

2. Create a database for the project (default: `crawl4ai_rag`)

3. The application will automatically create the necessary tables and indexes on first run



## Configuration

Create a `.env` file in the project root with the following variables:

```
# MCP Server Configuration
HOST=0.0.0.0
PORT=8051
TRANSPORT=sse

# Embedding Model Configuration (supports local LM Studio)
EMBEDDING_API_KEY=your_embedding_api_key  # or "lm-studio" for local
EMBEDDING_BASE_URL=https://api.openai.com/v1  # or http://127.0.0.1:1234/v1 for local
EMBEDDING_MODEL=text-embedding-3-small  # or text-embedding-nomic-embed-text-v1.5 for local

# LLM Configuration for summaries and contextual embeddings
LLM_API_KEY=your_llm_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-nano

# Reranker Configuration (local transformers with intelligent fallback)
RERANKER_MODEL_PATH=Qwen/Qwen3-Reranker-4B
RERANKER_DEVICE=auto

# RAG Strategies (set to "true" or "false", default to "false")
USE_CONTEXTUAL_EMBEDDINGS=false
USE_HYBRID_SEARCH=false
USE_RERANKING=false

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=crawl4ai_rag
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password
```

### Local LM Studio Support

The server now supports **native LM Studio integration** for embeddings, providing better compatibility and performance with local models:

- **Embedding Service**: Uses optimized `requests` library for direct HTTP calls to LM Studio
- **LLM Service**: Continues to use OpenAI client for chat completions
- **Separate Configuration**: Independent API keys, base URLs, and models for each service

**Example Local Configuration:**
```env
# Local LM Studio for embeddings
EMBEDDING_API_KEY=lm-studio
EMBEDDING_BASE_URL=http://127.0.0.1:1234/v1
EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5

# Local transformers for reranking with intelligent fallback
RERANKER_MODEL_PATH=Qwen/Qwen3-Reranker-4B
RERANKER_DEVICE=auto

# Remote service for LLM
LLM_API_KEY=your_remote_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
```

### 🎯 **Smart Qwen3-Reranker-4B Integration**

The server features **intelligent reranking** with automatic fallback:

**🥇 Primary: Qwen3-Reranker-4B (Transformers)**
- **Model**: Official `Qwen/Qwen3-Reranker-4B` via transformers library
- **Method**: Direct logits extraction following HuggingFace specification
- **Accuracy**: Maximum precision with true probability scores
- **Requirements**: Optimized 4B model, PyTorch + transformers

**🥈 Fallback: Embedding Similarity**
- **Method**: Cosine similarity using local embedding model
- **Speed**: Instant availability, no large downloads
- **Quality**: Good relevance ranking for most use cases
- **Compatibility**: Works with existing LM Studio setup

**Key Advantages:**
- ✅ **Zero Configuration**: Automatically selects best available method
- ✅ **Graceful Degradation**: Always functional, even without large models
- ✅ **Optimal Performance**: Uses true reranker when available
- ✅ **Local Privacy**: All processing happens locally

### RAG Strategy Options

The Crawl4AI RAG MCP server supports four powerful RAG strategies that can be enabled independently:

#### 1. **USE_CONTEXTUAL_EMBEDDINGS**
When enabled, this strategy enhances each chunk's embedding with additional context from the entire document. The system passes both the full document and the specific chunk to an LLM (configured via `LLM_MODEL`) to generate enriched context that gets embedded alongside the chunk content.

- **When to use**: Enable this when you need high-precision retrieval where context matters, such as technical documentation where terms might have different meanings in different sections.
- **Trade-offs**: Slower indexing due to LLM calls for each chunk, but significantly better retrieval accuracy.
- **Cost**: Additional LLM API calls during indexing.

#### 2. **USE_HYBRID_SEARCH**
Combines traditional keyword search with semantic vector search to provide more comprehensive results. The system performs both searches in parallel and intelligently merges results, prioritizing documents that appear in both result sets.

- **When to use**: Enable this when users might search using specific technical terms, function names, or when exact keyword matches are important alongside semantic understanding.
- **Trade-offs**: Slightly slower search queries but more robust results, especially for technical content.
- **Cost**: No additional API costs, just computational overhead.



#### 3. **USE_RERANKING**
Applies cross-encoder reranking to search results after initial retrieval. Uses a lightweight cross-encoder model (`cross-encoder/ms-marco-MiniLM-L-6-v2`) to score each result against the original query, then reorders results by relevance.

- **When to use**: Enable this when search precision is critical and you need the most relevant results at the top. Particularly useful for complex queries where semantic similarity alone might not capture query intent.
- **Trade-offs**: Adds ~100-200ms to search queries depending on result count, but significantly improves result ordering.
- **Cost**: No additional API costs - uses a local model that runs on CPU.
- **Benefits**: Better result relevance, especially for complex queries.



### Recommended Configurations

**For general documentation RAG:**
```
USE_CONTEXTUAL_EMBEDDINGS=false
USE_HYBRID_SEARCH=true
USE_RERANKING=true
```

**For enhanced search quality:**
```
USE_CONTEXTUAL_EMBEDDINGS=true
USE_HYBRID_SEARCH=true
USE_RERANKING=true
```

**For fast, basic RAG:**
```
USE_CONTEXTUAL_EMBEDDINGS=false
USE_HYBRID_SEARCH=true
USE_RERANKING=false
```

## Running the Server

### Using Docker

```bash
docker run --env-file .env -p 8051:8051 mcp/crawl4ai-rag
```

### Using Python

```bash
uv run src/crawl4ai_mcp.py
```

The server will start and listen on the configured host and port.

## Integration with MCP Clients

### SSE Configuration

Once you have the server running with SSE transport, you can connect to it using this configuration:

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "transport": "sse",
      "url": "http://localhost:8051/sse"
    }
  }
}
```

> **Note for Windsurf users**: Use `serverUrl` instead of `url` in your configuration:
> ```json
> {
>   "mcpServers": {
>     "crawl4ai-rag": {
>       "transport": "sse",
>       "serverUrl": "http://localhost:8051/sse"
>     }
>   }
> }
> ```
>
> **Note for Docker users**: Use `host.docker.internal` instead of `localhost` if your client is running in a different container. This will apply if you are using this MCP server within n8n!

> **Note for Claude Code users**: 
```
claude mcp add-json crawl4ai-rag '{"type":"http","url":"http://localhost:8051/sse"}' --scope user
```

### Stdio Configuration

Add this server to your MCP configuration for Claude Desktop, Windsurf, or any other MCP client:

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "python",
      "args": ["path/to/crawl4ai-mcp/src/crawl4ai_mcp.py"],
      "env": {
        "TRANSPORT": "stdio",
        "EMBEDDING_API_KEY": "your_embedding_api_key",
        "EMBEDDING_BASE_URL": "https://api.openai.com/v1",
        "EMBEDDING_MODEL": "text-embedding-3-small",
        "LLM_API_KEY": "your_llm_api_key",
        "LLM_BASE_URL": "https://api.openai.com/v1",
        "LLM_MODEL": "gpt-4.1-nano",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DATABASE": "crawl4ai_rag",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "your_postgres_password",

      }
    }
  }
}
```

### Docker with Stdio Configuration

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "docker",
      "args": ["run", "--rm", "-i",
               "-e", "TRANSPORT",
               "-e", "EMBEDDING_API_KEY",
               "-e", "EMBEDDING_BASE_URL",
               "-e", "EMBEDDING_MODEL",
               "-e", "LLM_API_KEY",
               "-e", "LLM_BASE_URL",
               "-e", "LLM_MODEL",
               "-e", "POSTGRES_HOST",
               "-e", "POSTGRES_PORT",
               "-e", "POSTGRES_DATABASE",
               "-e", "POSTGRES_USER",
               "-e", "POSTGRES_PASSWORD",
               "mcp/crawl4ai"],
      "env": {
        "TRANSPORT": "stdio",
        "EMBEDDING_API_KEY": "your_embedding_api_key",
        "EMBEDDING_BASE_URL": "https://api.openai.com/v1",
        "EMBEDDING_MODEL": "text-embedding-3-small",
        "LLM_API_KEY": "your_llm_api_key",
        "LLM_BASE_URL": "https://api.openai.com/v1",
        "LLM_MODEL": "gpt-4.1-nano",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DATABASE": "crawl4ai_rag",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "your_postgres_password"
      }
    }
  }
}
```



## Building Your Own Server

This implementation provides a foundation for building more complex MCP servers with web crawling capabilities. To build your own:

1. Add your own tools by creating methods with the `@mcp.tool()` decorator
2. Create your own lifespan function to add your own dependencies
3. Modify the `utils.py` file for any helper functions you need
4. Extend the crawling capabilities by adding more specialized crawlers
