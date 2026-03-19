# 域名访问问题排查指南

## 🚨 **当前问题状态**

### ❌ **仍需解决的问题**
- https://prometheus.apple-rag.com - 可能需要重启服务
- https://adguard.apple-rag.com - 可能需要重启服务

### ✅ **已修复的配置**
- NPM 代理配置已正确设置
- SSL 证书已配置
- 所有容器状态正常

## 🔄 **立即修复步骤**

### **步骤1: 重启 NPM 服务**
```bash
# 方法1: 重启 NPM 容器
docker compose restart npm_proxy

# 方法2: 完整重启
docker compose down && docker compose up -d
```

### **步骤2: 验证配置**
访问 NPM 管理界面: http://198.12.70.36:81

确认以下配置正确：

| 域名 | Forward Host | Forward Port | 状态 |
|------|-------------|-------------|------|
| prometheus.apple-rag.com | `prometheus_monitor` | `9090` | ✅ |
| adguard.apple-rag.com | `198.12.70.36` | `8053` | ✅ |

### **步骤3: 测试访问**
```bash
# 测试 Prometheus
curl -I https://prometheus.apple-rag.com

# 测试 AdGuard
curl -I https://adguard.apple-rag.com
```

## 🔍 **深度排查**

### **检查容器网络连通性**
```bash
# 从 NPM 容器测试 Prometheus
docker exec npm_proxy curl -s http://prometheus_monitor:9090/api/v1/status/config

# 检查 AdGuard 进程
ps aux | grep -i adguard
netstat -tlnp | grep 8053
```

### **检查防火墙设置**
```bash
# 检查防火墙状态
ufw status

# 确保端口开放
ufw allow 9090
ufw allow 8053
```

### **检查 DNS 解析**
```bash
# 检查域名解析
nslookup prometheus.apple-rag.com
nslookup adguard.apple-rag.com

# 应该解析到: 198.12.70.36
```

## 🛠️ **常见问题解决**

### **问题1: 502 Bad Gateway**
**原因**: NPM 无法连接到后端服务
**解决**:
1. 检查目标服务是否运行
2. 验证容器网络连通性
3. 重启相关服务

### **问题2: SSL 证书错误**
**原因**: Let's Encrypt 证书问题
**解决**:
1. 在 NPM 中重新申请证书
2. 检查域名 DNS 解析
3. 等待证书自动更新

### **问题3: 连接超时**
**原因**: 防火墙或网络问题
**解决**:
1. 检查防火墙设置
2. 验证端口开放状态
3. 检查服务器网络连接

## 📋 **完整检查清单**

- [ ] NPM 容器运行正常
- [ ] 目标服务容器运行正常
- [ ] NPM 代理配置正确
- [ ] SSL 证书有效
- [ ] 防火墙端口开放
- [ ] DNS 解析正确
- [ ] 容器网络连通
- [ ] 服务重启完成

## 🎯 **预期结果**

修复完成后，以下域名应该正常访问：
- ✅ https://prometheus.apple-rag.com
- ✅ https://adguard.apple-rag.com
- ✅ https://grafana.apple-rag.com
- ✅ https://npm.apple-rag.com
- ✅ https://portainer.apple-rag.com

## 📞 **紧急联系**

如果问题持续存在，请检查：
1. 服务器资源使用情况
2. Docker 守护进程状态
3. 系统日志错误信息

```bash
# 系统资源检查
htop
df -h

# Docker 状态检查
systemctl status docker

# 系统日志检查
journalctl -u docker -f
```
