#!/bin/bash

# =============================================================================
# Continuous Crawler 启动脚本
# =============================================================================
# 功能：
# 1. 自动更新代码 (git pull)
# 2. 激活虚拟环境
# 3. 启动 continuous_crawler.py
# 4. 错误处理和日志记录
# =============================================================================

# 配置参数
PROJECT_DIR="/usr/mcp-crawl4ai-rag"
VENV_PATH="$PROJECT_DIR/.venv"
PYTHON_SCRIPT="$PROJECT_DIR/tools/continuous_crawler.py"
LOG_DIR="/var/log/crawler"

# 创建日志目录
mkdir -p $LOG_DIR

# 日志函数
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_DIR/startup.log
}

# 错误处理函数
error_exit() {
    log "ERROR: $1"
    exit 1
}

# 开始执行
log "========================================="
log "Starting Continuous Crawler Service"
log "========================================="

# 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    error_exit "Project directory not found: $PROJECT_DIR"
fi

# 进入项目目录
cd $PROJECT_DIR || error_exit "Cannot change to project directory: $PROJECT_DIR"
log "Changed to project directory: $PROJECT_DIR"

# 更新代码
log "Updating code from git repository..."
if git pull; then
    log "Git pull completed successfully"
else
    error_exit "Git pull failed"
fi

# 检查虚拟环境
if [ ! -d "$VENV_PATH" ]; then
    error_exit "Virtual environment not found: $VENV_PATH"
fi

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    error_exit "Virtual environment activation script not found"
fi

# 激活虚拟环境
log "Activating virtual environment..."
source $VENV_PATH/bin/activate || error_exit "Failed to activate virtual environment"
log "Virtual environment activated successfully"

# 检查Python脚本
if [ ! -f "$PYTHON_SCRIPT" ]; then
    error_exit "Python script not found: $PYTHON_SCRIPT"
fi

# 设置环境变量
export PYTHONPATH="$PROJECT_DIR/src"
export PYTHONUNBUFFERED=1

# 启动程序
log "Starting continuous crawler..."
log "Python script: $PYTHON_SCRIPT"
log "PYTHONPATH: $PYTHONPATH"
log "========================================="

# 使用exec替换当前进程，确保信号正确传递
exec python tools/continuous_crawler.py
