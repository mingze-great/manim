# 思维可视化项目协作规则

本文件是本项目专属规则，优先用于 3002/3003 远程开发、部署、回退和排障。

## 环境定义

- `3002` 是正式展示/生产服务，不能直接试错。
- `3003` 是测试、验收、复现环境，新功能必须先部署到 3003 验证。
- 3003 验收通过后，才能按文档同步到 3002。
- 如果用户明确说“不能影响 3002”，所有修改必须限制在 3003 或独立备份目录。

## 服务与路径

3002：

```text
目录：/opt/manim-v2
前端：/opt/manim-v2/frontend/dist
后端：/opt/manim-v2/backend
后端服务：manim-v2-backend.service
Worker：manim-v2-worker.service
页面端口：3002
后端端口：8002
队列：manim_v2
```

3003：

```text
后端目录：/opt/manim-v2-3003-snapshot/backend
前端 dist：/opt/manim-v2-3003-repro-3002-current/frontend/dist
后端服务：manim-v2-3003-backend.service
Worker：manim-v2-3003-worker.service
页面端口：3003
后端端口：8003
队列：manim_v2_3003
```

共享数据库：`/opt/manim/backend/manim.db`

模板预览共享目录：`/opt/manim/shared/videos/template_examples`

## 3002 修改规则

- 不允许直接在 3002 上试错新功能。
- 修改 3002 前必须备份相关代码、配置和必要数据。
- 首页修改只能动首页相关展示和逻辑，不得影响登录、工作台、脚本生成、模板、渲染和 worker。
- 任何 3002 修改后必须验证：`/`、`/login`、`/creator`、模板预览视频、nginx、backend、worker。

## 3003 到 3002 同步规则

- 同步前必须记录 3003 实际运行来源，不只看某个目录名。
- 3003 后端来源以 systemd `WorkingDirectory` 为准。
- 3003 前端来源以 nginx `root` 指向的 dist 为准。
- 如果 3003 有未提交工作区改动，必须先固化为快照分支或在部署文档中明确记录。
- 同步到 3002 时必须保留 3002 自己的 `.env`、端口和队列。
- 同步到 3003 时必须保留 3003 自己的 `.env`、端口和队列。

## 部署快照规则

每次重要部署后必须创建或更新：

```text
docs/deployments/3002-current-YYYYMMDD.md
docs/deployments/templates_3002_YYYYMMDD.json
```

并推送远程快照分支，例如：`repro/3002-current-YYYYMMDD`。

快照文档必须包含部署时间、来源环境、来源分支和 commit、是否存在未提交改动、前端 dist hash、后端来源目录、目标服务、备份目录、验证结果和回退说明。

## 模板与预览视频规则

- 模板配置主要在数据库 `templates` 表中，不能只看 Git。
- 每次模板变更必须导出 `templates` 表。
- 模板预览视频必须验证 HTTP 可访问：`/api/videos/template_examples/template_<id>_preview.mp4`。
- 新增模板的真实生成配置必须参考老版动态模板结构，不能把固定示例 Manim 脚本直接写入生产模板 code。
- 预览视频可以使用固定样例，但不能污染真实生成模板。
- 用户可见字段不能出现不该暴露的内部字样。

## 运行数据与提交边界

禁止提交：

```text
backend/storage/
backend/videos/
frontend/tsconfig.tsbuildinfo
node_modules/
*.mp4
*.wav
```

允许提交后端源码、前端源码、必要时强制提交当前部署用 `frontend/dist`、部署文档、templates 表导出 JSON、清理脚本或运维脚本。

## 推荐流程

详细步骤见：`docs/deployments/DEPLOYMENT_WORKFLOW.md`。