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

# ============================================================================
# 数据库配置 - VPS 本地连接
# ============================================================================

DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="apple_rag_db"
DB_USER="apple_rag_user"
DB_PASSWORD="REDACTED_PASSWORD"

# ============================================================================
# 检查环境
# ============================================================================

log_info "开始 VPS HNSW 索引创建流程"

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

log_info "测试数据库连接..."

# 测试连接
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    log_success "数据库连接测试成功"
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

log_info "检查系统资源..."

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

log_info "开始执行 HNSW 索引创建..."
log_warning "此过程可能需要 2-6 小时，请保持连接稳定"

# 显示开始时间
START_TIME=$(date)
log_info "开始时间: $START_TIME"

# 执行 SQL 脚本
PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f "vps_create_hnsw.sql" \
    -v ON_ERROR_STOP=1 \
    --echo-queries \
    > "$LOG_FILE" 2> "$ERROR_LOG"

EXIT_CODE=$?

# 显示结束时间
END_TIME=$(date)
log_info "结束时间: $END_TIME"

# ============================================================================
# 检查结果
# ============================================================================

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
