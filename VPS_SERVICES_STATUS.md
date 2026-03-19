# VPS 服务状态文档

## 🌐 **当前服务访问状态**

### ✅ **正常运行的服务**

| 服务名称 | 域名 | 状态 | 配置 | SSL |
|---------|------|------|------|-----|
| **AdGuard** | https://adguard.apple-rag.com | ✅ Online | `198.12.70.36:8053` | Let's Encrypt |
| **Grafana** | https://grafana.apple-rag.com | ✅ Online | `grafana:3000` | Let's Encrypt |
| **NPM管理** | https://npm.apple-rag.com | ✅ Online | `npm:81` | Let's Encrypt |
| **Portainer** | https://portainer.apple-rag.com | ✅ Online | `portainer:9000` | Let's Encrypt |
| **Prometheus** | https://prometheus.apple-rag.com | ✅ Online | `prometheus_monitor:9090` | Let's Encrypt |

## 🔧 **NPM 代理配置详情**

### **AdGuard DNS 服务**
- **域名**: adguard.apple-rag.com
- **目标**: `http://198.12.70.36:8053`
- **说明**: AdGuard 运行在主机上，不是容器内
- **进程**: PID 374179，监听端口 53 和 8053

### **Prometheus 监控服务**
- **域名**: prometheus.apple-rag.com
- **目标**: `http://prometheus_monitor:9090`
- **说明**: 容器名为 `prometheus_monitor`，不是 `prometheus`
- **功能**: 系统监控和指标收集

### **Grafana 仪表板**
- **域名**: grafana.apple-rag.com
- **目标**: `http://grafana:3000`
- **功能**: 数据可视化和监控仪表板

### **Portainer 容器管理**
- **域名**: portainer.apple-rag.com
- **目标**: `http://portainer:9000`
- **功能**: Docker 容器管理界面

### **NPM 反向代理管理**
- **域名**: npm.apple-rag.com
- **目标**: `http://npm:81`
- **功能**: 反向代理和 SSL 证书管理

## 🛠️ **服务管理命令**

### **查看服务状态**
```bash
docker compose ps
```

### **重启特定服务**
```bash
# 重启 NPM
docker compose restart npm_proxy

# 重启 Prometheus
docker compose restart prometheus_monitor

# 重启 Grafana
docker compose restart grafana_dashboard
```

### **查看服务日志**
```bash
# NPM 日志
docker compose logs -f npm_proxy

# Prometheus 日志
docker compose logs -f prometheus_monitor

# 所有服务日志
docker compose logs
```

## 🔍 **故障排除**

### **域名无法访问时的检查步骤**

1. **检查容器状态**
   ```bash
   docker compose ps
   ```

2. **检查 NPM 配置**
   - 访问: http://198.12.70.36:81
   - 验证代理配置是否正确

3. **重启 NPM 服务**
   ```bash
   docker compose restart npm_proxy
   ```

4. **检查防火墙**
   ```bash
   ufw status
   ```

5. **检查 DNS 解析**
   ```bash
   nslookup prometheus.apple-rag.com
   ```

## 📊 **服务架构图**

```
Internet
    ↓
[NPM Proxy] (Port 80/443)
    ↓
┌─────────────────────────────────────┐
│  Docker Network: main_network       │
│                                     │
│  ┌─────────────┐  ┌─────────────┐   │
│  │  Grafana    │  │ Prometheus  │   │
│  │  :3000      │  │ _monitor    │   │
│  │             │  │ :9090       │   │
│  └─────────────┘  └─────────────┘   │
│                                     │
│  ┌─────────────┐  ┌─────────────┐   │
│  │ Portainer   │  │ PostgreSQL  │   │
│  │ :9000       │  │ :5432       │   │
│  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────┘
         │
    [Host System]
         │
   ┌─────────────┐
   │  AdGuard    │
   │  :8053      │
   │  PID 374179 │
   └─────────────┘
```

## 🎯 **重要提醒**

1. **AdGuard 特殊性**: 运行在主机上，不在容器内
2. **容器名称**: Prometheus 容器名为 `prometheus_monitor`
3. **SSL 证书**: 所有服务都使用 Let's Encrypt 自动证书
4. **配置更改**: 修改 NPM 配置后需要重启服务生效

## 📝 **更新日志**

- **2025-07-26**: 修复 Prometheus 和 AdGuard 代理配置
- **2025-07-26**: 确认所有服务正常运行
- **2025-07-26**: 更新文档反映实际配置状态
