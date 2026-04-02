#!/bin/bash
# Manim 平台部署脚本
# 自动排除敏感配置文件，避免覆盖服务器配置

set -e

echo "=========================================="
echo "  Manim 平台部署脚本"
echo "=========================================="

# 1. 打包后端代码（排除 .env 文件）
echo ""
echo "[1/5] 打包后端代码..."
tar -czvf backend.tar.gz \
  --exclude='backend/.env' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='*.db' \
  --exclude='videos/*' \
  backend/

# 2. 构建前端
echo ""
echo "[2/5] 构建前端..."
cd frontend
npm run build
cd ..
tar -czvf frontend_dist.tar.gz -C frontend/dist .

# 3. 上传到新服务器
echo ""
echo "[3/5] 上传到新服务器 (152.136.218.74)..."
scp backend.tar.gz root@152.136.218.74:/opt/manim/
scp frontend_dist.tar.gz root@152.136.218.74:/opt/manim/

# 4. 上传到旧服务器
echo ""
echo "[4/5] 上传到旧服务器 (106.52.166.109)..."
scp backend.tar.gz root@106.52.166.109:/opt/manim/

# 5. 部署到新服务器
echo ""
echo "[5/5] 部署到服务器..."
ssh root@152.136.218.74 << 'ENDSSH'
cd /opt/manim
echo "  - 解压后端代码..."
tar -xzvf backend.tar.gz > /dev/null
echo "  - 解压前端代码..."
tar -xzvf frontend_dist.tar.gz -C frontend/dist > /dev/null
echo "  - 重启服务..."
systemctl restart manim
echo "  - 新服务器部署完成！"
ENDSSH

ssh root@106.52.166.109 << 'ENDSSH'
cd /opt/manim
echo "  - 解压后端代码..."
tar -xzvf backend.tar.gz > /dev/null
echo "  - 重启服务..."
systemctl restart manim
echo "  - 旧服务器部署完成！"
ENDSSH

# 6. 验证部署
echo ""
echo "=========================================="
echo "  验证部署..."
echo "=========================================="

sleep 3

echo ""
echo "新服务器状态:"
curl -s http://152.136.218.74:8000/health | head -1

echo ""
echo "旧服务器状态:"
curl -s http://106.52.166.109:8000/health | head -1

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="