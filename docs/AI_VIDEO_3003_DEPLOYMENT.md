# AI Video Module 3003 Deployment

更新时间：2026-06-24 09:50 CST

## 分支与基线

本次 AI 视频模块基于 3003 当前复现 3002 的稳定快照继续开发。

```text
基线分支：repro/3002-current-20260623
基线提交：4f16548dad8b3b9b170eb815ccc955efaadd501d
开发分支：feature/ai-video-module-on-3003
开发提交：b7caab0dd90333bdf3524560e75eedd42709493b
```

远程分支已经推送：

```bash
git fetch origin feature/ai-video-module-on-3003
git checkout -B feature/ai-video-module-on-3003 origin/feature/ai-video-module-on-3003
```

## 部署位置

只部署到 3003，不影响 3002。

```text
服务器：152.136.218.74
3003 目录：/opt/manim-v2-3003-snapshot
3003 前端端口：3003
3003 后端端口：8003
3003 后端服务：manim-v2-3003-backend.service
3003 worker 服务：manim-v2-3003-worker.service
```

3002 仍保持独立：

```text
3002 目录：/opt/manim-v2
3002 前端端口：3002
3002 后端端口：8002
```

## 新增模块范围

新增前端入口：

```text
/ai-video
/ai-video/dashboard
/ai-video/create
/ai-video/editor/:id
/ai-video/templates
/ai-video/assets
/ai-video/brand-kit
/ai-video/exports
/ai-video/settings
```

新增后端 namespace：

```text
/api/ai-video/*
```

新增独立数据表：

```text
ai_video_projects
ai_video_jobs
ai_video_versions
ai_video_assets
ai_video_brand_kits
```

新增隔离文件目录：

```text
storage/ai-video/tasks/{jobId}/
```

## 已验证能力

远程 3003 已完成以下验证：

```text
登录测试用户：通过
POST /api/ai-video/jobs：通过
GET /api/ai-video/jobs/{jobId} 状态轮询：通过
GET /api/ai-video/projects/{projectId} 获取 project.json：通过
POST /api/ai-video/projects/{projectId}/edit 生成修改计划：通过
POST /api/ai-video/projects/{projectId}/apply-edit 保存新版本：通过
GET /api/ai-video/files/{jobId}/output/video.mp4 下载 MP4：通过
```

远程验收样例：

```text
jobId：job_1
projectId：1
输出文件：/api/ai-video/files/1/output/video.mp4
MP4 下载：200 OK，video/mp4，68227 bytes
```

服务健康：

```text
3003 页面：200 OK
8003 health：healthy
3002 / 8002：仍保持监听和 healthy
```

## 回滚信息

部署前 3003 备份：

```text
/opt/manim_backups/manim-v2-3003-before-ai-video-20260624_094606.tar.gz
```

回滚原则：

```text
只回滚 /opt/manim-v2-3003-snapshot
只重启 manim-v2-3003-backend.service 和 manim-v2-3003-worker.service
不要操作 /opt/manim-v2
不要重启 3002 / 8002
```

## 注意事项

当前第一版是安全接入 MVP：

```text
已完成独立入口、独立 API、独立表、任务状态、project.json、版本、品牌资产、导出记录、文件隔离和验证闭环。
渲染闭环当前在 3003 后端异步任务中生成可验证 MP4 占位产物。
后续接入真实 Remotion / CosyVoice 独立服务时，应继续使用 /api/ai-video/* 和 storage/ai-video/tasks/*，不要复用现有业务表或上传根目录。
```
