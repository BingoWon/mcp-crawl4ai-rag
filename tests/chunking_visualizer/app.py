"""Chunking Visualizer FastAPI Application"""

import sys
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from chunking import SmartChunker, ChunkingStrategy

app = FastAPI()
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


class ChunkRequest(BaseModel):
    text: str
    chunk_size: int = 5000

class ChunkResponse(BaseModel):
    chunks: List[Dict[str, Any]]
    strategy: Dict[str, Any]
    stats: Dict[str, Any]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "strategy": ChunkingStrategy.get_strategy_info()
    })


@app.post("/api/chunk", response_model=ChunkResponse)
async def chunk_text(request: ChunkRequest):
    """文本分块 API"""
    if not request.text.strip():
        return ChunkResponse(
            chunks=[],
            strategy=ChunkingStrategy.get_strategy_info(),
            stats={"total_chunks": 0, "total_chars": 0, "avg_chunk_size": 0}
        )
    
    # 创建分块器并处理文本
    chunker = SmartChunker(request.chunk_size)
    chunk_infos = chunker.chunk_text(request.text)
    
    # 构建响应数据
    chunks = []
    for chunk_info in chunk_infos:
        chunks.append({
            "content": chunk_info.content,
            "start_pos": chunk_info.start_pos,
            "end_pos": chunk_info.end_pos,
            "break_type": chunk_info.break_type.value,
            "chunk_index": chunk_info.chunk_index,
            "size": len(chunk_info.content)
        })
    
    # 计算统计信息
    total_chars = sum(chunk["size"] for chunk in chunks)
    avg_chunk_size = total_chars // len(chunks) if chunks else 0
    
    # 分割类型统计
    break_type_stats = {}
    for chunk in chunks:
        break_type = chunk["break_type"]
        break_type_stats[break_type] = break_type_stats.get(break_type, 0) + 1
    
    stats = {
        "total_chunks": len(chunks),
        "total_chars": total_chars,
        "avg_chunk_size": avg_chunk_size,
        "break_type_stats": break_type_stats
    }
    
    return ChunkResponse(
        chunks=chunks,
        strategy=ChunkingStrategy.get_strategy_info(),
        stats=stats
    )


@app.post("/chunk", response_class=HTMLResponse)
async def chunk_form(request: Request, text: str = Form(...), chunk_size: int = Form(5000)):
    """表单提交处理（用于非 JS 环境）"""
    chunk_request = ChunkRequest(text=text, chunk_size=chunk_size)
    result = await chunk_text(chunk_request)
    
    strategy_info = ChunkingStrategy.get_strategy_info()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "strategy": strategy_info,
        "chunks": result.chunks,
        "stats": result.stats,
        "input_text": text,
        "chunk_size": chunk_size
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
