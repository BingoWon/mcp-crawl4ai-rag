#!/bin/bash

# ============================================================================
# VPS HNSW 索引创建执行脚本
# 在 VPS 上直接运行，使用 localhost 连接
# ============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_progress() {
    echo -e "${GREEN}[PROGRESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 进度监控函数
show_progress_bar() {
    local current=$1
    local total=$2
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    
    printf "\r["
    for ((i=0; i<filled; i++)); do printf "█"; done
    for ((i=filled; i<width; i++)); do printf "░"; done
    printf "] %d%% (%d/%d)" "$percentage" "$current" "$total"
}

# 实时监控索引创建进度 - 增强版
monitor_index_progress() {
    local log_file="$1"
    local psql_pid="$2"
    local start_time=$(date +%s)
    local last_log_size=0
    local consecutive_no_progress=0

    log_progress "开始监控索引创建进度..."

    while true; do
        # 检查psql进程是否还在运行（使用PID而不是进程名匹配）
        if ! kill -0 "$psql_pid" 2>/dev/null; then
            log_info "检测到psql进程已结束 (PID: $psql_pid)"
            break
        fi

        # 当前时间和运行时长
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        local hours=$((elapsed / 3600))
        local minutes=$(((elapsed % 3600) / 60))
        local seconds=$((elapsed % 60))

        # 检查数据库连接和活动查询
        local db_status="连接失败"
        local active_queries="0"
        local index_exists="未知"

        # 尝试连接数据库获取详细状态
        if db_result=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
            SELECT
                COUNT(*) FILTER (WHERE state = 'active' AND (query ILIKE '%CREATE INDEX%' OR query ILIKE '%hnsw%')) as active_queries,
                CASE WHEN EXISTS(SELECT 1 FROM pg_indexes WHERE tablename = 'chunks' AND indexname = 'idx_chunks_embedding_hnsw')
                     THEN '已存在' ELSE '创建中' END as index_status
        " 2>/dev/null); then
            db_status="连接正常"
            active_queries=$(echo "$db_result" | awk '{print $1}')
            index_exists=$(echo "$db_result" | awk '{print $2}')
        fi

        # 检查系统资源使用（兼容Linux系统）
        local cpu_usage="N/A"
        local mem_usage="N/A"

        # Linux系统资源监控
        if command -v top >/dev/null 2>&1 && command -v free >/dev/null 2>&1; then
            cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//' 2>/dev/null || echo "N/A")
            mem_usage=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}' 2>/dev/null || echo "N/A")
        fi

        # 检查日志文件变化
        local log_status="无日志"
        local current_log_size=0
        if [ -f "$log_file" ]; then
            current_log_size=$(wc -l < "$log_file" 2>/dev/null || echo "0")
            if [ "$current_log_size" -gt "$last_log_size" ]; then
                log_status="日志更新"
                consecutive_no_progress=0
                last_log_size=$current_log_size
            else
                consecutive_no_progress=$((consecutive_no_progress + 1))
                log_status="无新日志(${consecutive_no_progress})"
            fi

            # 检查日志中的完成信号
            local last_lines=$(tail -5 "$log_file" 2>/dev/null)
            if [[ "$last_lines" == *"Index creation completed"* ]] || [[ "$last_lines" == *"HNSW Index Creation Process Completed"* ]]; then
                echo -e "\n${GREEN}[PROGRESS]${NC} 检测到索引创建完成信号！"
                break
            fi
        fi

        # 显示详细进度信息（每行显示，不覆盖）
        echo "${GREEN}[PROGRESS]${NC} $(date '+%H:%M:%S') | 运行时长: ${hours}h${minutes}m${seconds}s"
        echo "  数据库: $db_status | 活动查询: $active_queries | 索引状态: $index_exists"
        echo "  系统: CPU ${cpu_usage}% | 内存 ${mem_usage}% | 日志: $log_status (${current_log_size}行)"

        # 如果索引已存在，说明创建完成
        if [[ "$index_exists" == "已存在" ]]; then
            echo -e "${GREEN}[PROGRESS]${NC} 检测到索引已创建完成！"
            break
        fi

        # 如果长时间没有进度且没有活动查询，可能出现问题
        if [ "$consecutive_no_progress" -gt 30 ] && [ "$active_queries" -eq 0 ]; then
            echo -e "${YELLOW}[WARNING]${NC} 长时间无进度且无活动查询，可能出现问题"
            echo "  建议检查错误日志: $ERROR_LOG"
        fi

        echo "----------------------------------------"
        sleep 10
    done

    echo ""  # 换行
}

