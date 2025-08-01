#!/usr/bin/env python3
"""
通用PostgreSQL HTTP代理
现代化的FastAPI + asyncpg实现，支持任意SQL查询和基础API密钥认证
专为Cloudflare Workers设计
"""

import os
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn


# 基础配置
API_KEY = os.getenv("DATABASE_API_KEY", "ZBYlBx77H9Sc87k")


# 请求/响应模型
class QueryRequest(BaseModel):
    query: str = Field(..., description="SQL查询语句")
    params: Optional[List[Any]] = Field(default=None, description="查询参数")


class QueryResponse(BaseModel):
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    affected_rows: Optional[int] = None
    error: Optional[str] = None


class StatsResponse(BaseModel):
    total_pages: int
    total_chunks: int
    pages_with_content: int
    pages_with_content_percentage: float
    average_crawl_count: float
    database_size: str


# 简单认证函数
async def verify_api_key(api_key: str = Header(..., alias="X-API-Key")):
    """验证API密钥"""
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


# 全局连接池
pool: Optional[asyncpg.Pool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global pool
    
    # 启动时创建连接池
    database_url = (
        f"postgresql://{os.getenv('PGUSER', 'bingo')}:"
        f"{os.getenv('PGPASSWORD', 'xRdtkHIa53nYMWJ')}@"
        f"{os.getenv('PGHOST', 'localhost')}:"
        f"{os.getenv('PGPORT', '6432')}/"
        f"{os.getenv('PGDATABASE', 'crawl4ai_rag')}"
    )
    
    pool = await asyncpg.create_pool(
        database_url,
        min_size=5,
        max_size=20,
        command_timeout=30
    )
    
    yield
    
    # 关闭时清理连接池
    if pool:
        await pool.close()


# 创建FastAPI应用
app = FastAPI(
    title="PostgreSQL HTTP Gateway",
    description="现代化的PostgreSQL HTTP API网关",
    version="2.0.0",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_pool() -> asyncpg.Pool:
    """获取数据库连接池"""
    if not pool:
        raise HTTPException(status_code=503, detail="数据库连接池未初始化")
    return pool


@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        db_pool = await get_pool()
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"数据库连接失败: {str(e)}")


@app.get("/stats", response_model=StatsResponse)
async def get_stats(db_pool: asyncpg.Pool = Depends(get_pool)):
    """获取数据库统计信息"""
    try:
        async with db_pool.acquire() as conn:
            # 获取表统计
            pages_count = await conn.fetchval("SELECT COUNT(*) FROM pages")
            chunks_count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
            
            # 获取HNSW索引
            indexes = await conn.fetch("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'chunks' AND indexname LIKE '%hnsw%'
                ORDER BY indexname
            """)
            hnsw_indexes = [row['indexname'] for row in indexes]
            
            # 获取数据库大小
            db_size = await conn.fetchval("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)
            
            return StatsResponse(
                total_pages=pages_count,
                total_chunks=chunks_count,
                hnsw_indexes=hnsw_indexes,
                database_size=db_size
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    db_pool: asyncpg.Pool = Depends(get_pool),
    auth: bool = Depends(verify_api_key)
):
    """执行SQL查询"""
    try:
        async with db_pool.acquire() as conn:
            # 调试信息
            print(f"DEBUG: Query: {request.query}")
            print(f"DEBUG: Params: {request.params}")
            print(f"DEBUG: Params type: {type(request.params)}")

            # 判断查询类型
            query_upper = request.query.strip().upper()

            if query_upper.startswith('SELECT'):
                # 查询操作
                if request.params:
                    print(f"DEBUG: Executing with params: {request.params}")
                    rows = await conn.fetch(request.query, *request.params)
                else:
                    print(f"DEBUG: Executing without params")
                    rows = await conn.fetch(request.query)
                
                # 转换为字典列表
                data = [dict(row) for row in rows]
                
                return QueryResponse(
                    success=True,
                    data=data
                )
            
            else:
                # 修改操作 (INSERT, UPDATE, DELETE)
                if request.params:
                    result = await conn.execute(request.query, *request.params)
                else:
                    result = await conn.execute(request.query)
                
                # 解析影响行数
                affected_rows = 0
                if result:
                    parts = result.split()
                    if len(parts) >= 2 and parts[-1].isdigit():
                        affected_rows = int(parts[-1])
                
                return QueryResponse(
                    success=True,
                    affected_rows=affected_rows
                )
                
    except Exception as e:
        return QueryResponse(
            success=False,
            error=str(e)
        )


class BatchRequest(BaseModel):
    requests: List[QueryRequest]

@app.post("/batch", response_model=QueryResponse)
async def execute_batch(
    batch_request: BatchRequest,
    db_pool: asyncpg.Pool = Depends(get_pool),
    auth: bool = Depends(verify_api_key)
):
    """批量执行SQL查询"""
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                results = []
                total_affected = 0
                
                for req in batch_request.requests:
                    query_upper = req.query.strip().upper()
                    
                    if query_upper.startswith('SELECT'):
                        if req.params:
                            rows = await conn.fetch(req.query, *req.params)
                        else:
                            rows = await conn.fetch(req.query)
                        results.extend([dict(row) for row in rows])
                    else:
                        if req.params:
                            result = await conn.execute(req.query, *req.params)
                        else:
                            result = await conn.execute(req.query)
                        
                        if result:
                            parts = result.split()
                            if len(parts) >= 2 and parts[-1].isdigit():
                                total_affected += int(parts[-1])
                
                return QueryResponse(
                    success=True,
                    data=results if results else None,
                    affected_rows=total_affected if total_affected > 0 else None
                )
                
    except Exception as e:
        return QueryResponse(
            success=False,
            error=str(e)
        )








if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,
        access_log=True
    )
