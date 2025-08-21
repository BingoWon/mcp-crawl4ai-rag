-- ============================================================================
-- 检查 HNSW 索引状态脚本
-- 用于诊断索引创建是否成功以及当前状态
-- ============================================================================

-- 显示当前时间
SELECT 'Index Status Check at: ' || NOW() as check_time;

-- ============================================================================
-- 第一步：检查数据库基本状态
-- ============================================================================

SELECT 'Database: ' || current_database() as db_info;
SELECT 'User: ' || current_user as user_info;

-- 检查 chunks 表数据量
SELECT 
    'Total chunks: ' || COUNT(*) as total_count,
    'With embeddings: ' || COUNT(*) FILTER (WHERE embedding IS NOT NULL) as embedding_count,
    'Percentage with embeddings: ' || ROUND(100.0 * COUNT(*) FILTER (WHERE embedding IS NOT NULL) / COUNT(*), 2) || '%' as embedding_percentage
FROM chunks;

-- ============================================================================
-- 第二步：检查所有索引状态
-- ============================================================================

SELECT 'All indexes on chunks table:' as index_header;

SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size,
    CASE 
        WHEN indexdef ILIKE '%hnsw%' THEN 'HNSW Vector Index'
        WHEN indexdef ILIKE '%ivfflat%' THEN 'IVFFlat Vector Index'
        WHEN indexdef ILIKE '%btree%' THEN 'B-tree Index'
        ELSE 'Other Index'
    END as index_type,
    indexdef as index_definition
FROM pg_indexes 
WHERE tablename = 'chunks'
ORDER BY indexname;

-- ============================================================================
-- 第三步：专门检查 HNSW 索引
-- ============================================================================

SELECT 'HNSW Index Status:' as hnsw_header;

-- 检查是否存在 HNSW 索引
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN 'HNSW index EXISTS'
        ELSE 'HNSW index NOT FOUND'
    END as hnsw_status,
    COUNT(*) as hnsw_count
FROM pg_indexes 
WHERE tablename = 'chunks' 
AND indexname = 'idx_chunks_embedding_hnsw';

-- 如果存在，显示详细信息
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size,
    indexdef as definition
FROM pg_indexes 
WHERE tablename = 'chunks' 
AND indexname = 'idx_chunks_embedding_hnsw';

-- ============================================================================
-- 第四步：检查正在进行的索引创建
-- ============================================================================

SELECT 'Active index creation processes:' as active_header;

-- 查看正在运行的索引创建查询
SELECT 
    pid,
    usename,
    application_name,
    state,
    query_start,
    NOW() - query_start as duration,
    LEFT(query, 150) as query_preview
FROM pg_stat_activity 
WHERE state = 'active' 
AND (query ILIKE '%CREATE INDEX%' OR query ILIKE '%hnsw%')
ORDER BY query_start;

-- 如果没有活动的索引创建
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN 'No active index creation processes found'
        ELSE COUNT(*)::text || ' active index creation processes'
    END as active_status
FROM pg_stat_activity 
WHERE state = 'active' 
AND (query ILIKE '%CREATE INDEX%' OR query ILIKE '%hnsw%');

-- ============================================================================
-- 第五步：检查索引使用统计
-- ============================================================================

SELECT 'Index usage statistics:' as stats_header;

SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan
FROM pg_stat_user_indexes 
WHERE tablename = 'chunks'
ORDER BY indexname;

-- ============================================================================
-- 第六步：检查锁状态
-- ============================================================================

SELECT 'Lock information:' as lock_header;

-- 检查 chunks 表上的锁
SELECT 
    l.locktype,
    l.mode,
    l.granted,
    a.usename,
    a.query_start,
    LEFT(a.query, 100) as query_preview
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
JOIN pg_class c ON l.relation = c.oid
WHERE c.relname = 'chunks'
ORDER BY l.granted, a.query_start;

-- ============================================================================
-- 第七步：测试向量搜索（如果索引存在）
-- ============================================================================

-- 只有在 HNSW 索引存在时才执行测试
DO $$
DECLARE
    index_exists BOOLEAN;
    test_result TEXT;
BEGIN
    -- 检查索引是否存在
    SELECT EXISTS(
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'chunks' 
        AND indexname = 'idx_chunks_embedding_hnsw'
    ) INTO index_exists;
    
    IF index_exists THEN
        RAISE NOTICE 'HNSW index exists, performing search test...';
        
        -- 执行简单的向量搜索测试
        PERFORM id FROM chunks 
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> (SELECT embedding FROM chunks WHERE embedding IS NOT NULL LIMIT 1)
        LIMIT 1;
        
        RAISE NOTICE 'Vector search test completed successfully';
    ELSE
        RAISE NOTICE 'HNSW index does not exist, skipping search test';
    END IF;
END $$;

-- ============================================================================
-- 第八步：系统资源信息
-- ============================================================================

SELECT 'Database size information:' as size_header;

-- 数据库大小
SELECT 
    'Database size: ' || pg_size_pretty(pg_database_size(current_database())) as db_size;

-- chunks 表大小
SELECT 
    'Chunks table size: ' || pg_size_pretty(pg_total_relation_size('chunks')) as table_size;

-- 所有索引总大小
SELECT 
    'Total index size on chunks: ' || pg_size_pretty(SUM(pg_relation_size(indexname::regclass))) as total_index_size
FROM pg_indexes 
WHERE tablename = 'chunks';

-- ============================================================================
-- 诊断建议
-- ============================================================================

SELECT '=== DIAGNOSTIC SUMMARY ===' as summary_header;

-- 基于检查结果给出建议
SELECT 
    CASE 
        WHEN EXISTS(SELECT 1 FROM pg_indexes WHERE tablename = 'chunks' AND indexname = 'idx_chunks_embedding_hnsw') 
        THEN '✅ HNSW index exists and appears to be created successfully'
        WHEN EXISTS(SELECT 1 FROM pg_stat_activity WHERE query ILIKE '%CREATE INDEX%hnsw%' AND state = 'active')
        THEN '🔄 HNSW index creation is currently in progress'
        ELSE '❌ HNSW index not found and no active creation process detected'
    END as diagnosis;

SELECT '=== NEXT STEPS ===' as next_steps_header;
SELECT 'Check the error log file for detailed information about any failures' as step1;
SELECT 'Review system memory and disk space availability' as step2;
SELECT 'Consider adjusting PostgreSQL parameters if memory is insufficient' as step3;