# 阶段性进度显示
show_stage_progress() {
    local stage="$1"
    local message="$2"
    local stage_num="$3"
    local total_stages="$4"
    
    echo ""
    echo "============================================================================"
    printf "${BLUE}[阶段 %d/%d]${NC} %s\n" "$stage_num" "$total_stages" "$stage"
    echo "============================================================================"
    log_progress "$message"
    echo ""
}

# 获取数据库信息用于进度估算
get_database_info() {
    log_info "获取数据库信息用于进度估算..."
    
    local total_chunks=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM chunks;" 2>/dev/null | tr -d ' ')
    local embedding_chunks=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL;" 2>/dev/null | tr -d ' ')
    
    log_info "数据库统计: 总记录 ${total_chunks} 条，有embedding ${embedding_chunks} 条"
    
    # 基于数据量估算时间（每10万条约1小时）
    local estimated_hours=$((embedding_chunks / 100000 + 1))
    if [ "$estimated_hours" -gt 6 ]; then
        estimated_hours=6
    fi
    
    log_info "预估索引创建时间: ${estimated_hours}-$((estimated_hours + 2)) 小时"
    
    # 设置全局变量供其他函数使用
    TOTAL_CHUNKS="$total_chunks"
    EMBEDDING_CHUNKS="$embedding_chunks"
    ESTIMATED_HOURS="$estimated_hours"
}

# ============================================================================
# 数据库配置 - VPS 本地连接
# ============================================================================

DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="apple_rag_db"
DB_USER="apple_rag_user"
DB_PASSWORD="${DB_PASSWORD:-}"  # 从环境变量读取，避免硬编码

# ============================================================================
# 检查环境
# ============================================================================

show_stage_progress "环境检查" "开始 VPS HNSW 索引创建流程" 1 7

# 检查是否在持久会话中
if [ -n "$STY" ]; then
    log_success "检测到 screen 会话: $STY"
elif [ -n "$TMUX" ]; then
    log_success "检测到 tmux 会话"
else
    log_warning "未检测到持久会话，强烈建议使用 screen 或 tmux"
    echo "建议运行: screen -S hnsw_index"
    read -p "是否继续？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "用户取消操作"
        exit 0
    fi
fi

# 检查 psql 是否可用
if ! command -v psql &> /dev/null; then
    log_error "psql 命令未找到，请安装 PostgreSQL 客户端"
    log_info "Ubuntu/Debian: sudo apt install postgresql-client"
    log_info "CentOS/RHEL: sudo yum install postgresql"
    exit 1
fi

log_success "环境检查完成"

# ============================================================================
# 测试数据库连接
# ============================================================================

show_stage_progress "数据库连接测试" "验证数据库连接和获取统计信息" 2 7

# 测试连接
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    log_success "数据库连接测试成功"
    
    # 获取数据库信息用于进度估算
    get_database_info
else
    log_error "数据库连接失败，请检查："
    log_error "1. PostgreSQL 服务是否运行: sudo systemctl status postgresql"
    log_error "2. 数据库配置是否正确"
    log_error "3. 用户权限是否正确"
    exit 1
fi

# ============================================================================
# 检查系统资源
# ============================================================================

show_stage_progress "系统资源检查" "评估内存、磁盘和CPU资源" 3 7

# 检查内存
TOTAL_MEM=$(free -m | awk 'NR==2{printf "%.0f", $2}')
AVAILABLE_MEM=$(free -m | awk 'NR==2{printf "%.0f", $7}')

log_info "系统内存: ${TOTAL_MEM}MB 总计, ${AVAILABLE_MEM}MB 可用"

if [ "$AVAILABLE_MEM" -lt 3000 ]; then
    log_warning "可用内存不足 3GB，索引创建可能较慢或失败"
    log_warning "建议释放一些内存或调整参数"
fi

