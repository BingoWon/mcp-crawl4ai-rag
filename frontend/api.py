#!/usr/bin/env python3
"""
Database Viewer API - 现代化重构版本
数据库查看器API

现代化的FastAPI应用，提供高性能的数据库查询接口。
采用连接池管理、完全参数化查询、分层错误处理等最佳实践。
"""

import sys
import ast
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any
from enum import Enum

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

# 环境配置
load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.client import create_database_client

# 配置类
class APIConfig:
    HOST = "0.0.0.0"
    PORT = 8001
    PAGE_LIMIT = 100
    APPLE_DOC_PREFIX = "https://developer.apple.com/documentation"

    # 有效的排序字段 - 彻底重构设计
    VALID_PAGE_SORTS = {"id", "url", "created_at", "processed_at"}
    VALID_CHUNK_SORTS = {"id", "url"}

# 错误类型
class APIErrorType(Enum):
    DATABASE_ERROR = "数据库连接错误"
    VALIDATION_ERROR = "参数验证错误"
    INTERNAL_ERROR = "内部服务器错误"

# 工具函数
def simplify_apple_url(url: str) -> str:
    """简化Apple文档URL显示"""
    if url.startswith(APIConfig.APPLE_DOC_PREFIX):
        return url.replace(APIConfig.APPLE_DOC_PREFIX, "...")
    return url

def safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def handle_api_error(error_type: APIErrorType = APIErrorType.INTERNAL_ERROR) -> JSONResponse:
    """统一错误处理"""
    return JSONResponse(
        content={
            "success": False,
            "error": error_type.value,
            "data": None
        },
        status_code=500
    )

# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 现代化连接池管理"""
    # 启动时初始化数据库连接池
    app.state.db_client = create_database_client()
    await app.state.db_client.initialize()
    yield
    # 关闭时清理连接池
    await app.state.db_client.close()

# FastAPI应用初始化 - 现代化配置
app = FastAPI(
    title="Database Viewer API",
    version="2.0.0",
    description="现代化的数据库查看器API，采用连接池管理和安全查询",
    lifespan=lifespan
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库客户端访问器
async def get_db_client():
    """获取数据库客户端 - 现代化连接池访问"""
    return app.state.db_client


@app.get("/api/pages")
async def get_pages(
    search: str = Query("", description="搜索关键词"),
    sort: str = Query("created_at", description="排序字段"),
    order: str = Query("desc", description="排序方向")
) -> JSONResponse:
    """获取pages表数据 - 现代化安全查询"""
    try:
        client = await get_db_client()

        # 参数验证和安全处理 - 精简4字段设计
        sort_column = sort if sort in APIConfig.VALID_PAGE_SORTS else "created_at"
        sort_order = "ASC" if order.lower() == "asc" else "DESC"

        # 精简查询 - 只显示有content + 双重排序 + processed_at字段
        if search:
            query = f"""
                SELECT id, url, content, created_at, processed_at
                FROM pages
                WHERE content IS NOT NULL AND content != ''
                AND (url ILIKE $1 OR content ILIKE $1)
                ORDER BY {sort_column} {sort_order}, url ASC
                LIMIT $2
            """
            pages = await client.fetch_all(query, f"%{search}%", APIConfig.PAGE_LIMIT)
        else:
            query = f"""
                SELECT id, url, content, created_at, processed_at
                FROM pages
                WHERE content IS NOT NULL AND content != ''
                ORDER BY {sort_column} {sort_order}, url ASC
                LIMIT $1
            """
            pages = await client.fetch_all(query, APIConfig.PAGE_LIMIT)



        # 格式化数据 - 精简4字段设计
        formatted_pages = []
        content_count = 0

        for page in pages:
            content = page["content"]
            if content.strip():
                content_count += 1

            # 安全的内容截取
            display_content = content[:100] + "..." if len(content) > 100 else content

            formatted_pages.append({
                "id": page["id"],
                "url": simplify_apple_url(page["url"]),
                "full_url": page["url"],
                "content": display_content,
                "full_content": content,
                "created_at": page["created_at"],
                "processed_at": page["processed_at"]
            })

        return JSONResponse({
            "success": True,
            "data": formatted_pages,
            "count": len(formatted_pages),
            "stats": {
                "content_count": content_count
            }
        })

    except Exception:
        return handle_api_error(APIErrorType.DATABASE_ERROR)


@app.get("/api/chunks")
async def get_chunks(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(50, ge=1, le=100, description="每页大小"),
    search: str = Query("", description="搜索关键词"),
    page_id: str = Query("", description="页面ID过滤"),
    sort: str = Query("url", description="排序字段"),
    order: str = Query("asc", description="排序方向")
) -> JSONResponse:
    """获取chunks表数据 - 现代化分页查询"""
    try:
        client = await get_db_client()

        # 参数验证
        sort_column = sort if sort in APIConfig.VALID_CHUNK_SORTS else "created_at"
        sort_order = "ASC" if order.lower() == "asc" else "DESC"
        offset = (page - 1) * size

        # 构建查询条件
        where_conditions = []
        params = []

        if search:
            where_conditions.append("(url ILIKE $1 OR content ILIKE $1)")
            params.append(f"%{search}%")

        if page_id:
            param_index = len(params) + 1
            where_conditions.append(f"url IN (SELECT url FROM pages WHERE id = ${param_index}::uuid)")
            params.append(page_id)

        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

        # 简化查询 - 分别获取总数和数据
        # 获取总数
        count_query = f"SELECT COUNT(*) as total FROM chunks {where_clause}"
        total_result = await client.fetch_one(count_query, *params)
        total = total_result["total"]

        # 获取分页数据
        limit_param = len(params) + 1
        offset_param = len(params) + 2
        query = f"""
            SELECT id, url, content, embedding
            FROM chunks {where_clause}
            ORDER BY {sort_column} {sort_order}, url ASC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """
        params.extend([size, offset])
        chunks = await client.fetch_all(query, *params)

        # 格式化数据 - 现代化处理
        formatted_chunks = []
        for chunk in chunks:
            content = chunk["content"]
            display_content = content[:100] + "..." if len(content) > 100 else content

            # 安全的embedding处理
            embedding_info = "无"
            if chunk.get("embedding"):
                try:
                    embedding_array = ast.literal_eval(chunk["embedding"])
                    if isinstance(embedding_array, list) and len(embedding_array) > 0:
                        embedding_info = str([round(x, 4) for x in embedding_array[:5]])
                except Exception:
                    embedding_info = "解析错误"

            formatted_chunks.append({
                "id": chunk["id"],
                "url": simplify_apple_url(chunk["url"]),
                "full_url": chunk["url"],
                "content": display_content,
                "full_content": content,
                "embedding_info": embedding_info,
                "raw_embedding": str(chunk["embedding"]) if chunk.get("embedding") else None
            })

        return JSONResponse({
            "success": True,
            "data": formatted_chunks,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            }
        })

    except Exception:
        return handle_api_error(APIErrorType.DATABASE_ERROR)


