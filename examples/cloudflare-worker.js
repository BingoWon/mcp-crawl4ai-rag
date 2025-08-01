/**
 * Cloudflare Workers示例代码
 * 展示如何调用通用PostgreSQL HTTP API
 */

// 配置常量
const API_BASE_URL = 'https://db.apple-rag.com';
const API_KEY = '[你的API密钥]';  // 从环境变量或配置中获取

/**
 * 发送API请求
 */
async function apiRequest(endpoint, method = 'POST', data = null) {
  const headers = {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers,
    body: data ? JSON.stringify(data) : undefined
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return await response.json();
}

/**
 * 执行SQL查询
 */
async function executeQuery(query, params = null) {
  const data = { query, params };
  const result = await apiRequest('/query', 'POST', data);

  if (!result.success) {
    throw new Error(`Query failed: ${result.error}`);
  }

  return result.data;
}

/**
 * 执行SQL命令
 */
async function executeCommand(query, params = null) {
  const data = { query, params };
  const result = await apiRequest('/execute', 'POST', data);

  if (!result.success) {
    throw new Error(`Execute failed: ${result.error}`);
  }

  return result.affected_rows;
}

/**
 * 获取待爬取的页面批次
 */
async function getPagesBatch(batchSize = 5) {
  const query = `
    UPDATE pages
    SET crawl_count = crawl_count + 1,
        last_crawled_at = NOW()
    WHERE url IN (
        SELECT url FROM pages
        ORDER BY crawl_count ASC, last_crawled_at ASC NULLS FIRST
        LIMIT $1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING url
  `;

  const results = await executeQuery(query, [batchSize]);
  return results.map(row => row.url);
}

/**
 * 创建新页面
 */
async function createPage(url) {
  const query = `
    INSERT INTO pages (url, crawl_count, content, last_crawled_at)
    VALUES ($1, 0, '', NULL)
    ON CONFLICT (url) DO NOTHING
  `;

  const affectedRows = await executeCommand(query, [url]);
  return affectedRows > 0;
}

/**
 * 获取统计信息
 */
async function getStats() {
  const response = await fetch(`${API_BASE_URL}/stats`);
  
  if (!response.ok) {
    throw new Error(`Get stats failed: ${response.status}`);
  }
  
  return await response.json();
}

/**
 * Workers主处理函数
 */
export default {
  async fetch(request, env, ctx) {
    try {
      const url = new URL(request.url);
      
      // 路由处理
      switch (url.pathname) {
        case '/batch':
          const batchSize = parseInt(url.searchParams.get('size')) || 5;
          const urls = await getPagesBatch(batchSize);
          return new Response(JSON.stringify({ urls }), {
            headers: { 'Content-Type': 'application/json' }
          });
          
        case '/create':
          if (request.method !== 'POST') {
            return new Response('Method not allowed', { status: 405 });
          }
          const { url: pageUrl } = await request.json();
          const created = await createPage(pageUrl);
          return new Response(JSON.stringify({ created }), {
            headers: { 'Content-Type': 'application/json' }
          });
          
        case '/stats':
          const stats = await getStats();
          return new Response(JSON.stringify(stats), {
            headers: { 'Content-Type': 'application/json' }
          });
          
        default:
          return new Response('Not found', { status: 404 });
      }
      
    } catch (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }
};
