# 开发流程控制规格

## 目标
让 3003 SC1 项目的开发过程可控、可复现、可验证。任何功能开发、问题修复、部署同步、文档治理都必须进入统一流程。

## 文档分工
- `AGENTS.md`：项目长期规则，回答“这个项目是什么、不能破坏什么、进入项目先读什么”。
- `PROJECT_STATE.md`：当前状态，回答“现在做到哪里、最近改了什么、下一步是什么”。
- `rules/vibe-coding.md`：日常编码纪律，回答“AI 协作开发时怎么避免跑偏”。
- `rules/quality-gates.md`：门禁清单，回答“什么时候算可以提交、部署、验收”。
- `rules/skill-usage.md`：技能规范，回答“哪些工作应复用 skill，不要临时发挥”。
- `rules/agent-orchestration.md`：master agent 编排规则，回答“多个需求如何分发、review、整合”。
- `specs/sc1-stickman-workflow-spec.md`：产品规格，回答“最终成片必须满足什么”。
- `specs/development-control-spec.md`：流程规格，回答“开发过程如何闭环”。
- `specs/master-agent-workflow-spec.md`：多 agent 并行开发规格，回答“master agent 工作流如何验收”。
- `docs/superpowers/plans/`：实施计划，回答“复杂任务具体怎么拆步执行”。

## 任务进入流程
每个新任务先判断类型：

1. L0 轻量问答/文档：只问方案、解释流程，或只改少量文档。
2. L1 小修小改：单文件或少量文件，目标明确，不改接口契约。
3. L2 中等功能：跨两个以上模块，但需求清楚、可单独验收。
4. L3 复杂链路/远程部署：影响成片链路、平台完整流程或远程服务。
5. L4 多需求并行：用户希望同时开发多个需求，并由 master agent 统一分发和验收。

不同类型执行不同最低要求：

- L0：读取 `AGENTS.md` 和相关规则，提交前运行 `git diff --check`。
- L1：读取相关 rules/specs，运行对应最小验证；不默认使用多 agent。
- L2：需求不清时使用 `brainstorming`；跨模块时使用 `writing-plans`；完成后做 review 或等价检查。
- L3：必须更新 `PROJECT_STATE.md`；影响平台时必须生成或验证平台成片；部署后记录远程 HEAD 和验证结果。
- L4：必须读取 `rules/agent-orchestration.md` 和 `specs/master-agent-workflow-spec.md`，先拆分任务边界，再决定使用 subagent、thread、worktree 或串行执行。

## 编码流程
1. 读取项目规则和当前状态。
2. 明确本次任务的用户可见目标。
3. 搜索现有实现和历史文档。
4. 按 `rules/skill-usage.md` 判断任务复杂度和需要使用的 skills。
5. 如果是 L0/L1，走轻量核心流程，不默认写长计划或启用多 agent。
6. 如果是 L2/L3，按需写计划到 `docs/superpowers/plans/`。
7. 如果是 L4，按 `rules/agent-orchestration.md` 分发给 worker agent。
8. 做最小可验证修改。
9. 运行本地检查。
10. 如果影响成片，生成或验证平台成片。
11. 更新 `PROJECT_STATE.md`。
12. 提交。

## 验证流程
验证分三层：

### 本地静态验证
- `git diff --check`
- Python 语法检查
- 前端/Remotion 静态检查或构建检查
- 文档占位词检查

### 平台功能验证
- 通过 3003 创建任务。
- 任务状态到达 `completed`。
- 下载 MP4。
- 检查音视频流。
- 抽关键帧。

### 产品质量验证
- 对照参考视频看布局、节奏、字幕、场景图、关键词。
- 检查之前失败过的问题是否复现。
- 把验证结果写入 `PROJECT_STATE.md`。

## 部署流程
1. 更新 `PROJECT_STATE.md`。
2. 提交本地改动。
3. 确认分支和提交。
4. 同步远程代码。
5. 只重启必要服务。
6. 检查服务状态。
7. 通过平台创建验证任务。
8. 下载并检查成片。
9. 记录远程 HEAD、job id、输出路径、验证结论。

## 上下文交接流程
在上下文压缩、任务暂停、切换 agent 或远程同步前，`PROJECT_STATE.md` 必须包含：

- 当前任务
- 已完成内容
- 当前问题
- 最近修改文件
- 下一步计划
- 重要技术决策
- 不要重复做的事情
- 当前分支和提交
- 远程部署目录和远程 HEAD
- 最近一次验证 job id 和成片路径

## 可控性验收标准
- 新 agent 只读项目文档，不看历史聊天，也能继续当前任务。
- 每次远程部署都能追溯到分支、提交、文件、服务和验证 job。
- 每个成片修复都有抽帧或平台任务作为证据。
- 每个复杂任务都有计划文档。
- 每个新增规则都有对应的执行位置或验收门禁。
- 每个多需求并行任务都有 master agent 计划、worker 任务说明、逐项 review 和整体验收记录。
