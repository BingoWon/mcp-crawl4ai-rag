#!/bin/bash

# ============================================================================
# 数据库索引管理脚本
# 功能：创建索引、检查状态、监控进度
# ============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_progress() { echo -e "${GREEN}[PROGRESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }

# 数据库配置
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="apple_rag_db"
DB_USER="apple_rag_user"
DB_PASSWORD="${DB_PASSWORD:-}"

# 实时监控索引创建进度
monitor_index_progress() {
    local log_file="$1"
    local psql_pid="$2"
    local start_time=$(date +%s)

    log_progress "开始监控索引创建进度..."

    while kill -0 "$psql_pid" 2>/dev/null; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        local hours=$((elapsed / 3600))
        local minutes=$(((elapsed % 3600) / 60))
        local seconds=$((elapsed % 60))

        # 检查数据库状态
        local db_status="连接失败"
        local active_queries="0"
        local fulltext_exists="未知"
        local hnsw_exists="未知"

        if db_result=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
            SELECT
                COUNT(*) FILTER (WHERE state = 'active' AND query ILIKE '%CREATE INDEX%') as active_queries,
                CASE WHEN EXISTS(SELECT 1 FROM pg_indexes WHERE tablename = 'chunks' AND indexname = 'idx_chunks_fulltext')
                     THEN '已存在' ELSE '创建中' END as fulltext_status,
                CASE WHEN EXISTS(SELECT 1 FROM pg_indexes WHERE tablename = 'chunks' AND indexname = 'idx_chunks_embedding_hnsw')
                     THEN '已存在' ELSE '创建中' END as hnsw_status
        " 2>/dev/null); then
            db_status="连接正常"
            active_queries=$(echo "$db_result" | awk '{print $1}')
            fulltext_exists=$(echo "$db_result" | awk '{print $2}')
            hnsw_exists=$(echo "$db_result" | awk '{print $3}')
        fi

        # 显示进度
        echo "${GREEN}[PROGRESS]${NC} $(date '+%H:%M:%S') | 运行时长: ${hours}h${minutes}m${seconds}s"
        echo "  数据库: $db_status | 活动查询: $active_queries"
        echo "  Fulltext索引: $fulltext_exists | HNSW索引: $hnsw_exists"

        # 检查是否完成
        if [[ "$fulltext_exists" == "已存在" ]] && [[ "$hnsw_exists" == "已存在" ]]; then
            echo -e "${GREEN}[PROGRESS]${NC} 所有索引创建完成！"
            break
        fi

        echo "----------------------------------------"
        sleep 10
    done
}

# 创建索引
create_indexes() {
    log_info "开始创建索引流程..."

    # 检查持久会话
    if [ -z "$STY" ] && [ -z "$TMUX" ]; then
        log_warning "未检测到持久会话，强烈建议使用 screen 或 tmux"
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 0
    fi

    # 测试数据库连接
    log_info "测试数据库连接..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        log_error "数据库连接失败"
        exit 1
    fi
    log_success "数据库连接成功"

    # 获取数据量
    local total_chunks=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM chunks;" 2>/dev/null | tr -d ' ')
    local embedding_chunks=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL;" 2>/dev/null | tr -d ' ')
    
    log_info "数据量: 总记录 ${total_chunks} 条，有embedding ${embedding_chunks} 条"
    log_warning "预估时间: Fulltext 10-20分钟 + HNSW 2-6小时"

    # 创建日志目录
    local log_dir="index_logs"
    mkdir -p "$log_dir"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local log_file="$log_dir/creation_$timestamp.log"
    local error_log="$log_dir/error_$timestamp.log"

    log_info "日志文件: $log_file"

    # 执行索引创建
    {
        PGPASSWORD="$DB_PASSWORD" psql \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            -f "create_indexes.sql" \
            -v ON_ERROR_STOP=1 \
            --echo-queries \
            > "$log_file" 2> "$error_log"
        echo $? > /tmp/psql_exit_code
    } &

    local psql_pid=$!
    monitor_index_progress "$log_file" "$psql_pid"
    wait $psql_pid

    local exit_code=$(cat /tmp/psql_exit_code 2>/dev/null || echo "1")
    rm -f /tmp/psql_exit_code

    if [ $exit_code -eq 0 ]; then
        log_success "🎉 所有索引创建完成！"
        log_info "详细日志: $log_file"
    else
        log_error "索引创建失败，退出码: $exit_code"
        log_error "错误日志: $error_log"
        exit $exit_code
    fi
}

# 检查索引状态
check_indexes() {
    log_info "检查索引状态..."

    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
SELECT '=== Chunks Table Indexes ===' as header;

SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size,
    CASE 
        WHEN indexdef ILIKE '%hnsw%' THEN 'HNSW Vector'
        WHEN indexdef ILIKE '%gin%' AND indexdef ILIKE '%to_tsvector%' THEN 'Fulltext Search'
        WHEN indexdef ILIKE '%btree%' THEN 'B-tree'
        ELSE 'Other'
    END as type
FROM pg_indexes 
WHERE tablename = 'chunks'
ORDER BY indexname;

SELECT '=== Index Status ===' as header;

SELECT 
    CASE WHEN EXISTS(SELECT 1 FROM pg_indexes WHERE tablename = 'chunks' AND indexname = 'idx_chunks_fulltext')
         THEN '✅ Fulltext index exists' ELSE '❌ Fulltext index missing' END as fulltext_status,
    CASE WHEN EXISTS(SELECT 1 FROM pg_indexes WHERE tablename = 'chunks' AND indexname = 'idx_chunks_embedding_hnsw')
         THEN '✅ HNSW index exists' ELSE '❌ HNSW index missing' END as hnsw_status;
EOF
}

# 主菜单
show_menu() {
    echo ""
    echo "============================================================================"
    echo "                    数据库索引管理"
    echo "============================================================================"
    echo "1) 创建所有索引（Fulltext + HNSW）"
    echo "2) 检查索引状态"
    echo "3) 退出"
    echo "============================================================================"
    read -p "请选择操作 [1-3]: " choice

    case $choice in
        1) create_indexes ;;
        2) check_indexes ;;
        3) log_info "退出"; exit 0 ;;
        *) log_error "无效选择"; show_menu ;;
    esac
}

# 主程序
if [ $# -eq 0 ]; then
    show_menu
else
    case "$1" in
        create) create_indexes ;;
        check) check_indexes ;;
        *) log_error "用法: $0 [create|check]"; exit 1 ;;
    esac
fi

