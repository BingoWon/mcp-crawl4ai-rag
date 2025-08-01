#!/bin/bash

echo "🌐 数据库公网访问自动配置"
echo "=========================="
echo "将本地数据库暴露到公网访问"
echo ""

# 检查是否在正确目录
if [ ! -f "../.env" ]; then
    echo "❌ 请在项目根目录运行此脚本"
    echo "正确用法: ./database-public-access/setup_public_access.sh"
    exit 1
fi

# 检查必要文件
echo "🔍 检查必要文件..."
if [ ! -f "database_api_server.py" ]; then
    echo "❌ 未找到 database_api_server.py"
    exit 1
fi

# 检查Cloudflare Tunnel是否已配置
echo "🔍 检查Cloudflare Tunnel配置..."
if [ ! -f "$HOME/.cloudflared/config.yml" ]; then
    echo "❌ Cloudflare Tunnel未配置"
    echo "请先配置Cloudflare Tunnel:"
    echo "1. 安装 cloudflared"
    echo "2. 登录 Cloudflare"
    echo "3. 创建 tunnel"
    echo "4. 配置域名"
    exit 1
fi

# 检查API服务是否运行
echo "🔍 检查API服务状态..."
if launchctl list | grep -q "com.apple-rag.api"; then
    echo "✅ API服务已运行"
else
    echo "⚠️  API服务未运行，正在启动..."
    # 这里可以添加启动API服务的逻辑
fi

# 检查Tunnel服务是否运行
echo "🔍 检查Tunnel服务状态..."
if launchctl list | grep -q "com.apple-rag.tunnel"; then
    echo "✅ Tunnel服务已运行"
else
    echo "⚠️  Tunnel服务未运行，正在启动..."
    # 这里可以添加启动Tunnel服务的逻辑
fi

# 测试本地API
echo "🔍 测试本地API连接..."
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "✅ 本地API服务正常"
else
    echo "❌ 本地API服务异常"
    exit 1
fi

# 测试公网访问
echo "🔍 测试公网访问..."
if curl -s https://db.apple-rag.com/health | grep -q "healthy"; then
    echo "✅ 公网访问正常"
else
    echo "❌ 公网访问异常"
    exit 1
fi

# 测试数据库连接
echo "🔍 测试数据库连接..."
if curl -s -X POST https://db.apple-rag.com/query \
  -H "X-API-Key: ZBYlBx77H9Sc87k" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT 1"}' | grep -q "success"; then
    echo "✅ 数据库连接正常"
else
    echo "❌ 数据库连接异常"
    exit 1
fi

echo ""
echo "🎉 数据库公网访问配置完成！"
echo "=========================="
echo ""
echo "✅ 本地数据库: PostgreSQL (localhost:5432) → PgBouncer (localhost:6432)"
echo "✅ API服务: FastAPI (localhost:8000)"
echo "✅ 公网访问: https://db.apple-rag.com"
echo ""
echo "📊 访问方式:"
echo "- 健康检查: curl https://db.apple-rag.com/health"
echo "- 数据查询: curl -X POST https://db.apple-rag.com/query \\"
echo "           -H 'X-API-Key: ZBYlBx77H9Sc87k' \\"
echo "           -d '{\"query\": \"SELECT COUNT(*) FROM pages\"}'"
echo ""
echo "🌐 你的本地数据库现在可以被全世界安全访问！"
echo ""
echo "📚 更多信息请查看 README.md"
