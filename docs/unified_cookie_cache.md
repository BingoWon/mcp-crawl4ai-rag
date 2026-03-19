# 统一的 Apple Cookie 缓存机制

## 功能概述

在 `src/crawler/apple_stealth_crawler.py` 中实现了统一的 Apple 网站 Cookie 缓存机制，使用现有的 `.cookie_cache/apple_cookies.json` 文件，避免重复的缓存文件。

## 功能特性

### 1. 统一缓存文件
- **缓存路径**：`.cookie_cache/apple_cookies.json`
- **避免重复**：使用现有的缓存文件，不再创建额外的备份文件
- **格式统一**：包含 `cookies` 和 `timestamp` 字段的标准格式

### 2. 智能缓存策略
- **优先浏览器**：首先尝试从 Edge 浏览器获取最新 Cookie
- **自动缓存**：成功获取后立即更新缓存文件
- **智能回退**：浏览器获取失败时自动使用缓存文件
- **优雅降级**：所有方式都失败时返回空 Cookie，不影响爬虫运行

### 3. 统一格式
- **标准格式**：`{"cookies": {...}, "timestamp": 1234567890}`
- **简洁实现**：无向后兼容，代码量最小化

## 技术实现

### 核心方法

#### `_get_apple_cookies()`
主要的 Cookie 获取方法，实现完整的缓存和回退逻辑。

#### `_extract_cookies_from_browser()`
从 Edge 浏览器提取 Apple 网站 Cookie，过滤相关域名。

#### `_save_cookies_cache()`
保存 Cookie 到统一缓存文件，包含时间戳信息。

#### `_load_cookies_cache()`
从缓存文件加载 Cookie。

### 缓存文件格式

```json
{
  "cookies": {
    "cookie_name_1": "cookie_value_1",
    "cookie_name_2": "cookie_value_2"
  },
  "timestamp": 1754179166.708
}
```

## 使用方式

功能已完全集成到 `CrawlerPool` 类中：

```python
from src.crawler.apple_stealth_crawler import CrawlerPool

# 创建爬虫池时自动处理 Cookie 缓存
async with CrawlerPool(pool_size=3) as pool:
    # Cookie 已自动获取并配置
    content, links = await pool.crawl_page(url)
```

## 日志输出

系统提供详细的日志信息：

```
# 成功从浏览器获取并保存缓存
INFO - Successfully extracted 14 Apple cookies from Edge and saved to cache
INFO - Saved 14 cookies to cache file: .cookie_cache/apple_cookies.json

# 使用缓存文件
INFO - Edge browser not found or cookie extraction failed: ...
INFO - Using 14 Apple cookies from cache file

# 无 Cookie 可用
INFO - No cookies available from browser or cache
```

## 测试

提供了完整的测试套件 `tests/test_unified_cookie_cache.py`：

### 测试内容
1. **浏览器获取测试**：验证从 Edge 浏览器获取 Cookie
2. **缓存保存测试**：验证 Cookie 保存到缓存文件
3. **缓存加载测试**：验证从缓存文件加载 Cookie
4. **Fallback 测试**：验证浏览器失败时的回退机制
5. **完整流程测试**：验证整个 Cookie 获取流程

### 运行测试
```bash
python tests/test_unified_cookie_cache.py
```

## 优势

1. **避免重复**：使用现有缓存文件，不创建重复的备份文件
2. **代码简洁**：无向后兼容，代码量最小化
3. **自动化管理**：无需手动管理，系统自动处理缓存和回退
4. **提高稳定性**：即使浏览器环境变化，仍能使用缓存的有效 Cookie
5. **透明集成**：对现有代码无侵入性，自动集成到爬虫流程

## 文件结构

```
.cookie_cache/
└── apple_cookies.json    # 统一的 Cookie 缓存文件
```

## 注意事项

1. **Cookie 时效性**：缓存的 Cookie 可能会过期，建议定期更新
2. **隐私安全**：缓存文件包含敏感信息，注意文件权限和存储安全
3. **目录权限**：确保程序有权限在 `.cookie_cache/` 目录创建和写入文件
4. **浏览器依赖**：功能依赖 Edge 浏览器和 `browser_cookie3` 库
