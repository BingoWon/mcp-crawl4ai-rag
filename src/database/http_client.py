"""
通用HTTP数据库客户端
支持基础API密钥认证，专为Cloudflare Workers设计
"""

import json
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from .config import DatabaseConfig


class HTTPDatabaseClient:
    """通用HTTP数据库客户端，支持基础API密钥认证"""

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig.from_env()
        self.session: Optional[aiohttp.ClientSession] = None
        self._initialized = False
        self.base_url = self.config.remote_api_base_url

        # API密钥配置
        self.api_key = self.config.api_key

    async def initialize(self) -> None:
        """Initialize HTTP session"""
        if self._initialized:
            return
            
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.remote_api_timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # Test connection
            await self._health_check()
            self._initialized = True
            
            from utils.logger import setup_logger
            logger = setup_logger(__name__)
            logger.info(f"✅ HTTP database client initialized: {self.config.remote_api_base_url}")

        except Exception as e:
            from utils.logger import setup_logger
            logger = setup_logger(__name__)
            logger.error(f"❌ Failed to initialize HTTP database client: {e}")
            raise

    async def close(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self._initialized = False

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _health_check(self) -> None:
        """Check if remote API is healthy"""
        url = f"{self.config.remote_api_base_url}/health"
        async with self.session.get(url) as response:
            if response.status != 200:
                raise ConnectionError(f"Remote API health check failed: {response.status}")
            
            data = await response.json()
            if data.get('status') != 'healthy':
                raise ConnectionError(f"Remote API is not healthy: {data}")

    def _parse_pipe_separated_result(self, raw_result: str, column_names: List[str]) -> Dict[str, Any]:
        """解析管道分隔的查询结果"""
        if not raw_result or not column_names:
            return {}

        values = raw_result.split('|')
        # 确保值的数量与列名数量匹配
        while len(values) < len(column_names):
            values.append('')

        return {col: val for col, val in zip(column_names, values[:len(column_names)])}

    def _extract_column_names_from_query(self, query: str) -> List[str]:
        """从SQL查询中提取列名"""
        import re

        # 简单的SELECT列名提取（支持常见情况）
        query_upper = query.upper().strip()

        # 处理 SELECT COUNT(*) 等聚合查询
        if 'COUNT(*)' in query_upper:
            return ['count']

        # 处理 SELECT column1, column2 FROM table
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', query_upper)
        if select_match:
            columns_str = select_match.group(1)
            if columns_str.strip() == '*':
                # 对于SELECT *，我们无法预知列名，返回通用名称
                return ['result']

            # 解析列名
            columns = [col.strip() for col in columns_str.split(',')]
            # 处理别名 (AS alias)
            parsed_columns = []
            for col in columns:
                if ' AS ' in col:
                    parsed_columns.append(col.split(' AS ')[1].strip())
                else:
                    # 取最后一个词作为列名（处理 table.column 情况）
                    parsed_columns.append(col.split('.')[-1].strip())
            return parsed_columns

        # 默认返回通用列名
        return ['result']

    async def _execute_api_query(self, query: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute query via HTTP API"""
        url = f"{self.config.remote_api_base_url}/query"
        payload = {
            'query': query,
            'params': params or []
        }

        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                raise Exception(f"API query failed: {response.status}")

            result = await response.json()
            if not result.get('success', False):
                raise Exception(f"Query execution failed: {result.get('error', 'Unknown error')}")

            # 解析管道分隔的结果为字典格式
            if result.get('data'):
                column_names = self._extract_column_names_from_query(query)
                parsed_data = []
                for row in result['data']:
                    if isinstance(row, dict) and 'result' in row:
                        parsed_row = self._parse_pipe_separated_result(row['result'], column_names)
                        parsed_data.append(parsed_row)
                    else:
                        parsed_data.append(row)
                result['data'] = parsed_data

            return result

    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dicts"""
        result = await self._execute_api_query(query, list(args))
        return result.get('data', [])

    async def execute_command(self, command: str, *args) -> str:
        """Execute a command and return status"""
        result = await self._execute_api_query(command, list(args))
        return f"Command executed successfully, affected {result.get('row_count', 0)} rows"

    async def execute_many(self, command: str, args_list: List[tuple]) -> None:
        """Execute command with multiple parameter sets"""
        # For HTTP API, we need to execute each command separately
        # This is less efficient but maintains compatibility
        for args in args_list:
            await self._execute_api_query(command, list(args))



    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """发送HTTP请求"""
        if not self.session:
            raise RuntimeError("HTTP client not initialized")

        url = f"{self.base_url}{endpoint}"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        body = json.dumps(data) if data else None

        async with self.session.request(method, url, headers=headers, data=body) as response:
            if response.status != 200:
                raise Exception(f"HTTP request failed: {response.status}")

            return await response.json()

    # 通用SQL接口方法
    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """执行查询并返回所有结果"""
        data = {
            "query": query,
            "params": list(args) if args else None
        }
        result = await self._request("POST", "/query", data)

        if not result.get("success"):
            raise Exception(f"Query failed: {result.get('error')}")

        return result.get("data", [])

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """执行查询并返回单个结果"""
        results = await self.fetch_all(query, *args)
        return results[0] if results else None

    async def fetch_val(self, query: str, *args) -> Any:
        """执行查询并返回单个值"""
        result = await self.fetch_one(query, *args)
        if result:
            return next(iter(result.values()))
        return None

    async def execute_command(self, query: str, *args) -> str:
        """执行命令并返回结果"""
        data = {
            "query": query,
            "params": list(args) if args else None
        }
        result = await self._request("POST", "/execute", data)

        if not result.get("success"):
            raise Exception(f"Execute failed: {result.get('error')}")

        affected_rows = result.get("affected_rows", 0)
        return f"Command executed successfully. Affected rows: {affected_rows}"

    async def execute_many(self, query: str, params_list: List[tuple]) -> str:
        """批量执行命令"""
        requests = [
            {"query": query, "params": list(params)}
            for params in params_list
        ]

        result = await self._request("POST", "/batch", {"requests": requests})

        if not result.get("success"):
            raise Exception(f"Batch execute failed: {result.get('error')}")

        affected_rows = result.get("affected_rows", 0)
        return f"Batch executed successfully. Total affected rows: {affected_rows}"

    async def get_pages_batch(self, batch_size: int = 5) -> List[str]:
        """获取待爬取URL批次"""
        query = """
            SELECT url FROM pages
            WHERE crawl_count = 0
            ORDER BY created_at ASC
            LIMIT $1
        """
        results = await self.fetch_all(query, batch_size)
        return [row.get('url') or row.get('result') for row in results if row.get('url') or row.get('result')]

    async def insert_page(self, url: str) -> bool:
        """Insert URL with crawl_count=0 and last_crawled_at=NULL if not exists. Returns True if inserted."""
        query = """
            INSERT INTO pages (url, crawl_count, content, last_crawled_at)
            VALUES ($1, 0, '', NULL)
            ON CONFLICT (url) DO NOTHING
        """
        try:
            result = await self._execute_api_command(query, [url])
            # 检查是否有行被影响（即是否插入了新记录）
            return result.get("affected_rows", 0) > 0
        except Exception as e:
            # 如果出错，返回False
            return False

    # Database setup methods (no-op for HTTP client)
    async def _setup_database(self) -> None:
        """Setup database schema - no-op for HTTP client"""
        pass
