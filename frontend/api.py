#!/usr/bin/env python3
"""
极简API接口 - 获取pages和chunks数据
"""

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.client import PostgreSQLClient

app = FastAPI(title="Database Viewer API", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/pages")
async def get_pages() -> JSONResponse:
    """获取pages表数据"""
    try:
        async with PostgreSQLClient() as client:
            pages = await client.execute_query("""
                SELECT id, url, content, crawl_count, created_at, updated_at
                FROM pages
                ORDER BY crawl_count ASC, created_at DESC
            """)

            # 格式化数据
            formatted_pages = []
            for page in pages:
                formatted_pages.append({
                    "id": str(page["id"]),
                    "url": page["url"],
                    "content": page["content"][:100] + "..." if len(page["content"]) > 100 else page["content"],
                    "full_content": page["content"],  # 完整内容
                    "crawl_count": page["crawl_count"],
                    "created_at": page["created_at"].isoformat() if page["created_at"] else None,
                    "updated_at": page["updated_at"].isoformat() if page["updated_at"] else None
                })

            return JSONResponse({
                "success": True,
                "count": len(formatted_pages),
                "data": formatted_pages
            })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "data": []
        }, status_code=500)


@app.get("/api/chunks")
async def get_chunks() -> JSONResponse:
    """获取chunks表数据"""
    try:
        async with PostgreSQLClient() as client:
            chunks = await client.execute_query("""
                SELECT id, url, content, created_at, embedding
                FROM chunks
                ORDER BY created_at DESC
            """)

            # 格式化数据
            formatted_chunks = []
            for chunk in chunks:
                # 处理embedding数据
                embedding_info = "无"
                if chunk["embedding"]:
                    try:
                        # 解析embedding字符串为数组
                        import ast
                        embedding_array = ast.literal_eval(chunk["embedding"])
                        if isinstance(embedding_array, list) and len(embedding_array) > 0:
                            embedding_info = f"向量维度: {len(embedding_array)}, 前5个值: {embedding_array[:5]}"
                    except:
                        embedding_info = "解析错误"

                formatted_chunks.append({
                    "id": str(chunk["id"]),
                    "url": chunk["url"],
                    "content": chunk["content"][:100] + "..." if len(chunk["content"]) > 100 else chunk["content"],
                    "full_content": chunk["content"],  # 完整内容
                    "created_at": chunk["created_at"].isoformat() if chunk["created_at"] else None,
                    "embedding_info": embedding_info,
                    "raw_embedding": chunk["embedding"]  # 原始embedding数据
                })

            return JSONResponse({
                "success": True,
                "count": len(formatted_chunks),
                "data": formatted_chunks
            })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "data": []
        }, status_code=500)


@app.get("/api/stats")
async def get_stats() -> JSONResponse:
    """获取统计信息"""
    try:
        async with PostgreSQLClient() as client:
            # 获取pages统计
            pages_count = await client.execute_query("SELECT COUNT(*) as count FROM pages")
            chunks_count = await client.execute_query("SELECT COUNT(*) as count FROM chunks")
            
            return JSONResponse({
                "success": True,
                "data": {
                    "pages_count": pages_count[0]["count"],
                    "chunks_count": chunks_count[0]["count"]
                }
            })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "data": {"pages_count": 0, "chunks_count": 0}
        }, status_code=500)


@app.get("/")
async def root():
    """根路径"""
    return {"message": "Database Viewer API", "version": "1.0.0"}


if __name__ == "__main__":
    print("🚀 启动数据库查看器API...")
    print("📊 API地址: http://localhost:8001")
    print("📖 API文档: http://localhost:8001/docs")
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
