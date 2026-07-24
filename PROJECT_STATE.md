# 项目状态

## 当前任务
完善本地开发流程文档和 skills 体系，让后续 Codex 会话可以按“需求澄清 -> 计划 -> 并行分发 -> 子任务验收 -> 统一整合 -> 最终验收”的 master agent 流程开发。

## 当前重点
- 将核心项目文档中文化。
- 明确说明：不能假设每次编码前系统会自动完整读取所有文件，agent 必须主动读取关键文档。
- 补充 `rules/quality-gates.md`，把编码、提交、部署、成片验收做成门禁。
- 补充 `rules/skill-usage.md`，明确哪些工作应使用现成 skill，哪些项目专属 skill 建议创建。
- 补充 `specs/development-control-spec.md`，把需求进入、计划、编码、验证、部署、交接做成闭环规格。
- 从网络安装开发流程、代码评审、并行 agent、浏览器验证、安全审查等可复用 skills。
- 补充 `rules/agent-orchestration.md` 和 `specs/master-agent-workflow-spec.md`，定义 master agent 多需求并行开发流程。
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
- 已从 `openai/skills` 安装：`notion-spec-to-implementation`、`playwright`、`screenshot`、`security-best-practices`、`security-threat-model`。
- 已从 `obra/superpowers` 安装：`brainstorming`、`executing-plans`、`subagent-driven-development`、`requesting-code-review`、`receiving-code-review`、`verification-before-completion`、`dispatching-parallel-agents`、`using-git-worktrees`、`systematic-debugging`、`test-driven-development`、`finishing-a-development-branch`、`using-superpowers`。
- `rules/skill-usage.md` 已更新，明确每个已安装 skill 的使用时机。
- `rules/agent-orchestration.md` 已新增，定义 master agent、worker agent、reviewer agent 的职责、任务分发模板和三种实现方案。
- `specs/master-agent-workflow-spec.md` 已新增，定义多需求并行开发的 master agent 工作流规格。

## 当前问题
- 这次是本地 skills 安装和文档治理，不涉及 3003 服务重启或远程部署。
- 当前平台运行版本仍以远程部署目录 `/opt/manim-v2-3003-snapshot` 的最新已确认部署为准。
- 新安装的 skills 通常从下一轮对话开始稳定出现在可用 skills 列表中。

## 可复现锚点
- 当前本地分支：`codex/3003-standalone-stickman-workflow-20260712`
- 本次 skills/编排文档更新前本地提交：`c1a9b90e49a75d12782e8579a177dde6c83a28e5`
- 本次 skills/编排文档更新前提交时间：`2026-07-24 21:39:15 +0800`
- 本次 skills/编排文档更新前提交信息：`docs: localize development controls`
- 远程部署目录：`/opt/manim-v2-3003-snapshot`
- 最新已确认远程部署 HEAD：`360f19f7bfdc31973f6a097c9fd7132c19765f9b`
- 最新已确认远程部署时间：`2026-07-20 23:54:24 +0800`
- 状态更新时间：`2026-07-24 21:54:16 +08:00`

## 最近修改文件
- `AGENTS.md`
- `PROJECT_STATE.md`
- `rules/vibe-coding.md`
- `rules/quality-gates.md`
- `rules/skill-usage.md`
- `rules/agent-orchestration.md`
- `specs/sc1-stickman-workflow-spec.md`
- `specs/development-control-spec.md`
- `specs/master-agent-workflow-spec.md`
- `docs/superpowers/plans/2026-07-24-development-process-docs.md`
- 顶层工作区文件：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\AGENTS.md`

## 重要技术决策
- 项目文档默认使用中文。
- 不假设 Codex 每次编码前会自动读取 `rules/`、`specs/`、`PROJECT_STATE.md`；文档中要求 agent 主动读取。
- 当前必须优先使用的已安装流程类 skill：`brainstorming`、`writing-plans`、`executing-plans`、`subagent-driven-development`、`dispatching-parallel-agents`、`using-git-worktrees`、`requesting-code-review`、`receiving-code-review`、`verification-before-completion`。
- 当前可用于验证/安全/产品规格的 skill：`playwright`、`screenshot`、`notion-spec-to-implementation`、`security-best-practices`、`security-threat-model`、`byted-text-to-speech`。
- 建议优先创建的项目专属 skill：`sc1-video-validation`、`3003-deploy-sync`、`sc1-requirements-check`、`3003-master-agent-orchestration`。
- 多需求并行开发推荐使用：master agent + `brainstorming` + `writing-plans` + `using-git-worktrees` + `subagent-driven-development` + `requesting-code-review` + `verification-before-completion`。
- 开发流程拆为：读取规则 -> 判断任务类型 -> 使用 skill/写计划 -> 分发或最小改动 -> 验证 -> review -> 更新状态 -> 提交 -> 必要时部署。

## 不要重复做
- 不要重新设计整个 3003 工作流。
- 不要把平台验证替换成一次性本地脚本生成。
- 不要把生成媒体、缓存、storage、uploads 或密钥提交进仓库。
- 不要在未更新 `PROJECT_STATE.md` 的情况下远程同步或交接上下文。
- 不要在多需求并行开发时让多个 worker 同时修改同一批核心文件，除非先建立 worktree 和合并策略。

## 下一步
- 提交这次 skills 安装记录和 master agent 编排文档变更。
- 如果后续要进一步自动化，优先用 `skill-creator` 创建 `sc1-video-validation`、`3003-deploy-sync` 和 `3003-master-agent-orchestration`。