@app.get("/api/stats")
async def get_stats() -> JSONResponse:
    """获取统计信息 - 现代化统计查询"""
    try:
        client = await get_db_client()

        # 精简统计查询 - 添加processed_at统计
        result = await client.fetch_one("""
            WITH page_stats AS (
                SELECT
                    COUNT(*) as total_pages,
                    COUNT(CASE WHEN content IS NOT NULL AND content != '' THEN 1 END) as pages_with_content,
                    COUNT(CASE WHEN processed_at IS NOT NULL THEN 1 END) as pages_processed,
                    COUNT(CASE WHEN processed_at IS NULL AND content IS NOT NULL AND content != '' THEN 1 END) as pages_unprocessed
                FROM pages
            ),
            chunk_stats AS (
                SELECT
                    COUNT(*) as total_chunks,
                    COUNT(DISTINCT url) as unique_chunk_urls
                FROM chunks
            )
            SELECT
                p.total_pages,
                c.total_chunks,
                c.unique_chunk_urls,
                p.pages_with_content,
                p.pages_processed,
                p.pages_unprocessed,
                ROUND((p.pages_with_content::float / NULLIF(p.total_pages, 0) * 100)::numeric, 2) as content_percentage,
                ROUND((p.pages_processed::float / NULLIF(p.pages_with_content, 0) * 100)::numeric, 2) as processing_percentage
            FROM page_stats p, chunk_stats c
        """)

        # 精简数据转换 - 添加处理状态统计
        return JSONResponse({
            "success": True,
            "data": {
                "pages_count": result.get("total_pages", 0),
                "chunks_count": result.get("total_chunks", 0),
                "unique_chunk_urls": result.get("unique_chunk_urls", 0),
                "pages_with_content": result.get("pages_with_content", 0),
                "pages_processed": result.get("pages_processed", 0),
                "pages_unprocessed": result.get("pages_unprocessed", 0),
                "content_percentage": f"{safe_float(result.get('content_percentage', 0)):.2f}",
                "processing_percentage": f"{safe_float(result.get('processing_percentage', 0)):.2f}"
            }
        })

    except Exception:
        # 精简错误响应 - 添加处理状态字段
        return JSONResponse({
            "success": False,
            "error": APIErrorType.DATABASE_ERROR.value,
            "data": {
                "pages_count": 0,
                "chunks_count": 0,
                "unique_chunk_urls": 0,
                "pages_with_content": 0,
                "pages_processed": 0,
                "pages_unprocessed": 0,
                "content_percentage": "0.00",
                "processing_percentage": "0.00"
            }
        }, status_code=500)


@app.get("/")
async def root():
    """根路径 - API信息"""
    return {
        "message": "Database Viewer API - 现代化重构版本",
        "version": "2.0.0",
        "description": "高性能数据库查看器API，采用连接池管理和安全查询",
        "docs": "/docs",
        "endpoints": {
            "pages": "/api/pages",
            "chunks": "/api/chunks",
            "stats": "/api/stats"
        }
    }


if __name__ == "__main__":
    print("🚀 启动现代化数据库查看器API...")
    print(f"📊 API地址: http://localhost:{APIConfig.PORT}")
    print(f"📖 API文档: http://localhost:{APIConfig.PORT}/docs")
    print("✨ 现代化特性: 连接池管理、安全查询、性能优化")

    uvicorn.run(
        "api:app",
        host=APIConfig.HOST,
        port=APIConfig.PORT,
        reload=True,
        log_level="info"
    )
