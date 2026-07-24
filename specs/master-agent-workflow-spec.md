# Master Agent 工作流规格

## 目标
让用户可以在一个 master agent 窗口中提出多个需求，由 master agent 统一澄清需求、制定方案、拆分任务、分发给多个 agent 并行开发，最后逐项验收、统一整合、整体交付。

## 用户体验目标
用户只需要在一个窗口描述多个需求，例如：

> 同时做 A、B、C 三个需求，按 master agent 流程执行。

master agent 应该：

1. 识别多个需求。
2. 判断哪些能并行，哪些必须串行。
3. 给出方案和任务拆分。
4. 明确每个子任务的验收标准。
5. 分发给多个 worker agent。
6. 跟踪每个任务状态。
7. 对每个结果单独 review。
8. 合并后做整体验收。
9. 必要时部署和生成平台验证结果。

## 流程阶段

### 阶段 1：需求澄清
- 使用 `brainstorming`。
- 目标是把模糊需求变成可验收需求。
- 输出：需求清单、优先级、依赖关系、验收标准。

### 阶段 2：任务拆分
- 使用 `writing-plans`。
- 按模块、文件、接口、验证边界拆分。
- 输出：总计划文档和子任务清单。

### 阶段 3：隔离工作区
- 使用 `using-git-worktrees`。
- 每个并行需求一个 worktree 或分支。
- 输出：每个 worker 的工作区和允许修改文件范围。

### 阶段 4：并行执行
- 使用 `subagent-driven-development` 或 `dispatching-parallel-agents`。
- 每个 worker 只收到自己的任务说明。
- 输出：每个子任务的代码、验证结果、风险说明。

### 阶段 5：逐项验收
- 使用 `requesting-code-review`。
- 使用 `receiving-code-review` 处理反馈。
- 输出：每个子任务是否可合并的结论。

### 阶段 6：统一整合
- master agent 合并所有子任务。
- 解决冲突。
- 运行整体检查。

### 阶段 7：最终验收
- 使用 `verification-before-completion`。
- 如涉及 3003 成片，必须按 `rules/quality-gates.md` 和 `specs/sc1-stickman-workflow-spec.md` 验收。
- 输出：最终验证证据、成片路径或部署结果。

## 任务状态模型
每个子任务必须处于以下状态之一：

- `pending`：已拆分，未开始。
- `in_progress`：worker 正在执行。
- `blocked`：存在阻塞，等待 master 或用户决策。
- `ready_for_review`：worker 完成，等待 review。
- `changes_requested`：review 要求修改。
- `approved`：子任务通过验收。
- `merged`：已合并到 master 工作区。
- `verified`：整体流程验证通过。

## 验收标准
- master agent 有总计划文档。
- 每个 worker 有明确任务说明。
- 每个子任务有独立验证证据。
- 每个子任务经过 review。
- master agent 记录合并和最终验证结果。
- `PROJECT_STATE.md` 记录任务拆分、工作区、提交、验证结论和下一步。

## 失败处理
- 如果任务边界不清晰，回到需求澄清。
- 如果两个 worker 修改冲突，master 决定串行化或拆分共享接口。
- 如果子任务验证失败，退回 worker 修改。
- 如果最终整体验收失败，定位到具体子任务或集成层再修。

## 推荐落地路径
1. 先按方案 A 使用当前 Codex 子 agent 工具试运行。
2. 对稳定流程创建 `3003-master-agent-orchestration` 项目专属 skill。
3. 后续复杂任务统一通过该 skill 执行。
