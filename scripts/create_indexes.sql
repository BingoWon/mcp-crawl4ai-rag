-- ============================================================================
-- 数据库索引创建脚本 - 完整版
-- 包含：HNSW 向量索引 + Fulltext 全文搜索索引
-- 优化：先创建快速索引，再创建慢速索引
-- ============================================================================

SELECT 'Index Creation Started at: ' || NOW() as start_info;

-- ============================================================================
-- 第一步：显示当前状态
-- ============================================================================

SELECT 'Step 1: Checking current database status...' as step_info;

SELECT 'Database: ' || current_database() as db_info;
SELECT 'User: ' || current_user as user_info;
SELECT 'Server Version: ' || version() as version_info;

-- 检查数据量
SELECT 
    'Total chunks: ' || COUNT(*) as total_count,
    'With embeddings: ' || COUNT(*) FILTER (WHERE embedding IS NOT NULL) as embedding_count,
    'Percentage: ' || ROUND(100.0 * COUNT(*) FILTER (WHERE embedding IS NOT NULL) / COUNT(*), 2) || '%' as percentage
FROM chunks;

-- 检查表大小
SELECT 'Chunks table size: ' || pg_size_pretty(pg_total_relation_size('chunks')) as table_size;

-- ============================================================================
-- 第二步：删除现有索引（精确匹配，避免误删）
-- ============================================================================

SELECT 'Step 2: Removing existing indexes...' as step_info;

-- 显示将要删除的索引
SELECT 'Indexes to be removed:' as index_info;
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_indexes 
WHERE tablename = 'chunks' 
AND indexname IN ('idx_chunks_embedding_hnsw', 'idx_chunks_embedding_ivfflat', 'idx_chunks_fulltext');

-- 删除索引（精确匹配索引名）
DO $$
DECLARE
    index_record RECORD;
    index_count INTEGER := 0;
BEGIN
    FOR index_record IN 
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'chunks' 
        AND indexname IN ('idx_chunks_embedding_hnsw', 'idx_chunks_embedding_ivfflat', 'idx_chunks_fulltext')
    LOOP
        RAISE NOTICE 'Dropping index: %', index_record.indexname;
        EXECUTE 'DROP INDEX IF EXISTS ' || index_record.indexname;
        index_count := index_count + 1;
    END LOOP;
    
    IF index_count = 0 THEN
        RAISE NOTICE 'No existing indexes found';
    ELSE
        RAISE NOTICE 'Dropped % indexes', index_count;
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

-- 设置优化参数（针对 4核6GB VPS）
SET maintenance_work_mem = '3GB';
SET max_parallel_maintenance_workers = 4;
SET work_mem = '512MB';
SET random_page_cost = 1.1;

-- 确认参数设置
SELECT 'Optimized parameters:' as param_info;
SELECT 'maintenance_work_mem: ' || current_setting('maintenance_work_mem') as optimized_param;
SELECT 'max_parallel_maintenance_workers: ' || current_setting('max_parallel_maintenance_workers') as optimized_param;

-- ============================================================================
-- 第四步：创建 Fulltext 全文搜索索引（快速，优先创建）
-- ============================================================================

SELECT 'Step 4: Creating Fulltext search index...' as step_info;
SELECT 'Estimated time: 10-20 minutes' as time_estimate;
SELECT 'Index creation started at: ' || NOW() as index_start_time;

-- 创建 Fulltext 索引
CREATE INDEX CONCURRENTLY idx_chunks_fulltext 
ON chunks USING GIN (
  to_tsvector('simple', COALESCE(title, '') || ' ' || content)
);

SELECT 'Fulltext index creation completed at: ' || NOW() as index_end_time;

-- 验证 Fulltext 索引
SELECT 
    'Fulltext index created: ' || indexname as creation_result,
    'Index size: ' || pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_indexes 
WHERE tablename = 'chunks' 
AND indexname = 'idx_chunks_fulltext';

-- ============================================================================
-- 第五步：创建 HNSW 向量索引（慢速，后创建）
-- ============================================================================

SELECT 'Step 5: Creating HNSW vector index...' as step_info;
SELECT 'WARNING: This process may take 2-6 hours' as warning_info;
SELECT 'Index creation started at: ' || NOW() as index_start_time;

-- 创建 HNSW 索引
CREATE INDEX CONCURRENTLY idx_chunks_embedding_hnsw
ON chunks USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 16, ef_construction = 64);

SELECT 'HNSW index creation completed at: ' || NOW() as index_end_time;

-- 验证 HNSW 索引
SELECT 
    'HNSW index created: ' || indexname as creation_result,
    'Index size: ' || pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_indexes 
WHERE tablename = 'chunks' 
AND indexname = 'idx_chunks_embedding_hnsw';

-- ============================================================================
-- 第六步：性能测试
-- ============================================================================

SELECT 'Step 6: Performance testing...' as step_info;

-- 测试 Fulltext 搜索
SELECT 'Testing Fulltext search...' as test_info;
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, url, title, content
FROM chunks
WHERE to_tsvector('simple', COALESCE(title, '') || ' ' || content)
      @@ plainto_tsquery('simple', 'SwiftUI')
LIMIT 5;

-- 测试向量搜索
SELECT 'Testing vector search...' as test_info;
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

SELECT 'All Indexes Creation Completed Successfully!' as completion_info;
SELECT 'Completion time: ' || NOW() as completion_time;

-- 显示所有索引
SELECT 'All indexes on chunks table:' as final_info;
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size,
    CASE 
        WHEN indexdef ILIKE '%hnsw%' THEN 'HNSW Vector Index'
        WHEN indexdef ILIKE '%gin%' AND indexdef ILIKE '%to_tsvector%' THEN 'Fulltext Search Index'
        WHEN indexdef ILIKE '%btree%' THEN 'B-tree Index'
        ELSE 'Other Index'
    END as index_type
FROM pg_indexes 
WHERE tablename = 'chunks'
ORDER BY indexname;

-- 显示建议
SELECT '=== POST-CREATION RECOMMENDATIONS ===' as recommendations;
SELECT '1. Test search performance in your application' as recommendation;
SELECT '2. Monitor index usage with pg_stat_user_indexes' as recommendation;
SELECT '3. Consider database backup after successful index creation' as recommendation;
SELECT '4. Verify both vector and fulltext searches work correctly' as recommendation;

