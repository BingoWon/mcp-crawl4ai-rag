# API Keys Configuration

## 概述

本项目使用文件管理API Keys，提供自动故障转移和失效key删除功能。

## 配置文件

### `api_keys.txt`

存储所有SiliconFlow API Keys，每行一个key：

```
sk-your-first-api-key
sk-your-second-api-key
sk-your-third-api-key
```

## 功能特性

### 🔄 自动故障转移
- 当前key失效时自动切换到下一个可用key
- 支持无限数量的API keys
- 零停机时间的服务连续性

### 🗑️ 智能key管理
- **删除key**：401/402/403错误（认证失败、余额不足、权限拒绝）
- **切换key**：429错误（速率限制）
- **重试请求**：503/504错误（服务器错误）

### 💾 持久化存储
- key删除和切换操作自动保存到文件
- 重启后保持配置状态
- 线程安全的文件操作

## 使用方法

### 1. 创建配置文件

在项目根目录创建 `config/api_keys.txt` 文件：

```bash
mkdir -p config
echo "sk-your-api-key-here" > config/api_keys.txt
```

### 2. 添加多个keys

```bash
echo "sk-your-second-key" >> config/api_keys.txt
echo "sk-your-third-key" >> config/api_keys.txt
```

### 3. 验证配置

系统会自动：
- 检测失效的API keys
- 删除无效keys
- 切换到可用keys
- 记录操作日志

## 迁移说明

### 从环境变量迁移

如果您之前使用 `.env` 文件中的 `SILICONFLOW_API_KEY`：

1. 将key添加到 `config/api_keys.txt`
2. 从 `.env` 文件中删除 `SILICONFLOW_API_KEY`
3. 重启应用程序

### 配置验证

启动时查看日志确认配置正确：

```
✅ SiliconFlow API provider initialized with multi-key management
✅ Current key: sk-xxx...
```

## 故障排除

### 常见问题

**Q: 所有keys都失效了怎么办？**
A: 系统会抛出 "No API keys available" 错误，需要添加新的有效keys。

**Q: 如何查看当前使用的key？**
A: 查看应用程序日志，会显示当前key的前20个字符。

**Q: key切换是否会影响正在进行的请求？**
A: 不会，key切换只影响新的API请求。

### 日志示例

```
🔄 Rate limited, switched to next key
🗑️ Key permanently failed (HTTP 403), removed
✅ Multi-key batch encoded 100 embeddings
```

## 安全建议

1. **权限控制**：确保 `config/api_keys.txt` 文件权限为 600
2. **备份keys**：定期备份有效的API keys
3. **监控余额**：定期检查API key余额，及时充值
4. **日志审查**：定期查看key使用和切换日志

## 技术实现

- **KeyManager**：107行精简代码实现完整功能
- **线程安全**：使用Lock保护文件操作
- **异步操作**：使用aiofiles进行非阻塞文件I/O
- **智能索引**：正确处理key删除后的索引调整
