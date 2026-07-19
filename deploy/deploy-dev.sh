#!/bin/bash
set -e

echo "🔧 开始部署开发环境..."

# 切换到 develop 分支
git checkout develop
git pull origin develop

# 重启开发容器
docker compose -f docker-compose.dev.yml down || true
docker compose -f docker-compose.dev.yml build
docker compose -f docker-compose.dev.yml up -d

echo "✅ 开发环境部署完成！"
echo "访问: http://152.136.218.74:3000"
