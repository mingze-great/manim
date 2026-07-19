#!/bin/bash
set -e

echo "🚀 开始部署生产环境..."

# 拉取最新代码
git pull origin main

# 备份数据
./scripts/backup.sh || echo "备份失败，继续部署..."

# 停止旧容器
docker compose -f docker-compose.prod.yml down || true

# 构建新镜像
docker compose -f docker-compose.prod.yml build

# 启动新容器
docker compose -f docker-compose.prod.yml up -d

# 等待服务启动
echo "等待服务启动..."
sleep 15

# 健康检查
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✅ 部署成功！"
else
    echo "❌ 部署失败，回滚..."
    docker compose -f docker-compose.prod.yml down
    exit 1
fi
