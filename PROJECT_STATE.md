# 项目状态

## 当前任务
完善本地开发流程文档，让后续 Codex 会话不依赖聊天记忆，也能恢复 3003 SC1 心理学火柴人工作流上下文，并按规范继续开发。

## 当前重点
- 将核心项目文档中文化。
- 明确说明：不能假设每次编码前系统会自动完整读取所有文件，agent 必须主动读取关键文档。
- 补充 `rules/quality-gates.md`，把编码、提交、部署、成片验收做成门禁。
- 补充 `rules/skill-usage.md`，明确哪些工作应使用现成 skill，哪些项目专属 skill 建议创建。
- 补充 `specs/development-control-spec.md`，把需求进入、计划、编码、验证、部署、交接做成闭环规格。
- 更新顶层工作区 `AGENTS.md`，让新上下文能找到真正项目目录。

## 已完成
- `AGENTS.md` 已改成中文，包含项目使命、自动读取边界、成片不可妥协要求、开发流程、验证清单、远程操作、上下文恢复流程。
- `rules/vibe-coding.md` 已改成中文，包含编码前约束、状态管理、改动范围、视频质量、编码风格、测试验证、提交同步规则。
- `rules/quality-gates.md` 已新增，包含编码前、提交前、远程部署前、远程部署后、成片验收、文档验收门禁。
- `rules/skill-usage.md` 已新增，记录当前可用 skill、系统内置能力边界、建议创建的项目专属 skill。
- `specs/sc1-stickman-workflow-spec.md` 已改成中文，固化 3003 一键成片产品规格和验收标准。
- `specs/development-control-spec.md` 已新增，固化开发流程闭环。
- `docs/superpowers/plans/2026-07-24-development-process-docs.md` 已改成中文，并补充质量门禁、skill 使用规范、开发流程控制规格。
- 顶层工作区 `C:\Users\Administrator\Documents\Codex\2026-07-18\300\AGENTS.md` 已改成中文入口说明。

## 当前问题
- 这次是本地文档治理，不涉及 3003 服务重启或远程部署。
- 当前平台运行版本仍以远程部署目录 `/opt/manim-v2-3003-snapshot` 的最新已确认部署为准。

## 可复现锚点
- 当前本地分支：`codex/3003-standalone-stickman-workflow-20260712`
- 本次文档更新前本地提交：`5303d376ea7b8ee9ec0b5e7d99b0ebf85d8ea90b`
- 本次文档更新前提交时间：`2026-07-24 21:23:06 +0800`
- 本次文档更新前提交信息：`docs: add 3003 development process rules`
- 远程部署目录：`/opt/manim-v2-3003-snapshot`
- 最新已确认远程部署 HEAD：`360f19f7bfdc31973f6a097c9fd7132c19765f9b`
- 最新已确认远程部署时间：`2026-07-20 23:54:24 +0800`
- 状态更新时间：`2026-07-24 21:35:49 +08:00`

## 最近修改文件
- `AGENTS.md`
- `PROJECT_STATE.md`
- `rules/vibe-coding.md`
- `rules/quality-gates.md`
- `rules/skill-usage.md`
- `specs/sc1-stickman-workflow-spec.md`
- `specs/development-control-spec.md`
- `docs/superpowers/plans/2026-07-24-development-process-docs.md`
- 顶层工作区文件：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\AGENTS.md`

## 重要技术决策
- 项目文档默认使用中文。
- 不假设 Codex 每次编码前会自动读取 `rules/`、`specs/`、`PROJECT_STATE.md`；文档中要求 agent 主动读取。
- 当前必须优先使用的已安装 skill：`writing-plans`、`byted-text-to-speech`。
- 建议优先创建的项目专属 skill：`sc1-video-validation`、`3003-deploy-sync`、`sc1-requirements-check`。
- 开发流程拆为：读取规则 -> 判断任务类型 -> 使用 skill/写计划 -> 最小改动 -> 验证 -> 更新状态 -> 提交 -> 必要时部署。

## 不要重复做
- 不要重新设计整个 3003 工作流。
- 不要把平台验证替换成一次性本地脚本生成。
- 不要把生成媒体、缓存、storage、uploads 或密钥提交进仓库。
- 不要在未更新 `PROJECT_STATE.md` 的情况下远程同步或交接上下文。

## 下一步
- 提交这次中文化和流程治理文档变更。
- 如果后续要进一步自动化，优先用 `skill-creator` 创建 `sc1-video-validation` 和 `3003-deploy-sync` 两个项目专属 skill。
