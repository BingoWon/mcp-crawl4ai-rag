#!/usr/bin/env python3
"""
极简API接口 - 获取pages和chunks数据
"""

import sys
import ast
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
async def get_pages(page: int = 1, size: int = 50, search: str = "",
                   sort: str = "crawl_count", order: str = "asc") -> JSONResponse:
    """获取pages表数据（分页）"""
    try:
        async with PostgreSQLClient() as client:
            # 构建查询条件
            where_clause = ""
            params = []
            if search:
                where_clause = "WHERE url ILIKE $1 OR content ILIKE $1"
                params.append(f"%{search}%")

            # 构建排序
            valid_sorts = ["id", "url", "crawl_count", "created_at", "updated_at"]
            sort_column = sort if sort in valid_sorts else "crawl_count"
            sort_order = "ASC" if order.lower() == "asc" else "DESC"

            # 计算分页
            offset = (page - 1) * size

            # 获取总数
            count_query = f"SELECT COUNT(*) as total FROM pages {where_clause}"
            total_result = await client.fetch_all(count_query, *params)
            total = total_result[0]["total"]

            # 获取分页数据
            limit_param = len(params) + 1
            offset_param = len(params) + 2
            query = f"""
                SELECT id, url, content, crawl_count, created_at, updated_at
                FROM pages {where_clause}
                ORDER BY {sort_column} {sort_order}
                LIMIT ${limit_param} OFFSET ${offset_param}
            """
            params.extend([size, offset])
            pages = await client.fetch_all(query, *params)

            # 格式化数据
            formatted_pages = []
            for page in pages:
                # 简化URL显示
                display_url = page["url"]
                if display_url.startswith("https://developer.apple.com/documentation"):
                    display_url = display_url.replace("https://developer.apple.com/documentation", "...")

                formatted_pages.append({
                    "id": page["id"],  # 数据库层已处理UUID序列化
                    "url": display_url,
                    "full_url": page["url"],  # 完整URL
                    "content": page["content"][:100] + "..." if len(page["content"]) > 100 else page["content"],
                    "full_content": page["content"],  # 完整内容
                    "crawl_count": page["crawl_count"],
                    "created_at": page["created_at"],  # 数据库层已转换为ISO格式
                    "updated_at": page["updated_at"]  # 数据库层已转换为ISO格式
                })

            return JSONResponse({
                "success": True,
                "data": formatted_pages,
                "pagination": {
                    "page": page,  # FastAPI已确保是整数
                    "size": size,  # FastAPI已确保是整数
                    "total": total,
                    "pages": (total + size - 1) // size
                }
            })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "data": []
        }, status_code=500)


@app.get("/api/chunks")
async def get_chunks(page: int = 1, size: int = 50, search: str = "",
                    page_id: str = "", sort: str = "created_at", order: str = "desc") -> JSONResponse:
    """获取chunks表数据（分页）"""
    try:
        async with PostgreSQLClient() as client:
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

            # 构建排序
            valid_sorts = ["id", "url", "created_at"]
            sort_column = sort if sort in valid_sorts else "created_at"
            sort_order = "ASC" if order.lower() == "asc" else "DESC"

            # 计算分页
            offset = (page - 1) * size

            # 获取总数
            count_query = f"SELECT COUNT(*) as total FROM chunks {where_clause}"
            total_result = await client.fetch_all(count_query, *params)
            total = total_result[0]["total"]

            # 获取分页数据
            limit_param = len(params) + 1
            offset_param = len(params) + 2
            query = f"""
                SELECT id, url, content, created_at, embedding
                FROM chunks {where_clause}
                ORDER BY {sort_column} {sort_order}
                LIMIT ${limit_param} OFFSET ${offset_param}
            """
            params.extend([size, offset])
            chunks = await client.fetch_all(query, *params)

            # 格式化数据
            formatted_chunks = []
            for chunk in chunks:
                # 简化URL显示
                display_url = chunk["url"]
                if display_url.startswith("https://developer.apple.com/documentation"):
                    display_url = display_url.replace("https://developer.apple.com/documentation", "...")

                # 处理embedding数据 - 直接显示前5个值
                embedding_info = "无"
                if chunk["embedding"]:
                    try:
                        import ast
                        embedding_array = ast.literal_eval(chunk["embedding"])
                        if isinstance(embedding_array, list) and len(embedding_array) > 0:
                            # 直接显示前5个值，保留4位小数
                            embedding_info = str([round(x, 4) for x in embedding_array[:5]])
                    except Exception:
                        embedding_info = "解析错误"

                formatted_chunks.append({
                    "id": chunk["id"],  # 数据库层已处理UUID序列化
                    "url": display_url,
                    "full_url": chunk["url"],  # 完整URL
                    "content": chunk["content"][:100] + "..." if len(chunk["content"]) > 100 else chunk["content"],
                    "full_content": chunk["content"],  # 完整内容
                    "created_at": chunk["created_at"],  # 数据库层已转换为ISO格式
                    "embedding_info": embedding_info,
                    "raw_embedding": str(chunk["embedding"]) if chunk["embedding"] else None
                })

            return JSONResponse({
                "success": True,
                "data": formatted_chunks,
                "pagination": {
                    "page": page,  # FastAPI已确保是整数
                    "size": size,  # FastAPI已确保是整数
                    "total": total,
                    "pages": (total + size - 1) // size
                }
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
            # 获取pages基础统计
            pages_count = await client.fetch_all("SELECT COUNT(*) as count FROM pages")
            chunks_count = await client.fetch_all("SELECT COUNT(*) as count FROM chunks")

            # 获取有content的pages统计
            pages_with_content = await client.fetch_all("""
                SELECT COUNT(*) as count FROM pages
                WHERE content IS NOT NULL AND content != ''
            """)

            # 获取平均crawl count
            avg_crawl_count = await client.fetch_all("""
                SELECT AVG(crawl_count) as avg_count FROM pages
            """)

            total_pages = pages_count[0]["count"]
            content_pages = pages_with_content[0]["count"]
            content_percentage = (content_pages / total_pages * 100) if total_pages > 0 else 0
            avg_crawl = float(avg_crawl_count[0]["avg_count"]) if avg_crawl_count[0]["avg_count"] else 0

            return JSONResponse({
                "success": True,
                "data": {
                    "pages_count": total_pages,
                    "chunks_count": chunks_count[0]["count"],
                    "pages_with_content": content_pages,
                    "content_percentage": round(content_percentage, 1),
                    "avg_crawl_count": round(avg_crawl, 2)
                }
            })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "data": {
                "pages_count": 0,
                "chunks_count": 0,
                "pages_with_content": 0,
                "content_percentage": 0,
                "avg_crawl_count": 0
            }
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
