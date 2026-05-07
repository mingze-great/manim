# Repro 3002 From Remote

目标：

- 通过远程分支直接拉取
- 复现当前 `3002` 对应服务状态
- 不依赖本地未提交代码

## 基准

- 复现分支：`repro/3002-105c9739`
- 复现提交：`105c9739`
- 已验证环境：
  - `3003`
  - 目录：`/opt/manim-v2-3003-snapshot`

## 适用场景

- 新机器复现
- 新端口复现
- 排查“线上到底跑哪版”
- 避免把工作分支上更多未验证改动带进部署

## 标准步骤

### 1. 拉取远程分支

```bash
git fetch origin repro/3002-105c9739
git checkout -B repro/3002-105c9739 FETCH_HEAD
git reset --hard FETCH_HEAD
```

如果本地已经有该分支：

```bash
git fetch origin repro/3002-105c9739
git checkout repro/3002-105c9739
git reset --hard origin/repro/3002-105c9739
```

### 2. 后端校验

```bash
python -m py_compile backend/app/api/projects.py backend/app/api/tasks.py backend/app/services/stickman_generator_v2.py backend/app/tasks/render.py
```

### 3. 前端构建

```bash
cd frontend
npm run build
cd ..
```

### 4. 部署到目标目录

如果目标就是另一套独立目录，例如 `/opt/manim-v2-3003-snapshot`：

后端：

```bash
rm -rf /opt/manim-v2-3003-snapshot/backend/app
cp -r backend/app /opt/manim-v2-3003-snapshot/backend/
```

前端：

```bash
rm -rf /opt/manim-v2-3003-snapshot/frontend/dist
mkdir -p /opt/manim-v2-3003-snapshot/frontend/dist
cp -r frontend/dist/* /opt/manim-v2-3003-snapshot/frontend/dist/
```

说明：

- 如果跨机器传输，优先继续使用 `tar.gz` 或 `bundle`
- 不要用 Windows `zip` 直接覆盖 Linux 代码目录

### 5. 重启对应服务

以 `3003` 为例：

```bash
systemctl restart manim-v2-3003-backend.service
systemctl restart manim-v2-3003-worker.service
sleep 8
```

### 6. 验证

```bash
curl -s http://127.0.0.1:8003/health
curl -I http://127.0.0.1:3003/
git rev-parse HEAD
git rev-parse --abbrev-ref HEAD
```

预期：

- 健康检查返回 `status=healthy`
- 前端返回 `200 OK`
- git 分支是 `repro/3002-105c9739`
- git 提交是 `105c9739`

## 当前包含能力

这条复现分支对应的功能基线包括：

- 对话默认 `classic`
- 增强讲解独立工作流
- 文案分镜处理进度反馈
- 英文字幕状态提示

## 不包含后续实验改动

这条分支故意不追后面工作分支上的所有新提交，只用于：

- 稳定复现当前 `3002`
- 作为新端口/新环境的统一基线

## 关联文档

- `docs/V2_3002_STANDARD_DEPLOY.md`
