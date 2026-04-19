#!/bin/bash
# 后台渲染稳定性优化 - 部署脚本
# 执行方式: bash scripts/deploy_backend_stability.sh

set -e

echo "========================================="
echo "开始部署后台渲染稳定性优化"
echo "========================================="

# 进入项目目录
cd /opt/manim-dev

# 1. 拉取最新代码
echo ""
echo "[1/6] 拉取最新代码..."
git fetch origin
git checkout fix/stickman-types-and-api
git pull origin fix/stickman-types-and-api

# 2. 检查 Redis 状态
echo ""
echo "[2/6] 检查 Redis 状态..."
if systemctl is-active --quiet redis-server; then
    echo "✓ Redis 已运行"
else
    echo "启动 Redis..."
    systemctl start redis-server
    systemctl enable redis-server
fi

# 3. 安装 Python 依赖
echo ""
echo "[3/6] 安装 Python 依赖..."
cd /opt/manim-dev/backend
if [ -f "requirements.txt" ]; then
    /root/miniconda3/envs/manim/bin/pip install -r requirements.txt
fi

# 4. 构建前端
echo ""
echo "[4/6] 构建前端..."
cd /opt/manim-dev/frontend
npm install
npm run build

# 5. 重启 Celery Worker
echo ""
echo "[5/6] 重启 Celery Worker..."
pkill -f "celery.*manim" || true
sleep 2
cd /opt/manim-dev/backend
nohup /root/miniconda3/envs/manim/bin/celery -A app.celery_app worker --loglevel=info > /opt/manim-dev/logs/celery.log 2>&1 &
echo "✓ Celery Worker 已启动"

# 6. 重启后端服务
echo ""
echo "[6/6] 重启后端服务..."
systemctl restart manim-dev || supervisorctl restart manim-dev || pkill -f "uvicorn.*app.main:app" || true
sleep 3
cd /opt/manim-dev/backend
nohup /root/miniconda3/envs/manim/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload > /opt/manim-dev/logs/backend.log 2>&1 &
echo "✓ 后端服务已重启"

echo ""
echo "========================================="
echo "部署完成！"
echo "========================================="
echo ""
echo "验证命令："
echo "  - 检查 Celery 状态: curl http://localhost:8001/tasks/celery-status"
echo "  - 查看进行中任务: curl http://localhost:8001/tasks/in-progress"
echo "  - 查看 Celery 日志: tail -f /opt/manim-dev/logs/celery.log"
echo "  - 查看后端日志: tail -f /opt/manim-dev/logs/backend.log"
