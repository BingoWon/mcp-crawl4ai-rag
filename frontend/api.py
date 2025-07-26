#!/usr/bin/env python3
"""
Database Viewer API
数据库查看器API

提供pages和chunks数据的查询接口，支持分页、排序、搜索和统计功能。

=== 核心功能 ===

**Pages接口 (/api/pages)**
- 分页查询：支持page、size参数
- 排序功能：支持多字段排序（id、url、crawl_count、process_count、created_at、last_crawled_at）
- 搜索过滤：支持URL关键词搜索
- 统计信息：提供爬取间隔时间统计

**Chunks接口 (/api/chunks)**
- 分页查询：支持page、size参数
- 内容展示：显示chunk内容和相关URL信息

**统计接口 (/api/stats)**
- 页面统计：总数、有内容页面数、内容百分比
- 处理统计：平均爬取次数、平均处理次数（仅有内容页面）
- 精度控制：爬取和处理次数保留4位小数，百分比保留2位小数

=== 爬取间隔时间统计 ===

**计算逻辑：**
- 数据过滤：只包含crawl_count > 0的页面（已实际爬取的页面）
- 时间排序：按last_crawled_at升序排列确保时间顺序
- 间隔计算：计算相邻记录的时间差（秒）
- 平均值：所有时间间隔的算术平均值

**业务价值：**
- 排除未爬取页面：crawl_count = 0的页面只是记录等待爬取，不参与统计
- 真实性能指标：反映实际爬取操作的时间间隔
- 系统监控：帮助评估爬取频率和系统性能
"""

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.utils import get_database_client

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
async def get_pages(search: str = "", sort: str = "last_crawled_at", order: str = "desc") -> JSONResponse:
    """获取pages表数据（固定前100条）"""
    try:
        client = await get_database_client()

        # 构建查询条件
        where_clause = "WHERE last_crawled_at IS NOT NULL"
        params = []
        if search:
            where_clause += " AND (url ILIKE $1 OR content ILIKE $1)"
            params.append(f"%{search}%")

        # 构建排序 - 优雅现代精简
        valid_sorts = ["id", "url", "crawl_count", "process_count", "created_at", "last_crawled_at"]
        sort_column = sort if sort in valid_sorts else "last_crawled_at"
        sort_order = "ASC" if order.lower() == "asc" else "DESC"

        # 获取前100条数据 - 固定数量，无分页
        query = f"""
            SELECT id, url, content, crawl_count, process_count, created_at, last_crawled_at
            FROM pages {where_clause}
            ORDER BY {sort_column} {sort_order}
            LIMIT 100
        """

        if search:
            pages = await client.fetch_all(query, params[0])
        else:
            pages = await client.fetch_all(query)

        # 计算平均爬取间隔时间（只包含已爬取的页面）- 优雅现代精简
        avg_crawl_interval = None
        crawled_pages = [page for page in pages if page["crawl_count"] > 0]

        if len(crawled_pages) >= 2:
            # 按last_crawled_at排序（确保时间顺序）
            sorted_pages = sorted(crawled_pages, key=lambda x: x["last_crawled_at"])
            intervals = []

            for i in range(1, len(sorted_pages)):
                prev_time = sorted_pages[i-1]["last_crawled_at"]
                curr_time = sorted_pages[i]["last_crawled_at"]

                # 计算时间间隔（秒）
                from datetime import datetime
                if isinstance(prev_time, str):
                    prev_dt = datetime.fromisoformat(prev_time.replace('Z', '+00:00'))
                    curr_dt = datetime.fromisoformat(curr_time.replace('Z', '+00:00'))
                else:
                    prev_dt = prev_time
                    curr_dt = curr_time

                interval_seconds = (curr_dt - prev_dt).total_seconds()
                intervals.append(interval_seconds)

            # 计算平均值（intervals在此作用域内已定义）
            if intervals:
                avg_crawl_interval = sum(intervals) / len(intervals)

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
                "process_count": page["process_count"],
                "created_at": page["created_at"],  # 数据库层已转换为ISO格式
                "last_crawled_at": page["last_crawled_at"]  # 数据库层已转换为ISO格式
            })

        return JSONResponse({
            "success": True,
            "data": formatted_pages,
            "count": len(formatted_pages),
            "stats": {
                "avg_crawl_interval": f"{avg_crawl_interval:.2f}" if avg_crawl_interval else None,
                "data_count": len(crawled_pages) if 'crawled_pages' in locals() else 0
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
        client = await get_database_client()

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
        client = await get_database_client()

        # 合并所有统计查询为单个复杂查询 - 全局最优解
        stats = await client.fetch_all("""
            WITH page_stats AS (
                SELECT
                    COUNT(*) as total_pages,
                    COUNT(CASE WHEN content IS NOT NULL AND content != '' THEN 1 END) as pages_with_content,
                    AVG(crawl_count) as avg_crawl_count,
                    AVG(CASE WHEN content IS NOT NULL AND content != '' THEN process_count END) as avg_process_count,
                    COUNT(CASE WHEN crawl_count > 0 AND LENGTH(content) < 10 THEN 1 END) as anomalous_pages
                FROM pages
            ),
            chunk_stats AS (
                SELECT COUNT(*) as total_chunks FROM chunks
            )
            SELECT
                p.total_pages,
                c.total_chunks,
                p.pages_with_content,
                ROUND((p.pages_with_content::float / NULLIF(p.total_pages, 0) * 100)::numeric, 2) as content_percentage,
                ROUND(p.avg_crawl_count::numeric, 4) as avg_crawl_count,
                ROUND(p.avg_process_count::numeric, 4) as avg_process_count,
                p.anomalous_pages
            FROM page_stats p, chunk_stats c
        """)

        result = stats[0] if stats else {}

        # 转换Decimal类型为float以支持JSON序列化 - 全局最优解
        return JSONResponse({
            "success": True,
            "data": {
                "pages_count": result.get("total_pages", 0),
                "chunks_count": result.get("total_chunks", 0),
                "pages_with_content": result.get("pages_with_content", 0),
                "content_percentage": f"{float(result.get('content_percentage', 0)):.2f}",
                "avg_crawl_count": float(result.get("avg_crawl_count", 0)),
                "avg_process_count": float(result.get("avg_process_count", 0)),
                "anomalous_pages": result.get("anomalous_pages", 0)
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
                "content_percentage": "0.00",
                "avg_crawl_count": 0,
                "avg_process_count": 0,
                "anomalous_pages": 0
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