# 检查磁盘空间
DISK_AVAILABLE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
log_info "磁盘可用空间: ${DISK_AVAILABLE}GB"

if [ "$DISK_AVAILABLE" -lt 5 ]; then
    log_warning "磁盘可用空间不足 5GB，可能无法完成索引创建"
    log_warning "索引预计占用 2-3GB 空间"
fi

# ============================================================================
# 创建日志目录和文件
# ============================================================================

show_stage_progress "日志准备" "创建日志目录和文件" 4 7

LOG_DIR="hnsw_logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG_FILE="$LOG_DIR/hnsw_creation_$TIMESTAMP.log"
ERROR_LOG="$LOG_DIR/hnsw_error_$TIMESTAMP.log"

log_info "日志文件: $LOG_FILE"
log_info "错误日志: $ERROR_LOG"

# ============================================================================
# 执行索引创建
# ============================================================================

show_stage_progress "索引创建准备" "启动索引创建进程" 5 7

log_warning "预估时间: ${ESTIMATED_HOURS}-$((ESTIMATED_HOURS + 2)) 小时"
log_warning "数据量: ${EMBEDDING_CHUNKS} 条记录需要建立索引"
log_info "建议操作: 使用 Ctrl+A D 分离screen会话，稍后重连查看"

# 显示开始时间
START_TIME=$(date)
log_info "开始时间: $START_TIME"

# 在后台执行 SQL 脚本并监控进度
{
    PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -f "vps_create_hnsw.sql" \
        -v ON_ERROR_STOP=1 \
        --echo-queries \
        > "$LOG_FILE" 2> "$ERROR_LOG"
    echo $? > /tmp/psql_exit_code
} &

# 获取 psql 进程ID
PSQL_PID=$!

show_stage_progress "索引创建监控" "实时监控索引创建进度" 6 7

# 启动进度监控（传递psql进程ID）
monitor_index_progress "$LOG_FILE" "$PSQL_PID"

# 等待 psql 进程完成
wait $PSQL_PID
EXIT_CODE=$(cat /tmp/psql_exit_code 2>/dev/null || echo "1")
rm -f /tmp/psql_exit_code

# 显示结束时间和详细状态
END_TIME=$(date)
log_info "结束时间: $END_TIME"

# 分析日志文件内容
if [ -f "$LOG_FILE" ]; then
    log_info "分析日志文件内容..."
    local log_lines=$(wc -l < "$LOG_FILE")
    log_info "日志文件总行数: $log_lines"

    # 显示日志文件的最后几行
    log_info "日志文件最后10行:"
    tail -10 "$LOG_FILE" | while IFS= read -r line; do
        log_info "  $line"
    done
fi

# 检查错误日志
if [ -f "$ERROR_LOG" ] && [ -s "$ERROR_LOG" ]; then
    log_warning "发现错误日志内容:"
    cat "$ERROR_LOG" | while IFS= read -r line; do
        log_error "  $line"
    done
fi

# ============================================================================
# 检查结果
# ============================================================================

show_stage_progress "结果验证" "验证索引创建结果" 7 7

if [ $EXIT_CODE -eq 0 ]; then
    log_success "🎉 HNSW 索引创建完成！"
    
    # 验证索引
    log_info "验证索引创建结果..."
    PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -c "SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) as size FROM pg_indexes WHERE tablename = 'chunks' AND indexname = 'idx_chunks_embedding_hnsw';"
    
    log_success "索引创建流程全部完成！"
    log_info "详细日志保存在: $LOG_FILE"
    
    # 显示后续建议
    echo ""
    log_info "=== 后续建议 ==="
    log_info "1. 测试向量搜索性能"
    log_info "2. 监控查询执行计划"
    log_info "3. 考虑备份数据库"
    log_info "4. 观察索引使用统计"
    
else
    log_error "HNSW 索引创建失败，退出码: $EXIT_CODE"
    log_error "错误日志保存在: $ERROR_LOG"
    
    if [ -s "$ERROR_LOG" ]; then
        log_error "最近的错误信息:"
        tail -10 "$ERROR_LOG"
    fi
    
    exit $EXIT_CODE
fi

log_success "VPS HNSW 索引创建流程完成！"
