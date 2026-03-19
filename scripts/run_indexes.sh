#!/bin/bash

# ============================================================================
# Database Index Management Script
# Functions: create indexes, check status, monitor progress
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()     { echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_success()  { echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_warning()  { echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_error()    { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_progress() { echo -e "${GREEN}[PROGRESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }

# --------------------------------------------------------------------------
# Load config from .env
# --------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR%/scripts}"
ENV_FILE="$PROJECT_ROOT/.env"

load_env_var() {
    local var_name="$1"
    local default="$2"
    local value
    if [ -f "$ENV_FILE" ]; then
        value=$(grep -E "^${var_name}=" "$ENV_FILE" | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    fi
    echo "${value:-$default}"
}

DB_HOST=$(load_env_var "CLOUD_DB_HOST" "localhost")
DB_PORT=$(load_env_var "CLOUD_DB_PORT" "5432")
DB_NAME=$(load_env_var "CLOUD_DB_DATABASE" "apple_rag_db")
DB_USER=$(load_env_var "CLOUD_DB_USER" "apple_rag_user")
DB_PASSWORD="${DB_PASSWORD:-$(load_env_var "CLOUD_DB_PASSWORD" "")}"
DOCKER_CONTAINER="postgres_db"

if [ -n "$DB_PASSWORD" ] && [ -f "$ENV_FILE" ]; then
    log_info "Loaded database config from .env"
fi

# --------------------------------------------------------------------------
# Connection detection (cached)
# --------------------------------------------------------------------------
CACHED_CONNECTION_METHOD=""

detect_db_connection_method() {
    if [ -n "$CACHED_CONNECTION_METHOD" ]; then
        echo "$CACHED_CONNECTION_METHOD"
        return
    fi

    if docker ps 2>/dev/null | grep -q "$DOCKER_CONTAINER"; then
        CACHED_CONNECTION_METHOD="docker"
    elif PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        CACHED_CONNECTION_METHOD="direct"
    else
        CACHED_CONNECTION_METHOD="unknown"
    fi
    echo "$CACHED_CONNECTION_METHOD"
}

execute_db_query() {
    local query="$1"
    local method
    method=$(detect_db_connection_method)

    case "$method" in
        docker)
            docker exec "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -A -F'|' -c "$query" 2>/dev/null
            ;;
        direct)
            PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A -F'|' -c "$query" 2>/dev/null
            ;;
        *)
            return 1
            ;;
    esac
}

# --------------------------------------------------------------------------
# Monitor index creation progress
# --------------------------------------------------------------------------
monitor_index_progress() {
    local psql_pid="$1"
    local start_time
    start_time=$(date +%s)
    local method
    method=$(detect_db_connection_method)

    log_progress "Monitoring index creation (connection: $method)..."

    while kill -0 "$psql_pid" 2>/dev/null; do
        local now elapsed hours minutes seconds
        now=$(date +%s)
        elapsed=$((now - start_time))
        hours=$((elapsed / 3600))
        minutes=$(((elapsed % 3600) / 60))
        seconds=$((elapsed % 60))

        local db_ok=false
        local active_queries="?"
        local fulltext_status="?"
        local hnsw_status="?"
        local hnsw_size="-"

        # Safe query: avoids ::regclass cast that throws when index missing
        if db_result=$(execute_db_query "
            SELECT
                (SELECT COUNT(*) FROM pg_stat_activity
                 WHERE datname = current_database()
                   AND state = 'active'
                   AND query ILIKE '%CREATE INDEX%') as active_creates,
                CASE WHEN EXISTS(SELECT 1 FROM pg_indexes WHERE tablename='chunks' AND indexname='idx_chunks_fulltext')
                     THEN 'YES' ELSE 'NO' END as ft,
                CASE WHEN EXISTS(SELECT 1 FROM pg_indexes WHERE tablename='chunks' AND indexname='idx_chunks_embedding_hnsw')
                     THEN 'YES' ELSE 'NO' END as hnsw,
                COALESCE((SELECT pg_size_pretty(pg_relation_size(c.oid))
                          FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                          WHERE c.relname='idx_chunks_embedding_hnsw' AND n.nspname='public'), '-') as hnsw_sz
        " 2>/dev/null); then
            db_ok=true
            active_queries=$(echo "$db_result" | head -1 | awk -F'|' '{gsub(/^ +| +$/,"",$1); print $1}')
            fulltext_status=$(echo "$db_result" | head -1 | awk -F'|' '{gsub(/^ +| +$/,"",$2); print $2}')
            hnsw_status=$(echo "$db_result" | head -1 | awk -F'|' '{gsub(/^ +| +$/,"",$3); print $3}')
            hnsw_size=$(echo "$db_result" | head -1 | awk -F'|' '{gsub(/^ +| +$/,"",$4); print $4}')
        fi

        local ft_icon="🔄"
        local hnsw_icon="🔄"
        [[ "$fulltext_status" == "YES" ]] && ft_icon="✅"
        [[ "$hnsw_status" == "YES" ]] && hnsw_icon="✅"

        echo -e "${GREEN}[PROGRESS]${NC} $(date '+%H:%M:%S') | Runtime: ${hours}h${minutes}m${seconds}s"
        if [ "$db_ok" = true ]; then
            echo -e "  DB: ✅ | Active CREATE INDEX queries: $active_queries"
        else
            echo -e "  DB: ⚠️  monitor query failed (index creation still running)"
        fi
        echo -e "  Fulltext: $ft_icon | HNSW: $hnsw_icon ($hnsw_size)"

        if [[ "$fulltext_status" == "YES" ]] && [[ "$hnsw_status" == "YES" ]]; then
            echo -e "${GREEN}[PROGRESS]${NC} All indexes created!"
            break
        fi

        echo "----------------------------------------"
        sleep 15
    done
}

# --------------------------------------------------------------------------
# Create indexes
# --------------------------------------------------------------------------
create_indexes() {
    log_info "Starting index creation..."

    # Skip interactive prompt when running non-interactively (e.g. from nohup/pipe)
    if [ -z "$STY" ] && [ -z "$TMUX" ] && [ -t 0 ]; then
        log_warning "No persistent session detected (screen/tmux recommended)"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 0
    fi

    local method
    method=$(detect_db_connection_method)
    log_info "Database connection method: $method"

    if [ "$method" == "unknown" ]; then
        log_error "Cannot connect to database (tried Docker and direct)"
        log_error "  Host=$DB_HOST Port=$DB_PORT User=$DB_USER DB=$DB_NAME"
        [ -z "$DB_PASSWORD" ] && log_error "  DB_PASSWORD is empty - check .env file"
        exit 1
    fi
    log_success "Database connected ($method)"

    local total_chunks embedding_chunks
    total_chunks=$(execute_db_query "SELECT COUNT(*) FROM chunks;" | tr -d ' |')
    embedding_chunks=$(execute_db_query "SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL;" | tr -d ' |')

    log_info "Data: ${total_chunks} total chunks, ${embedding_chunks} with embeddings"
    log_warning "Estimated time: Fulltext 10-20min + HNSW 2-6 hours"

    local log_dir="$PROJECT_ROOT/index_logs"
    mkdir -p "$log_dir"
    local timestamp
    timestamp=$(date '+%Y%m%d_%H%M%S')
    local log_file="$log_dir/creation_$timestamp.log"
    local error_log="$log_dir/error_$timestamp.log"

    log_info "Log file: $log_file"

    local sql_file="$SCRIPT_DIR/create_indexes.sql"
    if [ ! -f "$sql_file" ]; then
        log_error "SQL file not found: $sql_file"
        exit 1
    fi

    local exit_code_file
    exit_code_file=$(mktemp "/tmp/psql_exit_code_$$.XXXXXX")

    # Run psql in background; disable set -e inside subshell so exit code is captured
    (
        set +e
        if [ "$method" == "docker" ]; then
            docker exec -i "$DOCKER_CONTAINER" psql \
                -U "$DB_USER" \
                -d "$DB_NAME" \
                -v ON_ERROR_STOP=1 \
                --echo-queries \
                < "$sql_file" \
                > "$log_file" 2> "$error_log"
        else
            PGPASSWORD="$DB_PASSWORD" psql \
                -h "$DB_HOST" \
                -p "$DB_PORT" \
                -U "$DB_USER" \
                -d "$DB_NAME" \
                -f "$sql_file" \
                -v ON_ERROR_STOP=1 \
                --echo-queries \
                > "$log_file" 2> "$error_log"
        fi
        echo $? > "$exit_code_file"
    ) &

    local psql_pid=$!
    monitor_index_progress "$psql_pid"
    wait $psql_pid 2>/dev/null || true

    local exit_code
    exit_code=$(cat "$exit_code_file" 2>/dev/null || echo "1")
    rm -f "$exit_code_file"

    # Check partial success even on failure
    local ft_exists hnsw_exists
    ft_exists=$(execute_db_query "SELECT CASE WHEN EXISTS(SELECT 1 FROM pg_indexes WHERE tablename='chunks' AND indexname='idx_chunks_fulltext') THEN 'YES' ELSE 'NO' END;" 2>/dev/null | tr -d ' |')
    hnsw_exists=$(execute_db_query "SELECT CASE WHEN EXISTS(SELECT 1 FROM pg_indexes WHERE tablename='chunks' AND indexname='idx_chunks_embedding_hnsw') THEN 'YES' ELSE 'NO' END;" 2>/dev/null | tr -d ' |')

    if [ "$exit_code" -eq 0 ]; then
        log_success "All indexes created successfully!"
        log_info "Log: $log_file"
    else
        log_error "Index creation failed (exit code: $exit_code)"
        log_error "Error log: $error_log"
        echo ""
        log_info "=== Partial Result ==="
        if [ "$ft_exists" = "YES" ]; then
            log_success "  Fulltext index: created successfully"
        else
            log_error "  Fulltext index: MISSING"
        fi
        if [ "$hnsw_exists" = "YES" ]; then
            log_success "  HNSW index: created successfully"
        else
            log_error "  HNSW index: MISSING"
        fi
        exit "$exit_code"
    fi
}

# --------------------------------------------------------------------------
# Check index status
# --------------------------------------------------------------------------
check_indexes() {
    log_info "Checking index status..."

    local method
    method=$(detect_db_connection_method)
    log_info "Connection method: $method"

    if [ "$method" == "unknown" ]; then
        log_error "Cannot connect to database"
        exit 1
    fi

    local query="
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
    CASE WHEN EXISTS(SELECT 1 FROM pg_indexes WHERE tablename='chunks' AND indexname='idx_chunks_fulltext')
         THEN '✅ Fulltext index exists' ELSE '❌ Fulltext index missing' END as fulltext_status,
    CASE WHEN EXISTS(SELECT 1 FROM pg_indexes WHERE tablename='chunks' AND indexname='idx_chunks_embedding_hnsw')
         THEN '✅ HNSW index exists' ELSE '❌ HNSW index missing' END as hnsw_status;
"

    if [ "$method" == "docker" ]; then
        docker exec "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "$query"
    else
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$query"
    fi
}

# --------------------------------------------------------------------------
# Interactive menu
# --------------------------------------------------------------------------
show_menu() {
    echo ""
    echo "============================================================================"
    echo "                    Database Index Management"
    echo "============================================================================"
    echo "1) Create all indexes (Fulltext + HNSW)"
    echo "2) Check index status"
    echo "3) Exit"
    echo "============================================================================"
    read -p "Select [1-3]: " choice

    case $choice in
        1) create_indexes ;;
        2) check_indexes ;;
        3) log_info "Exit"; exit 0 ;;
        *) log_error "Invalid choice"; show_menu ;;
    esac
}

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
if [ $# -eq 0 ]; then
    show_menu
else
    case "$1" in
        create) create_indexes ;;
        check)  check_indexes ;;
        *)      log_error "Usage: $0 [create|check]"; exit 1 ;;
    esac
fi
