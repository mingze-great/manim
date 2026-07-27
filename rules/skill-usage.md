# Skill 使用规范

## 目标

减少流程噪音，只保留当前项目真正高频、能提升交付质量的 skills。小需求不启用完整流程；只有需求不清晰、需要 UI 验证、素材库生成或最终验收时才使用对应 skill。

## 当前保留的自定义 skills

- `brainstorming`：用于需求分析、产品设计、方案取舍。只有需求较大、边界不清晰、UI/商业/流程需要先定方案时使用；小修小补不强制使用。
- `requesting-code-review`：用于重要功能完成后的代码 review。小改动可用普通自查替代；涉及鉴权、上传、生成链路、部署时建议使用。
- `verification-before-completion`：用于声明完成前的验收。凡是要说“已完成、已修复、平台可用”，必须先有新鲜验证证据。
- `material-library-generator`：用于参考图生成素材库、两张样图确认、批量素材和 `materials.json` 生成。只在素材库生成/验证任务中使用。
- `playwright`：用于真实浏览器验证平台 UI、截图、交互问题定位。API 能证明的问题优先用 API；UI 展示、按钮、预览、音频试听等问题再用它。

## 已归档的 skills

以下 skills 已从活动目录移到 `C:\Users\Administrator\.codex\skills-disabled\20260727-pruned`，默认不再触发：

- `using-superpowers`
- `systematic-debugging`
- `test-driven-development`
- `writing-plans`
- `executing-plans`
- `dispatching-parallel-agents`
- `subagent-driven-development`
- `using-git-worktrees`
- `receiving-code-review`
- `finishing-a-development-branch`
- `byted-text-to-speech`
- `akshare-stock`
- `notion-spec-to-implementation`
- `screenshot`
- `security-best-practices`
- `security-threat-model`

说明：`test-driven-development` 目录因 Windows 占用未能整体移动，但其中的 `SKILL.md` 已移入归档目录，因此不会再作为可用 skill 加载。

## 选择规则

### 简单需求

例如文案调整、单个样式微调、小 bug、小接口字段修复：

1. 直接读相关文件。
2. 实施最小改动。
3. 跑最小验证命令。
4. 必要时更新 `PROJECT_STATE.md`。

不使用多 agent，不写长计划，不创建额外 spec。

### 中等需求

例如前后端都要改、影响用户可见流程、涉及套餐/权限/素材库/生成参数：

1. 简短说明方案。
2. 实施改动。
3. 跑后端测试、前端 build 或目标验证。
4. 用 `verification-before-completion` 的标准给出证据。

只有需求本身还不清晰时才使用 `brainstorming`。

### 复杂需求

例如重构火柴人成片流程、改部署结构、改合作者商业链路、大范围 UI 改版：

1. 先用 `brainstorming` 明确目标、边界和成功标准。
2. 编码完成后用 `requesting-code-review` 或等价代码审查。
3. 部署前后必须更新 `PROJECT_STATE.md`。
4. 平台真实闭环验证，不能只用本地脚本替代。

### 素材库需求

涉及“参考图片生成一套素材库”“两张样图确认”“生成 `materials.json`”时使用 `material-library-generator`。默认要求：

- 两张样图先确认。
- 背景以白色、干净、低干扰为主。
- 中间人物明确，允许少量道具/场景衬托。
- 输出结构为编号 PNG 加 UTF-8 `materials.json`。

## 不再做的事

- 不因为有 skill 就强制每轮使用。
- 不再让 `using-superpowers` 接管所有对话。
- 不为小需求启动多 agent/worktree 流程。
- 不用已归档 skill 写冗长计划，除非用户明确要求恢复。

## 恢复方式

如果后续需要恢复某个 skill，把对应目录从：

`C:\Users\Administrator\.codex\skills-disabled\20260727-pruned`

移回：

`C:\Users\Administrator\.codex\skills`

下一轮 Codex 上下文通常就会重新识别。
