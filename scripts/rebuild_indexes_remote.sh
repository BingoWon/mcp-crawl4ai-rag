#!/bin/bash

# ============================================================================
# Remote Index Rebuild - one-command execution from local machine
#
# Usage:
#   ./scripts/rebuild_indexes_remote.sh              # create indexes (default)
#   ./scripts/rebuild_indexes_remote.sh check         # check index status
#   ./scripts/rebuild_indexes_remote.sh create        # create indexes
#   ./scripts/rebuild_indexes_remote.sh logs          # tail latest creation log
#   ./scripts/rebuild_indexes_remote.sh attach        # reattach to screen session
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SSH_HOST="${SSH_HOST:-apple-rag}"
REMOTE_PROJECT="${REMOTE_PROJECT:-/root/mcp-crawl4ai-rag}"
SCREEN_NAME="indexes"

ACTION="create"

for arg in "$@"; do
    case "$arg" in
        check)  ACTION="check" ;;
        create) ACTION="create" ;;
        logs)   ACTION="logs" ;;
        attach) ACTION="attach" ;;
        -h|--help)
            echo "Usage: $0 [create|check|logs|attach]"
            echo ""
            echo "  create    Create all indexes in screen session (default)"
            echo "  check     Check current index status"
            echo "  logs      Tail the latest creation log on VPS"
            echo "  attach    Reattach to the running screen session"
            exit 0
            ;;
        *) echo -e "${RED}Unknown argument: $arg${NC}"; exit 1 ;;
    esac
done

echo -e "${BLUE}[INFO]${NC} Target: ssh ${SSH_HOST} -> ${REMOTE_PROJECT}"
echo -e "${BLUE}[INFO]${NC} Action: ${ACTION}"

# --------------------------------------------------------------------------
# SSH connectivity check
# --------------------------------------------------------------------------
echo -e "${BLUE}[INFO]${NC} Testing SSH connection..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$SSH_HOST" "echo ok" > /dev/null 2>&1; then
    echo -e "${RED}[ERROR]${NC} Cannot connect to ${SSH_HOST}"
    echo "Check SSH config: ~/.ssh/config"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} SSH connected"

# --------------------------------------------------------------------------
# Quick actions that don't need file sync
# --------------------------------------------------------------------------
if [ "$ACTION" = "attach" ]; then
    echo -e "${BLUE}[INFO]${NC} Attaching to screen session '${SCREEN_NAME}'..."
    exec ssh -t "$SSH_HOST" "screen -r ${SCREEN_NAME} || echo 'No active session found'"
fi

if [ "$ACTION" = "logs" ]; then
    echo -e "${BLUE}[INFO]${NC} Tailing latest creation log..."
    ssh -t "$SSH_HOST" "ls -t ${REMOTE_PROJECT}/index_logs/creation_*.log 2>/dev/null | head -1 | xargs tail -50 || echo 'No logs found'"
    exit 0
fi

# --------------------------------------------------------------------------
# Sync scripts to VPS
# --------------------------------------------------------------------------
echo -e "${BLUE}[INFO]${NC} Syncing scripts to VPS..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ssh "$SSH_HOST" "mkdir -p ${REMOTE_PROJECT}/scripts"
scp -q "$SCRIPT_DIR/run_indexes.sh" "$SCRIPT_DIR/create_indexes.sql" \
    "${SSH_HOST}:${REMOTE_PROJECT}/scripts/"
ssh "$SSH_HOST" "chmod +x ${REMOTE_PROJECT}/scripts/run_indexes.sh"
echo -e "${GREEN}[OK]${NC} Scripts synced"

# --------------------------------------------------------------------------
# Verify .env exists on VPS with database password
# --------------------------------------------------------------------------
echo -e "${BLUE}[INFO]${NC} Verifying .env on VPS..."
ENV_CHECK=$(ssh "$SSH_HOST" "
    if [ ! -f ${REMOTE_PROJECT}/.env ]; then
        echo 'MISSING'
    elif ! grep -q '^CLOUD_DB_PASSWORD=.' ${REMOTE_PROJECT}/.env; then
        echo 'NO_PASSWORD'
    else
        echo 'OK'
    fi
")

case "$ENV_CHECK" in
    MISSING)
        echo -e "${RED}[ERROR]${NC} .env file not found on VPS at ${REMOTE_PROJECT}/.env"
        echo "Copy your local .env to VPS first:"
        echo "  scp .env ${SSH_HOST}:${REMOTE_PROJECT}/.env"
        exit 1
        ;;
    NO_PASSWORD)
        echo -e "${RED}[ERROR]${NC} CLOUD_DB_PASSWORD not set in ${REMOTE_PROJECT}/.env"
        exit 1
        ;;
    OK)
        echo -e "${GREEN}[OK]${NC} .env verified"
        ;;
esac

# --------------------------------------------------------------------------
# Check index status
# --------------------------------------------------------------------------
if [ "$ACTION" = "check" ]; then
    echo -e "${BLUE}[INFO]${NC} Checking index status..."
    ssh -t "$SSH_HOST" "cd ${REMOTE_PROJECT} && scripts/run_indexes.sh check"
    exit 0
fi

# --------------------------------------------------------------------------
# Create indexes in screen + nohup for double protection
# --------------------------------------------------------------------------
echo -e "${YELLOW}[INFO]${NC} Starting index creation in screen session '${SCREEN_NAME}'..."
echo ""

# Kill existing session if any
ssh "$SSH_HOST" "screen -S ${SCREEN_NAME} -X quit 2>/dev/null; true"

# nohup inside screen: even if screen dies, the process survives
ssh "$SSH_HOST" "screen -dmS ${SCREEN_NAME} bash -c '
    cd ${REMOTE_PROJECT}
    nohup scripts/run_indexes.sh create &
    NOHUP_PID=\$!
    wait \$NOHUP_PID
    echo \"\"
    echo \"========================================\"
    echo \"  Index creation finished (exit: \$?)\"
    echo \"  Press Enter to close this session\"
    echo \"========================================\"
    read
'"

sleep 2

if ssh "$SSH_HOST" "screen -ls 2>/dev/null | grep -q ${SCREEN_NAME}"; then
    echo -e "${GREEN}[OK]${NC} Screen session started"
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "  Index creation running on VPS"
    echo ""
    echo -e "  Attach:  ${GREEN}$0 attach${NC}"
    echo -e "  Detach:  press ${YELLOW}Ctrl+A, D${NC}"
    echo -e "  Status:  ${GREEN}$0 check${NC}"
    echo -e "  Logs:    ${GREEN}$0 logs${NC}"
    echo -e "${BLUE}========================================${NC}"
else
    echo -e "${RED}[ERROR]${NC} Screen session failed to start"
    echo "Check VPS manually: ssh ${SSH_HOST}"
    exit 1
fi
