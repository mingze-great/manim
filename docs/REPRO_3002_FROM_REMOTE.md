# Repro 3002 From Remote

目标：

- 通过远程分支直接拉取
- 复现当前 `3002` 对应服务状态
- 不依赖本地未提交代码

## 基准

- 复现分支：`repro/3002-105c9739`
- 复现提交：`105c9739`
- 开发分支：`feature/stickman-v2-viral-hook-optimization-acceptance`
- 说明：
  - 要稳定复现当前 `3002`，只拉 `repro/3002-105c9739`
  - `feature/stickman-v2-viral-hook-optimization-acceptance` 用于继续开发和记录文档，不作为当前 `3002` 的唯一复现基准

## 为什么单独建 Repro 分支

- `3002` 线上状态需要一个“冻结快照”，保证任何时候都能按同一个分支和提交复现。
- 开发分支会继续前进，包含未完全验证的新改动；如果直接拿开发分支复现，后面很容易出现“同名分支、不同效果”。
- `repro/3002-105c9739` 的作用就是把“当时线上稳定版本”单独钉住：
  - 方便新机器复现
  - 方便回滚
  - 方便和后续优化版本做对比

## 在别处复现 3002

假设目标目录是 `/opt/manim-v2-copy`，目标端口是前端 `3010`、后端 `8010`。

### 1. 拉取复现分支

```bash
git clone <repo-url> /opt/manim-v2-copy
cd /opt/manim-v2-copy
git fetch origin repro/3002-105c9739
git checkout -B repro/3002-105c9739 FETCH_HEAD
git reset --hard FETCH_HEAD
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

### 4. 准备独立运行目录和配置

- 复制 `.env.development` / `.env.production`
- 确认数据库、Redis、上传目录路径符合新环境
- 不要和现有 `3002` / `3003` 目录混用 `dist`、`app`、日志目录

### 5. 启动独立服务

- 后端工作目录指向新目录下的 `backend`
- 前端 Nginx 指向新目录下的 `frontend/dist`
- 端口使用新的独立端口

### 6. 验证

```bash
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
curl -s http://127.0.0.1:8010/health
curl -I http://127.0.0.1:3010/
```

预期：

- 分支：`repro/3002-105c9739`
- 提交：`105c9739`

## 后续要在当前 3002 基础上继续优化时怎么做

推荐流程：

1. 在开发分支继续做改动：
   - `feature/stickman-v2-viral-hook-optimization-acceptance`
2. 本地验证通过后，先提交并推到远程开发分支。
3. 部署到 `3002` 验证。
4. 如果新版本稳定，**再新建一个新的 repro 分支**，例如：
   - `repro/3002-<new-sha>`
5. 更新本文件和 `V2_3002_STANDARD_DEPLOY.md`，把新的 repro 分支写进去。

这样做的好处：

- 开发分支负责“继续演进”
- repro 分支负责“冻结一个可复现的线上版本”
- 两条线职责清晰，不会互相污染
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
