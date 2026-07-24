# AGENTS.md

## 项目使命
本项目维护 3003 端口上的 SC1 心理学火柴人一键成片工作流。平台必须支持用户只输入一个主题，就自动完成爆款文案生成、语义分段、素材匹配、配音合成、Remotion 渲染、进度反馈、成片校验和交付。

核心质量标准是完全贴近参考视频：

- 本地参考视频：`E:\ai\火柴人工作流\SC1全赛道高级版火柴人\20250901-10a36ef4-5593-478f-a2f6-5b28301f4a7e.mov`
- 本地素材库：`E:\ai\火柴人工作流\outputs`
- 远程素材库：`/opt/manim_assets/sc1-outputs`
- 远程 3003 部署目录：`/opt/manim-v2-3003-snapshot`
- 当前部署分支：`codex/3003-standalone-stickman-workflow-20260712`

## 是否会自动读取这些文件
不能假设每次编码前系统都会自动完整读取所有项目文档。通常新的 Codex 上下文会收到离当前目录最近的 `AGENTS.md` 内容，但不会保证自动读取 `PROJECT_STATE.md`、`rules/`、`specs/` 或历史计划文件。

因此，任何进入本项目的 agent 在动代码前必须主动读取：

1. `AGENTS.md`
2. `PROJECT_STATE.md`
3. `rules/vibe-coding.md`
4. `rules/quality-gates.md`
5. `rules/skill-usage.md`
6. `rules/agent-orchestration.md`
7. `specs/sc1-stickman-workflow-spec.md`
8. `specs/development-control-spec.md`
9. `specs/master-agent-workflow-spec.md`

如果是远程部署、上下文交接或长任务压缩前，还必须先更新 `PROJECT_STATE.md`。

## 成片不可妥协要求
- 同一时间只显示一张居中的场景图。
- 场景图必须完整展示，不能被字幕、横线、面板、遮罩或预览裁切遮挡。
- 场景图出现后不能持续缩放。
- 场景图入场要有轻微、多变、自然的滑入或上浮效果，不能僵硬地硬切。
- 一个语义分段可以共用一张场景图，对应 1-3 个字幕 cue；任何分段都不能超过 3 个 cue。
- 字幕必须跟每个 cue 变化，不能只展示场景标题或段落首句。
- 中文字幕必须居中；每个 cue 末尾标点要去掉。
- 英文字幕如存在，必须跟同一个 cue 对齐。
- 方框总结必须是 2-4 个字的中文情绪关键词，不能直接截取字幕长句。
- 方框总结在当前语义分段内依次出现；前面的保留到该分段结束。
- 分段切换时，该分段的总结关键词一起消失。
- 禁止出现 `@Sc1火柴人`。
- 右上角固定展示：`心理分享 | 认知突破`。
- 默认使用已确认的参考音色，除非用户明确选择其他声音。
- 音频、中文字幕、英文字幕、场景图、总结关键词必须共用同一套 cue 时间线。

## 开发流程
- 新上下文开始时先读 `PROJECT_STATE.md`，不要凭聊天记忆继续。
- 远程同步、部署、上下文交接前必须更新 `PROJECT_STATE.md`。
- 改动范围要小，优先修现有链路，不新增平行工作流。
- 优先遵循现有 backend、frontend、Remotion 的项目模式。
- 不提交密钥、API key、生成媒体、上传文件、缓存或临时构建产物。
- 项目治理文档统一放在：`AGENTS.md`、`PROJECT_STATE.md`、`rules/`、`specs/`、`docs/`。
- 代码提交要小而清晰。一次提交应该只解决一个可验证问题或补充一组相关文档。

## 必须检查的文件
- `backend/app/services/ai_video.py`：文案规划、SC1 分段、素材匹配、TTS、音频/cue 时间线、渲染 payload。
- `backend/app/api/stickman_workflow.py`：一键生成 API 和平台任务行为。
- `frontend/src/pages/StickmanWorkflow/index.tsx`：前端生成页面、声音/素材选择、进度体验。
- `frontend/src/pages/StickmanWorkflow/StickmanWorkflow.css`：预览、进度、工作流样式。
- `video-render-service/remotion-mind-video/src/remotion/Sc1StickmanVideo.jsx`：最终视频合成、场景图、字幕、关键词、音频播放。
- `docs/心理学火柴人视频复刻文档.md`：用户口径的复刻要求。
- `rules/vibe-coding.md`：日常 AI 编码约束。
- `rules/quality-gates.md`：编码、提交、部署、验收门禁。
- `rules/skill-usage.md`：技能使用规范。
- `rules/agent-orchestration.md`：master agent 分发、review、整合规则。
- `specs/sc1-stickman-workflow-spec.md`：产品和技术规格。
- `specs/development-control-spec.md`：开发流程控制规格。
- `specs/master-agent-workflow-spec.md`：多需求并行开发的 master agent 工作流规格。

## 验证清单
在声明视频工作流修复完成前，必须尽量通过平台完整流程验证，而不是只跑本地脚本：

1. 通过 `http://152.136.218.74:3003` 创建任务。
2. 确认任务状态到达 `completed`。
3. 下载生成的 MP4。
4. 确认 MP4 同时包含视频流和音频流。
5. 在关键 cue 边界和场景切换点抽帧。
6. 检查场景图完整性、字幕居中、总结关键词、右上角标签、无水印。
7. 对照参考视频检查布局、节奏、视觉感觉。
8. 在远程同步或交接前，把验证 job id、输出路径、分支、提交、部署时间记录到 `PROJECT_STATE.md`。

## 远程操作
- SSH 目标：`root@152.136.218.74`
- 优先使用 `scripts/` 中已有远程执行和上传脚本。
- 只重启必要服务：
  - 后端/API 修改：`manim-v2-3003-backend.service`
  - worker/TTS/渲染编排修改：`manim-v2-3003-worker.service`
  - Remotion 渲染修改：`manim-v2-3003-ai-video-render.service`
- 部署后必须检查服务状态，并生成新的平台任务验证。

## 上下文恢复流程
如果未来 agent 失忆或上下文被压缩：

1. 读取本文件。
2. 读取 `PROJECT_STATE.md`。
3. 读取 `rules/vibe-coding.md`。
4. 读取 `rules/quality-gates.md`。
5. 读取 `rules/skill-usage.md`。
6. 读取 `rules/agent-orchestration.md`。
7. 读取 `specs/sc1-stickman-workflow-spec.md`。
8. 读取 `specs/development-control-spec.md`。
9. 读取 `specs/master-agent-workflow-spec.md`。
10. 按最新记录的分支、提交、部署目录和验证结果继续。
11. 不要重新规划整个项目，除非用户明确要求重做。
