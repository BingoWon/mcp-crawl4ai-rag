# 数据库索引管理

## 📋 快速开始

### 创建所有索引
```bash
# 1. SSH + Screen
ssh user@198.12.70.36
screen -S indexes

# 2. 复制脚本
nano create_indexes.sql    # 复制 SQL 内容
nano run_indexes.sh        # 复制 Shell 内容
chmod +x run_indexes.sh

# 3. 设置密码并执行
export DB_PASSWORD="XXX"
./run_indexes.sh create

# 4. 分离会话（可选）
Ctrl+A, D  # 分离
screen -r indexes  # 重连
```

### 检查索引状态
```bash
export DB_PASSWORD="your_password"
./run_indexes.sh check
```

---

## 📊 索引类型说明

### 1. Fulltext 全文搜索索引
**用途**: 技术术语精确匹配搜索
- 索引名: `idx_chunks_fulltext`
- 类型: GIN 索引
- 配置: PostgreSQL 'simple' 配置
- 大小: ~80-100 MB
- 创建时间: 10-20 分钟

**适用场景**:
- 搜索技术术语（`@State`, `SecItemAdd`）
- 搜索 API 函数名
- 搜索版本信息（`iOS 26 beta`）
- 搜索发布说明

**查询示例**:
```sql
SELECT id, url, title, content
FROM chunks
WHERE to_tsvector('simple', COALESCE(title, '') || ' ' || content)
      @@ plainto_tsquery('simple', 'SwiftUI')
LIMIT 5;
```

### 2. HNSW 向量索引
**用途**: 语义相似度搜索
- 索引名: `idx_chunks_embedding_hnsw`
- 类型: HNSW 向量索引
- 向量维度: halfvec(2560)
- 大小: ~2.7 GB
- 创建时间: 2-6 小时

**适用场景**:
- 语义搜索
- 相似文档查找
- 混合搜索（与 Fulltext 结合）

**查询示例**:
```sql
SELECT id, url, content,
       1 - (embedding <=> $1::halfvec) as similarity
FROM chunks
WHERE embedding IS NOT NULL
ORDER BY embedding <=> $1::halfvec
LIMIT 5;
```

---

## 🎯 使用场景

### 场景 1: 首次创建索引
```bash
# 使用交互式菜单
./run_indexes.sh

# 选择: 1) 创建所有索引
```

### 场景 2: 检查索引状态
```bash
# 直接执行检查
./run_indexes.sh check
```

### 场景 3: 重新创建索引
```bash
# 脚本会自动删除旧索引并重新创建
./run_indexes.sh create
```

---

## ⚙️ 系统要求

### 硬件要求
- **内存**: 至少 3GB 可用内存
- **磁盘**: 至少 5GB 可用空间
- **CPU**: 4核推荐

### 软件要求
- PostgreSQL 客户端（psql）
- Screen 或 Tmux（推荐）

---

## 📈 性能数据

### Fulltext 搜索性能
- 查询时间: 5-10 ms（使用索引）
- 无索引时间: 80-100 ms（全表扫描）
- 性能提升: 10-20 倍

### HNSW 向量搜索性能
- 查询时间: 5-20 ms（使用索引）
- 无索引时间: 数秒（全表扫描）
- 性能提升: 100+ 倍

---

## 🔧 配置说明

### 数据库连接配置
脚本中的默认配置：
```bash
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="apple_rag_db"
DB_USER="apple_rag_user"
```

### 索引创建参数
SQL 脚本中的优化参数：
```sql
SET maintenance_work_mem = '3GB';
SET max_parallel_maintenance_workers = 4;
SET work_mem = '512MB';
```

**调整建议**:
- 内存不足时，降低 `maintenance_work_mem` 到 `1GB`
- CPU 核心少时，降低 `max_parallel_maintenance_workers` 到 `2`

---

## 🚨 故障排除

### 问题 1: 数据库连接失败
```bash
# 检查 PostgreSQL 服务
sudo systemctl status postgresql

# 启动服务
sudo systemctl start postgresql

# 检查连接
psql -h localhost -U apple_rag_user -d apple_rag_db
```

### 问题 2: 内存不足
**症状**: 索引创建失败，错误日志显示内存不足

**解决方案**:
修改 `create_indexes.sql` 中的参数：
```sql
SET maintenance_work_mem = '1GB';  -- 降低到 1GB
SET max_parallel_maintenance_workers = 2;  -- 降低到 2
```

### 问题 3: 磁盘空间不足
**症状**: 索引创建失败，错误日志显示磁盘空间不足

**解决方案**:
```bash
# 检查磁盘空间
df -h

# 清理不必要的文件
# 确保至少有 5GB 可用空间
```

### 问题 4: 进程意外终止
```bash
# 重新连接 screen 会话
screen -r indexes

# 查看错误日志
tail -50 index_logs/error_*.log

# 重新运行（会自动清理旧索引）
./run_indexes.sh create
```

---

## 📝 日志文件

### 日志位置
```
index_logs/
├── creation_YYYYMMDD_HHMMSS.log  # 创建日志
└── error_YYYYMMDD_HHMMSS.log     # 错误日志
```

### 查看日志
```bash
# 查看最新创建日志
tail -f index_logs/creation_*.log

# 查看错误日志
cat index_logs/error_*.log
```

---

## 🎓 最佳实践

### 1. 使用持久会话
**必须**在 screen 或 tmux 中运行，避免网络中断导致索引创建失败。

### 2. 监控进度
脚本会自动显示实时进度，包括：
- 运行时长
- 活动查询数
- 索引创建状态

### 3. 创建顺序
脚本已优化创建顺序：
1. 先创建 Fulltext 索引（快，10-20分钟）
2. 再创建 HNSW 索引（慢，2-6小时）

这样即使 HNSW 失败，Fulltext 索引也已创建完成。

### 4. 验证索引
创建完成后，使用检查命令验证：
```bash
./run_indexes.sh check
```

---

## 📚 参考资料

### PostgreSQL 全文搜索
- [PostgreSQL Full Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [GIN Indexes](https://www.postgresql.org/docs/current/gin.html)

### pgvector HNSW
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [HNSW Algorithm](https://arxiv.org/abs/1603.09320)

---

## 🔄 版本历史

### v2.0 (当前版本)
- ✅ 整合 Fulltext + HNSW 索引创建
- ✅ 优化创建顺序（快速索引优先）
- ✅ 精确索引删除逻辑（避免误删）
- ✅ 统一的进度监控
- ✅ 简化文件结构（3个文件）

### v1.0 (已废弃)
- 分离的 HNSW 索引创建脚本
- 无 Fulltext 索引支持

---

**文档版本**: v2.0  
**最后更新**: 2025-10-09

