<h1 align="center">MCP RAG Server for Apple Developer Documentation</h1>

<p align="center">
  <em>Intelligent RAG Queries for Apple Developer Documentation using Advanced Vector Search</em>
</p>

A high-performance implementation of the [Model Context Protocol (MCP)](https://modelcontextprotocol.io) providing AI agents with intelligent document retrieval from Apple Developer Documentation using state-of-the-art RAG techniques.

## 🎯 **Key Features**

- **🚀 Production-Ready MCP Server**: Elegant async architecture with lazy database initialization
- **🧠 Advanced Vector Search**: Qwen3-Embedding-4B with Apple Silicon MPS optimization
- **🔍 Hybrid Search**: Combines vector similarity with keyword matching for comprehensive results
- **⚡ Smart Reranking**: Qwen3-Reranker-4B integration with automatic fallback mechanisms
- **🍎 Apple-Optimized**: Specialized for Apple Developer Documentation content structure
- **📊 PostgreSQL + pgvector**: High-performance vector storage with cosine similarity search
- **🔧 Modern Architecture**: FastMCP 2.9.0 with Streamable HTTP transport

## 🏗️ **Architecture Overview**

This system implements a **clean separation of concerns**:

### 🎯 **MCP Server (Core RAG Service)**
- **Single Responsibility**: Dedicated RAG query service via Model Context Protocol
- **Lazy Initialization**: DatabaseManager with async connection pool management
- **High Performance**: Optimized for fast query responses with minimal overhead
- **Type Safety**: Comprehensive type annotations and error handling

### 🕷️ **Independent Crawling System**
- **Batch Processing**: Intelligent batch crawling with connection pool reuse
- **Apple-Specialized**: Optimized for Apple Developer Documentation with anti-detection
- **Smart Discovery**: Automatic link discovery and URL pool expansion
- **Performance**: 3-5x faster crawling through concurrent processing

### 🖥️ **Web Management Interface**
- **Real-time Monitoring**: Live statistics and crawling progress
- **Content Management**: Browse and search crawled pages and chunks
- **System Health**: Database storage monitoring and performance metrics

The primary goal is to provide a robust, production-ready RAG service that can be integrated into AI coding assistants and knowledge engines like [Archon](https://github.com/coleam00/Archon).

## Overview

This system provides a complete solution for intelligent web crawling and advanced RAG queries through a **dual-architecture design**:

### 🎯 **MCP Server (Pure RAG Service)**
- **Single Responsibility**: Dedicated RAG query service via Model Context Protocol
- **Advanced Search**: Vector search, hybrid search, and intelligent reranking
- **High Performance**: Optimized for fast query responses without crawling overhead
- **Smart Reranking**: Qwen3-Reranker-4B integration with automatic fallback

### 🕷️ **Independent Crawling System**
- **Batch Processing**: Intelligent batch crawling with connection pool reuse
- **Smart Discovery**: Automatic link discovery and URL pool expansion
- **Apple-Optimized**: Specialized for Apple Developer Documentation with anti-detection
- **Performance**: 3-5x faster crawling through concurrent processing

### 🖥️ **Web Management Interface**
- **Real-time Monitoring**: Live statistics and crawling progress
- **Content Management**: Browse and search crawled pages and chunks
- **System Health**: Database storage monitoring and anomaly detection
- **User-Friendly**: Modern web interface for system administration

The system includes several advanced RAG strategies:
- **Hybrid Search** combining vector and keyword search
- **Smart Reranking** using Qwen3-Reranker-4B with automatic fallback
- **Contextual Embeddings** for enriched semantic understanding

See the [Configuration section](#configuration) below for details on how to enable and configure these strategies.

## Vision

The Crawl4AI RAG MCP server is just the beginning. Here's where we're headed:

1. **Integration with Archon**: Building this system directly into [Archon](https://github.com/coleam00/Archon) to create a comprehensive knowledge engine for AI coding assistants to build better AI agents.

2. **Multiple Embedding Models**: Expanding beyond OpenAI to support a variety of embedding models, including the ability to run everything locally with Ollama for complete control and privacy.

3. **Advanced RAG Strategies**: Implementing sophisticated retrieval techniques like contextual retrieval, late chunking, and others to move beyond basic "naive lookups" and significantly enhance the power and precision of the RAG system, especially as it integrates with Archon.

4. **Enhanced Chunking Strategy**: Implementing a Context 7-inspired chunking approach that focuses on examples and creates distinct, semantically meaningful sections for each chunk, improving retrieval precision.

5. **Performance Optimization**: Increasing crawling and indexing speed to make it more realistic to "quickly" index new documentation to then leverage it within the same prompt in an AI coding assistant.

## 🚀 **Technical Features**

### 🧠 **Advanced RAG Capabilities**
- **Vector Similarity Search**: Qwen3-Embedding-4B with 2560-dimension embeddings
- **Apple Silicon Optimization**: MPS acceleration for local embedding generation
- **Hybrid Search Strategy**: Combines semantic vector search with keyword matching
- **Smart Reranking**: Qwen3-Reranker-4B with automatic fallback to embedding similarity
- **Lazy Database Management**: Async connection pool with optimal resource usage
- **Type-Safe Implementation**: Comprehensive type annotations and error handling

### 🏗️ **Modern Architecture**
- **FastMCP 2.9.0**: Streamable HTTP transport for optimal performance
- **Async-First Design**: All operations use async/await for high concurrency
- **Lazy Initialization**: DatabaseManager with on-demand connection creation
- **Clean Separation**: Independent MCP server and crawling system components
- **Production-Ready**: Comprehensive error handling and graceful degradation
- **MCP专用Embedding**: Dedicated SiliconFlow API integration for query embedding
- **Structured Logging**: Multi-level logging system with service and business event tracking

### 🗄️ **Data Management**
- **PostgreSQL + pgvector**: Vector storage with cosine similarity search
- **Intelligent Chunking**: Header-based content segmentation for Apple docs
- **Embedding Storage**: Efficient vector storage in chunks table
- **Connection Pooling**: Optimized database connection management
- **Batch Operations**: High-performance bulk database operations

### 🍎 **Apple Documentation Optimization**
- **Content Extraction**: Specialized parsing for Apple Developer Documentation
- **Link Discovery**: Intelligent URL discovery and expansion
- **Anti-Detection**: Optimized crawling strategies for Apple websites
- **Content Filtering**: Removes navigation and repetitive content
- **Structured Processing**: Preserves document hierarchy and formatting

### 🔧 **Developer Experience**
- **Single MCP Tool**: Simple `perform_rag_query` interface
- **JSON Responses**: Structured results with URLs, content, and similarity scores
- **Comprehensive Logging**: Multi-level logging system for complete observability
- **Environment Configuration**: Flexible .env-based configuration
- **Error Handling**: Graceful error responses with detailed error messages

### 📊 **Logging Architecture**
- **Service Level**: Server startup, database connections, module initialization
- **Business Level**: RAG query processing, search operations, result formatting
- **Technical Level**: Embedding generation, API calls, performance metrics
- **Error Level**: Exception handling, API failures, connection issues
- **Debug Level**: Detailed flow tracking, intermediate results, technical diagnostics

## 🛠️ **MCP Tool**

The MCP server provides a single, powerful RAG query tool:

### `perform_rag_query`

**Advanced RAG queries with intelligent document retrieval from Apple Developer Documentation**

#### Parameters:
- **`query`** (string): Natural language search query
- **`match_count`** (integer, optional): Number of results to return (default: 5)

#### Features:
- **Vector Similarity Search**: Uses Qwen3-Embedding-4B for semantic understanding
- **Hybrid Search**: Combines vector similarity with keyword matching when enabled
- **Smart Reranking**: Qwen3-Reranker-4B with automatic fallback to embedding similarity
- **Apple Documentation**: Optimized for Apple Developer Documentation content
- **Structured Results**: Returns JSON with URLs, content snippets, and similarity scores

#### Example Response:
```json
{
  "success": true,
  "query": "SwiftUI navigation best practices",
  "search_mode": "hybrid",
  "reranking_applied": false,
  "results": [
    {
      "url": "https://developer.apple.com/documentation/swiftui/navigation",
      "content": "Navigation\nEnable people to move between different parts...",
      "similarity": 0.7660215725309129
    }
  ],
  "count": 1
}
```

#### Error Handling:
Returns structured error responses with detailed error messages for debugging and monitoring.

## System Components

### Independent Crawling System
The crawling functionality is provided by an independent system (`tools/continuous_crawler.py`):
- **Batch Processing**: Intelligent batch crawling with connection pooling
- **Smart Discovery**: Automatic link discovery and URL expansion
- **Performance Optimized**: 3-5x faster through concurrent processing
- **Apple Specialized**: Optimized for Apple Developer Documentation

### Web Management Interface
Access the management interface at `http://localhost:8001`:
- **Real-time Dashboard**: System statistics and monitoring
- **Content Browser**: Search and browse crawled content
- **Storage Analytics**: Database usage and anomaly detection
- **System Health**: Performance metrics and error tracking





## Prerequisites

- [Python 3.12+](https://www.python.org/downloads/) for running the system
- [PostgreSQL](https://postgresql.org/) with [pgvector](https://github.com/pgvector/pgvector) extension (vector database)
- [OpenAI API key](https://platform.openai.com/api-keys) or [Silicon Flow API key](https://siliconflow.cn/) (for embeddings)
- Sufficient disk space for crawled content (Apple docs ~800MB+)


## Installation

### Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/coleam00/mcp-crawl4ai-rag.git
   cd mcp-crawl4ai-rag
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on the configuration section below

4. Set up PostgreSQL with pgvector extension

### System Components Setup

#### 1. MCP Server (RAG Service)
```bash
# Run the MCP server for RAG queries
python src/crawl4ai_mcp.py
```

#### 2. Independent Crawling System
```bash
# Run the intelligent crawling system
python tools/continuous_crawler.py
```

#### 3. Web Management Interface
```bash
# Run the web dashboard (optional)
cd frontend && python api.py
```

The system components can run independently:
- **MCP Server**: Provides RAG query capabilities via Model Context Protocol
- **Crawling System**: Continuously crawls and processes content
- **Web Interface**: Provides monitoring and management capabilities

## Database Setup

Before running the server, you need to set up PostgreSQL with the pgvector extension:

1. Install PostgreSQL and the pgvector extension on your system

2. Create a database for the project (default: `crawl4ai_rag`)

3. The application will automatically create the necessary tables and indexes on first run



## ⚙️ **Configuration**

Create a `.env` file in the project root with the following variables:

### Core Configuration
```env
# MCP Server Configuration
HOST=127.0.0.1
PORT=4200
TRANSPORT=http  # FastMCP 2.9.0 with Streamable HTTP

# Embedding Configuration
EMBEDDING_MODE=local  # "local" for Qwen3-Embedding-4B, "api" for SiliconFlow
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B
EMBEDDING_DIM=2560

# API Configuration (if using EMBEDDING_MODE=api)
SILICONFLOW_API_KEY=your_siliconflow_api_key

# Reranker Configuration
USE_RERANKING=true
RERANKER_MODEL=Qwen/Qwen3-Reranker-4B

# Search Configuration
USE_HYBRID_SEARCH=true  # Combines vector and keyword search

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=crawl4ai_rag
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password
```

### Embedding Modes

#### Local Mode (Recommended)
```env
EMBEDDING_MODE=local
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B
```
- Uses local Qwen3-Embedding-4B with Apple Silicon MPS acceleration
- No API costs, complete privacy
- Optimized for Apple Developer Documentation

#### API Mode
```env
EMBEDDING_MODE=api
SILICONFLOW_API_KEY=your_siliconflow_api_key
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B
```
- Uses SiliconFlow API for embedding generation
- Requires API key and internet connection
- Consistent with local model output

### 📊 **Logging Configuration**

The MCP server includes a comprehensive logging system for monitoring and debugging:

#### Log Levels
```env
# Set in mcp.run() call or environment
LOG_LEVEL=debug  # debug, info, warning, error
```

#### Logging Features
- **Service Lifecycle**: Server startup, database connections, module initialization
- **RAG Query Flow**: Complete query processing pipeline tracking
- **Performance Metrics**: Search results, processing times, result counts
- **Error Handling**: Detailed error messages with context
- **Debug Information**: Technical details for development and troubleshooting

#### Log Output Examples
```
🚀 Starting MCP RAG Server
📡 Transport: HTTP (FastMCP 2.9.0)
🌐 Endpoint: http://127.0.0.1:4200/mcp
✅ Database connection established successfully
🔍 RAG query received: 'SwiftUI navigation' (match_count: 3)
🔧 Search mode: hybrid
📊 Vector search found 6 results
🔤 Keyword search found 4 results
✅ RAG query completed successfully: 3 results returned
```

#### Production Recommendations
- **Production**: Use `info` level for essential events only
- **Development**: Use `debug` level for detailed flow tracking
- **Monitoring**: Monitor `error` level logs for system health

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

## 🚀 **Running the System**

### 1. Start the MCP Server (Core Service)

```bash
# Run the MCP RAG server
python src/crawl4ai_mcp.py
```

The MCP server will start on `http://127.0.0.1:4200/mcp` using FastMCP 2.9.0 with Streamable HTTP transport.

**Server Features:**
- **Lazy Database Initialization**: Connections created on-demand for optimal performance
- **Apple Silicon Optimization**: MPS acceleration for local embedding generation
- **Comprehensive Logging**: Detailed logs for debugging and monitoring
- **Graceful Error Handling**: Structured error responses for all failure modes

**Logging Output:**
The server provides detailed logging for monitoring and debugging:
```
🚀 Starting MCP RAG Server
📡 Transport: HTTP (FastMCP 2.9.0)
🌐 Endpoint: http://127.0.0.1:4200/mcp
🔗 Initializing database connection for MCP server
✅ Database connection established successfully
✅ Reranker initialized successfully
```

**Query Processing Logs:**
```
🔍 RAG query received: 'SwiftUI navigation best practices' (match_count: 3)
🔧 Search mode: hybrid
🔍 Creating MCP query embedding for: SwiftUI navigation best practices...
✅ MCP query embedding created successfully, dimension: 2560
🔀 Performing hybrid search (vector + keyword)
📊 Vector search found 6 results
🔤 Keyword search found 4 results
🎯 Applying smart reranking
🔄 Reranking 6 results for query: SwiftUI navigation best prac...
✅ Reranking completed, top score: 0.8542
📋 Formatting 3 final results
✅ RAG query completed successfully: 3 results returned
```

### 2. Start the Crawling System (Optional)

```bash
# Run the independent crawling system for content acquisition
python tools/continuous_crawler.py
```

**Crawling Features:**
- **Batch Processing**: Intelligent batch crawling with connection pooling
- **Apple Documentation**: Specialized for Apple Developer Documentation
- **Smart Discovery**: Automatic link discovery and URL expansion
- **Performance**: 3-5x faster through concurrent processing

### 3. Start the Web Interface (Optional)

```bash
# Run the web management interface
cd frontend && python api.py
```

Access the web interface at `http://localhost:8001` for system monitoring and content management.

### 🏗️ **System Architecture**

The system uses a **clean separation of concerns**:

- **🎯 MCP Server**: Core RAG service for AI agent integration (required)
- **🕷️ Crawling System**: Independent content acquisition (run as needed)
- **🖥️ Web Interface**: Management and monitoring dashboard (optional)

Each component can run independently and scale according to your needs.

## 🔌 **MCP Client Integration**

### FastMCP 2.9.0 HTTP Configuration (Recommended)

The MCP server uses **FastMCP 2.9.0 with Streamable HTTP transport** for optimal performance and reliability.

#### Standard MCP Client Configuration:
```json
{
  "mcpServers": {
    "apple-docs-rag": {
      "transport": "http",
      "url": "http://127.0.0.1:4200/mcp"
    }
  }
}
```

#### Windsurf Configuration:
```json
{
  "mcpServers": {
    "apple-docs-rag": {
      "transport": "http",
      "serverUrl": "http://127.0.0.1:4200/mcp"
    }
  }
}
```

#### Claude Code CLI:
```bash
claude mcp add-json apple-docs-rag '{"type":"http","url":"http://127.0.0.1:4200/mcp"}' --scope user
```

### ✨ **Why HTTP Transport?**

- **🚀 Performance**: Streamable HTTP provides better performance than stdio
- **🔧 Reliability**: More stable connection management
- **📊 Monitoring**: Better debugging and monitoring capabilities
- **🔄 Scalability**: Supports multiple concurrent connections
- **🛠️ Modern**: Aligns with modern MCP best practices

### Alternative: Stdio Configuration

For environments that require stdio transport, you can still use the traditional approach:

```json
{
  "mcpServers": {
    "rag-server": {
      "command": "python",
      "args": ["path/to/mcp-crawl4ai-rag/src/crawl4ai_mcp.py", "--stdio"],
      "env": {
        "EMBEDDING_MODE": "api",
        "SILICONFLOW_API_KEY": "your_siliconflow_api_key",
        "EMBEDDING_MODEL": "Qwen/Qwen3-Embedding-4B",
        "EMBEDDING_DIM": "2560",
        "RERANKER_MODEL": "Qwen/Qwen3-Reranker-4B",
        "USE_RERANKING": "true",
        "USE_HYBRID_SEARCH": "true",
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

> **Note**: Streamable HTTP is the recommended transport for modern deployments. Use stdio only when required by your specific environment.

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
