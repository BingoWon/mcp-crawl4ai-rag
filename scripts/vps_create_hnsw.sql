-- ============================================================================
-- VPS HNSW 索引创建脚本 - 纯 SQL 版本
-- 在 VPS 上直接运行，使用 localhost 连接
-- ============================================================================

-- 显示开始时间
SELECT 'HNSW Index Creation Started at: ' || NOW() as start_info;

-- ============================================================================
-- 第一步：显示当前状态
-- ============================================================================

-- 显示数据库基本信息
SELECT 'Database: ' || current_database() as db_info;
SELECT 'User: ' || current_user as user_info;
SELECT 'Server Version: ' || version() as version_info;

-- 检查数据量
SELECT 
    'Total chunks: ' || COUNT(*) as total_count,
    'With embeddings: ' || COUNT(*) FILTER (WHERE embedding IS NOT NULL) as embedding_count
FROM chunks;

-- 检查表大小
SELECT 'Chunks table size: ' || pg_size_pretty(pg_total_relation_size('chunks')) as table_size;

-- ============================================================================
-- 第二步：删除现有向量索引
-- ============================================================================

SELECT 'Step 2: Checking and removing existing vector indexes...' as step_info;

-- 显示现有向量索引
SELECT 'Existing vector indexes:' as index_info;
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_indexes 
WHERE tablename = 'chunks' 
AND (indexdef ILIKE '%hnsw%' OR indexdef ILIKE '%ivfflat%' OR indexdef ILIKE '%vector%')
AND indexname != 'chunks_pkey';

-- 删除现有向量索引
DO $$
DECLARE
    index_record RECORD;
    index_count INTEGER := 0;
BEGIN
    -- 查找并删除现有的向量索引
    FOR index_record IN 
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'chunks' 
        AND (indexdef ILIKE '%hnsw%' OR indexdef ILIKE '%ivfflat%' OR indexdef ILIKE '%vector%')
        AND indexname != 'chunks_pkey'
    LOOP
        RAISE NOTICE 'Dropping existing vector index: %', index_record.indexname;
        EXECUTE 'DROP INDEX IF EXISTS ' || index_record.indexname;
        index_count := index_count + 1;
    END LOOP;
    
    IF index_count = 0 THEN
        RAISE NOTICE 'No existing vector indexes found';
    ELSE
        RAISE NOTICE 'Dropped % vector indexes', index_count;
    END IF;
END $$;

-- ============================================================================
-- 第三步：优化数据库参数
-- ============================================================================

SELECT 'Step 3: Optimizing database parameters...' as step_info;

-- 显示当前参数
SELECT 'Current parameters:' as param_info;
SELECT 'maintenance_work_mem: ' || current_setting('maintenance_work_mem') as current_param;
SELECT 'max_parallel_maintenance_workers: ' || current_setting('max_parallel_maintenance_workers') as current_param;
SELECT 'work_mem: ' || current_setting('work_mem') as current_param;

-- 设置优化参数（针对 4核6GB VPS）
SET maintenance_work_mem = '4GB';
SET max_parallel_maintenance_workers = 4;
SET work_mem = '512MB';
SET random_page_cost = 1.1;

-- 确认参数设置
SELECT 'Optimized parameters:' as param_info;
SELECT 'maintenance_work_mem: ' || current_setting('maintenance_work_mem') as optimized_param;
SELECT 'max_parallel_maintenance_workers: ' || current_setting('max_parallel_maintenance_workers') as optimized_param;
SELECT 'work_mem: ' || current_setting('work_mem') as optimized_param;

-- ============================================================================
-- 第四步：创建 HNSW 索引
-- ============================================================================

SELECT 'Step 4: Creating HNSW index...' as step_info;
SELECT 'WARNING: This process may take 2-6 hours for 447K records' as warning_info;
SELECT 'Index creation started at: ' || NOW() as index_start_time;

-- 创建 HNSW 索引
-- 使用 halfvec_cosine_ops 因为我们的 embedding 是 halfvec(2560) 类型
CREATE INDEX CONCURRENTLY idx_chunks_embedding_hnsw
ON chunks USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 16, ef_construction = 64);

SELECT 'Index creation completed at: ' || NOW() as index_end_time;

-- ============================================================================
-- 第五步：验证索引创建结果
-- ============================================================================

SELECT 'Step 5: Verifying index creation...' as step_info;

-- 检查索引是否创建成功
SELECT 
    'Index created: ' || indexname as creation_result,
    'Index size: ' || pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size,
    'Index definition: ' || indexdef as index_def
FROM pg_indexes 
WHERE tablename = 'chunks' 
AND indexname = 'idx_chunks_embedding_hnsw';

-- 检查索引统计信息
SELECT 
    'Index statistics for: ' || indexname as stats_info,
    'Tuples read: ' || COALESCE(idx_tup_read::text, '0') as tup_read,
    'Tuples fetched: ' || COALESCE(idx_tup_fetch::text, '0') as tup_fetch
FROM pg_stat_user_indexes 
WHERE indexname = 'idx_chunks_embedding_hnsw';

-- ============================================================================
-- 第六步：性能测试
-- ============================================================================

SELECT 'Step 6: Performance testing...' as step_info;

-- 执行向量相似度搜索测试
WITH test_vector AS (
    SELECT embedding FROM chunks WHERE embedding IS NOT NULL LIMIT 1
)
SELECT 
    'Performance test completed' as test_info,
    'Sample results:' as results_header;

-- 实际搜索测试
WITH test_vector AS (
    SELECT embedding FROM chunks WHERE embedding IS NOT NULL LIMIT 1
)
SELECT 
    id,
    LEFT(url, 50) || '...' as url_preview,
    ROUND((1 - (embedding <=> (SELECT embedding FROM test_vector)))::numeric, 4) as similarity
FROM chunks
WHERE embedding IS NOT NULL
ORDER BY embedding <=> (SELECT embedding FROM test_vector)
LIMIT 5;

-- ============================================================================
-- 完成信息
-- ============================================================================

SELECT 'HNSW Index Creation Process Completed Successfully!' as completion_info;
SELECT 'Completion time: ' || NOW() as completion_time;

-- 显示所有 chunks 表的索引
SELECT 'All indexes on chunks table:' as final_info;
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size,
    CASE 
        WHEN indexdef ILIKE '%hnsw%' THEN 'HNSW Vector Index'
        WHEN indexdef ILIKE '%btree%' THEN 'B-tree Index'
        ELSE 'Other Index'
    END as index_type
FROM pg_indexes 
WHERE tablename = 'chunks'
ORDER BY indexname;

-- 显示建议
SELECT '=== POST-CREATION RECOMMENDATIONS ===' as recommendations;
SELECT '1. Monitor query performance improvements' as recommendation;
SELECT '2. Consider database backup after successful index creation' as recommendation;
SELECT '3. Monitor index usage with pg_stat_user_indexes' as recommendation;
SELECT '4. Test vector similarity searches in your application' as recommendation;
