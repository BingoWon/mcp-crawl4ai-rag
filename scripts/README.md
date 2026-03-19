# Database Index Management

## Quick Start

### One-command from local machine (recommended)
```bash
# Create all indexes (auto SSH + screen + nohup + sync + load password)
./scripts/rebuild_indexes_remote.sh

# Check index status
./scripts/rebuild_indexes_remote.sh check

# Reattach to running screen session
./scripts/rebuild_indexes_remote.sh attach

# Tail latest creation log
./scripts/rebuild_indexes_remote.sh logs
```

The script automatically:
1. Tests SSH connection (via `apple-rag` in `~/.ssh/config`)
2. Syncs latest scripts to VPS
3. Verifies `.env` exists on VPS with database password
4. Starts a screen + nohup session (survives SSH disconnect AND screen crash)
5. Loads all database config from `.env` — no manual `export` needed

### Run directly on VPS
```bash
cd /root/mcp-crawl4ai-rag
scripts/run_indexes.sh create   # password auto-loaded from .env
scripts/run_indexes.sh check    # check index status
```

---

## Index Types

### 1. Fulltext Search Index
**Purpose**: exact match for technical terms
- Name: `idx_chunks_fulltext`
- Type: GIN index
- Config: PostgreSQL 'simple' (no stemming — good for code/API names)
- Size: ~80-100 MB
- Creation time: 10-20 minutes

**Use cases**: `@State`, `SecItemAdd`, `iOS 26 beta`, API names, release notes

**Query example**:
```sql
SELECT id, url, title, content
FROM chunks
WHERE to_tsvector('simple', COALESCE(title, '') || ' ' || content)
      @@ plainto_tsquery('simple', 'SwiftUI')
LIMIT 5;
```

### 2. HNSW Vector Index
**Purpose**: semantic similarity search
- Name: `idx_chunks_embedding_hnsw`
- Type: HNSW vector index
- Dimensions: halfvec(2560)
- Size: ~2.7 GB
- Creation time: 2-6 hours

**Use cases**: semantic search, similar document lookup, hybrid search

**Query example**:
```sql
SELECT id, url, content,
       1 - (embedding <=> $1::halfvec) as similarity
FROM chunks
WHERE embedding IS NOT NULL
ORDER BY embedding <=> $1::halfvec
LIMIT 5;
```

---

## Usage Scenarios

### Scenario 1: Rebuild indexes from local
```bash
./scripts/rebuild_indexes_remote.sh

# Monitor progress
./scripts/rebuild_indexes_remote.sh attach   # or: ssh apple-rag -t 'screen -r indexes'
# Detach: Ctrl+A, D
```

### Scenario 2: Check index status
```bash
./scripts/rebuild_indexes_remote.sh check
```

### Scenario 3: View logs remotely
```bash
./scripts/rebuild_indexes_remote.sh logs
```

---

## System Requirements

### Hardware
- **RAM**: at least 3GB available
- **Disk**: at least 5GB free space
- **CPU**: 4 cores recommended

### Software
- PostgreSQL client (psql)
- screen (on VPS)

---

## Performance

### Fulltext Search
- With index: 5-10 ms
- Without: 80-100 ms (full table scan)
- Improvement: 10-20x

### HNSW Vector Search
- With index: 5-20 ms
- Without: several seconds (full table scan)
- Improvement: 100x+

---

## Configuration

### Database Connection
Scripts auto-load all config from project `.env`:
```bash
CLOUD_DB_HOST=75.127.7.212    # defaults to localhost on VPS
CLOUD_DB_PORT=5432
CLOUD_DB_DATABASE=apple_rag_db
CLOUD_DB_USER=apple_rag_user
CLOUD_DB_PASSWORD=***         # auto-loaded, no manual export
```

### Index Creation Parameters
Tuning parameters in `create_indexes.sql`:
```sql
SET maintenance_work_mem = '3GB';
SET max_parallel_maintenance_workers = 4;
SET work_mem = '512MB';
```

**Adjustments**:
- Low memory: reduce `maintenance_work_mem` to `1GB`
- Few CPU cores: reduce `max_parallel_maintenance_workers` to `2`

---

## Troubleshooting

### Problem 1: Database connection failed
```bash
sudo systemctl status postgresql
sudo systemctl start postgresql
psql -h localhost -U apple_rag_user -d apple_rag_db
```

### Problem 2: Out of memory
Reduce parameters in `create_indexes.sql`:
```sql
SET maintenance_work_mem = '1GB';
SET max_parallel_maintenance_workers = 2;
```

### Problem 3: Disk space
```bash
df -h
# Ensure at least 5GB free
```

### Problem 4: Process terminated unexpectedly
```bash
# Reattach to screen
./scripts/rebuild_indexes_remote.sh attach

# Check logs
./scripts/rebuild_indexes_remote.sh logs

# Re-run (auto-cleans old indexes)
./scripts/rebuild_indexes_remote.sh
```

---

## Log Files

### Location
```
index_logs/
├── creation_YYYYMMDD_HHMMSS.log  # creation log
└── error_YYYYMMDD_HHMMSS.log     # error log
```

### View logs
```bash
# From local machine
./scripts/rebuild_indexes_remote.sh logs

# On VPS directly
tail -f index_logs/creation_*.log
cat index_logs/error_*.log
```

---

## Best Practices

### 1. Connection Resilience
The remote script uses **screen + nohup** double protection:
- `screen`: allows reattaching to see live output
- `nohup`: ensures process survives even if screen crashes

### 2. Creation Order
Optimized order: Fulltext first (fast), HNSW second (slow).
If HNSW fails, Fulltext is already available.

### 3. Partial Success Reporting
On failure, the script reports which indexes were successfully created
and which are missing — no need to guess.

### 4. Verify After Creation
```bash
./scripts/rebuild_indexes_remote.sh check
```

---

## References

### PostgreSQL Full Text Search
- [PostgreSQL Full Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [GIN Indexes](https://www.postgresql.org/docs/current/gin.html)

### pgvector HNSW
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [HNSW Algorithm](https://arxiv.org/abs/1603.09320)

---

## Version History

### v3.1 (current)
- Fixed: monitoring query crash when index doesn't exist yet
- Fixed: exit code capture failure under `set -e`
- Fixed: psql output parsing (now uses proper `|` delimiter)
- Added: nohup inside screen for double SSH-disconnect protection
- Added: `attach` and `logs` subcommands
- Added: .env verification on VPS before running
- Added: partial success reporting on failure
- Improved: connection method cached (no repeated probe per query)
- Improved: all DB config loaded from .env (not just password)

### v3.0
- One-command remote execution (`rebuild_indexes_remote.sh`)
- Auto-load database password from `.env`
- Auto-sync scripts to VPS
- Auto-manage screen session

### v2.0
- Combined Fulltext + HNSW index creation
- Optimized creation order (fast index first)
- Precise index deletion (exact name match)
- Unified progress monitoring

---

**Doc version**: v3.1
**Last updated**: 2026-03-19
