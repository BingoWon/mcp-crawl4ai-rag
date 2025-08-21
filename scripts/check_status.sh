#!/bin/bash

# ============================================================================
# 检查 HNSW 索引状态脚本
# ============================================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 数据库配置
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="apple_rag_db"
DB_USER="apple_rag_user"
DB_PASSWORD="${DB_PASSWORD:-}"  # 从环境变量读取，避免硬编码

echo "============================================================================"
echo "🔍 HNSW 索引状态检查"
echo "============================================================================"

# 检查日志文件
echo -e "${BLUE}📋 检查最新的日志文件...${NC}"
if [ -d "hnsw_logs" ]; then
    LATEST_LOG=$(ls -t hnsw_logs/hnsw_creation_*.log 2>/dev/null | head -1)
    LATEST_ERROR=$(ls -t hnsw_logs/hnsw_error_*.log 2>/dev/null | head -1)
    
    if [ -n "$LATEST_LOG" ]; then
        echo "📄 最新日志文件: $LATEST_LOG"
        echo "📏 日志文件大小: $(du -h "$LATEST_LOG" | cut -f1)"
        echo ""
        echo "📖 日志文件最后 10 行:"
        tail -10 "$LATEST_LOG"
        echo ""
    fi
    
    if [ -n "$LATEST_ERROR" ] && [ -s "$LATEST_ERROR" ]; then
        echo -e "${RED}❌ 发现错误日志: $LATEST_ERROR${NC}"
        echo "🔍 错误日志内容:"
        cat "$LATEST_ERROR"
        echo ""
    fi
else
    echo "📁 未找到 hnsw_logs 目录"
fi

echo "============================================================================"
echo -e "${BLUE}🔍 检查数据库索引状态...${NC}"

# 执行数据库检查
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "check_index_status.sql"

echo ""
echo "============================================================================"
echo -e "${BLUE}🖥️  检查系统资源...${NC}"

# 检查内存使用
echo "💾 内存使用情况:"
free -h

echo ""
echo "💽 磁盘使用情况:"
df -h

echo ""
echo "⚡ CPU 使用情况:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//'

echo ""
echo "🔄 PostgreSQL 进程:"
ps aux | grep postgres | grep -v grep

echo ""
echo "============================================================================"
echo -e "${BLUE}🔍 检查正在运行的索引创建进程...${NC}"

# 检查是否有正在运行的索引创建
ACTIVE_INDEX=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT COUNT(*) FROM pg_stat_activity 
WHERE state = 'active' 
AND (query ILIKE '%CREATE INDEX%' OR query ILIKE '%hnsw%');")

if [ "$ACTIVE_INDEX" -gt 0 ]; then
    echo -e "${YELLOW}🔄 发现 $ACTIVE_INDEX 个正在运行的索引创建进程${NC}"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT 
        pid,
        usename,
        state,
        NOW() - query_start as duration,
        LEFT(query, 100) as query_preview
    FROM pg_stat_activity 
    WHERE state = 'active' 
    AND (query ILIKE '%CREATE INDEX%' OR query ILIKE '%hnsw%');"
else
    echo "📋 没有发现正在运行的索引创建进程"
fi

echo ""
echo "============================================================================"
echo -e "${GREEN}✅ 检查完成${NC}"
echo ""
echo "🔍 如果需要查看完整的诊断信息，请查看上面的输出"
echo "📋 如果索引创建失败，请检查错误日志文件"
echo "🔄 如果索引正在创建中，请耐心等待或使用 Ctrl+A, D 分离 screen 会话"
