# 3003 最新服务部署记录（2026-07-11）

## 部署目标

将 3003 部署到知识 IP 自动包装工作流的最新远程分支状态，不影响 3002。

## 部署来源

- 服务器：152.136.218.74
- 目录：/opt/manim-v2-3003-snapshot
- 分支：codex/3003-knowledge-ip-workflow-20260710
- 提交：ab0644a9
- 提交信息：fix: make knowledge IP workflow reusable on 3003
- 部署时间：2026-07-11 02:31:35 +0800

## 本次构建

- 前端：cd frontend && npm run build
- Remotion 渲染服务：cd video-render-service/remotion-mind-video && npm run build

## 重启服务

- manim-v2-3003-backend.service
- manim-v2-3003-worker.service
- manim-v2-3003-ai-video-render.service

## 验证结果

- http://127.0.0.1:3003/ 返回 200
- http://127.0.0.1:8003/health 返回 healthy
- http://127.0.0.1:18787/api/health 返回 ok，并识别 Remotion browserExecutable
- 3002 未修改

## 注意事项

部署目录存在运行产物和历史未提交文件，例如 backend/storage/、backend/uploads/、Remotion public/、renders/、tmp/ 等，未纳入本次提交。

前端 dist 为部署构建产物，如后续回滚请按分支提交重新构建。
