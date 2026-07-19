# 3003 知识 IP 真实工作流部署记录

- 部署时间：2026-07-11 17:14-17:38 +0800
- 目标服务：3003
- 部署目录：`/opt/manim-v2-3003-snapshot`
- 分支：`codex/3003-knowledge-ip-workflow-20260710`
- 提交：`53f70b78`
- 备份目录：`/opt/manim_backups/3003_before_knowledge_ip_real_workflow_20260711_171432`

## 本次变更

- 移除“上传后前端模拟进度并指向固定样片”的生成逻辑。
- 新增后端 `knowledge_ip` API：上传视频、启动任务、查询任务、获取本次成片。
- 上传动作独立：`/api/knowledge-ip/uploads` 只保存文件并创建任务，不进入生成进度。
- 开始生成动作：`/api/knowledge-ip/jobs/{job_id}/start` 后才进入提取音频、Paraformer 字幕识别、内容结构分析、动态图形包装、Remotion 渲染和保存成片。
- 前端生成结果只使用本次任务的 `result_url`，不再复用固定视频作为下载结果。
- 修复 Remotion 脚本对 `materialTrackSrc` 的默认固定素材轨回填，允许没有素材轨时使用组件内置动态图形包装。

## 验证结果

- `python -m py_compile backend/app/api/knowledge_ip.py backend/app/main.py` 通过。
- `npm run build` 通过。
- `/knowledge-ip` 返回 200。
- 上传接口返回中文：`视频已上传，等待开始生成。`
- 用 8 秒真实人声片段验证完整链路：任务 `kip_f55a88e2241f` 生成成功。
- 生成结果：`/api/knowledge-ip/jobs/kip_f55a88e2241f/video`，`ffprobe` 显示 8.086 秒、约 1.3MB。
- 前后端源码检查 `??` 计数为 0，未发现中文乱码。

## 当前边界

- 已接入 Paraformer 字幕识别与 Remotion 包装渲染。
- AI 小视频素材生成阶段当前先使用实时动态图形包装，后续再接入 wan/happyhorse 等模型生成分段素材视频。
- 当前任务状态存储在服务器文件中，后续生产化建议迁入数据库/队列，支持重启恢复、取消、重试和并发控制。

## ?? 3003 ???

- ?????2026-07-11 17:40-17:43 +0800
- ?????`http://127.0.0.1:3003/api/knowledge-ip/...`???? 3003 ? Nginx/API ?????
- ?????????`kip_9f1839ac0677`?
- ?????????? `extract_audio`?`render`?`completed`?
- ?????`/api/knowledge-ip/jobs/kip_9f1839ac0677/video`?
- `ffprobe` ???`duration=8.086000`?`size=1307192`?

???3003 ???????????????????????????????????

