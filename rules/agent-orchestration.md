# Master Agent 编排规则

## 目标
当用户想同时开发多个需求时，不再依赖手工开多个窗口。一个 master agent 负责明确需求、制定方案、拆分任务、分发给多个 agent、逐项验收、统一整合、最终验收。

多 agent 是复杂任务工具，不是默认开发模式。简单需求、小修小改、单文件调整、明确 bug 修复，应优先使用 `rules/skill-usage.md` 的 L0/L1/L2 流程，不启动 master-agent 编排。

## 角色分工

### Master Agent
- 澄清需求。
- 判断任务是否能并行。
- 写总规格和实施计划。
- 拆分任务边界。
- 分配 worktree、分支、文件范围和验收标准。
- 跟踪每个子任务状态。
- 对每个子任务做独立 review。
- 合并所有子任务。
- 做最终整体验收。
- 更新 `PROJECT_STATE.md`。

### Worker Agent
- 只执行被分配的需求。
- 只读取必要上下文。
- 不改其他 worker 的文件。
- 完成局部验证。
- 提交或输出清晰 diff。
- 向 master 汇报改动、验证结果、风险和剩余问题。

### Reviewer Agent
- 不参与实现。
- 只根据需求、计划、diff、测试结果做审查。
- 输出阻塞问题、重要问题、次要问题。
- 不直接修改代码，除非 master 明确要求。

## 可并行任务的判断
满足以下条件才适合并行：

- 任务目标能独立验收。
- 文件修改范围基本不重叠。
- 数据库迁移、接口契约、共享类型等依赖已明确。
- 可以为每个任务准备独立 worktree 或明确合并顺序。
- 每个任务都有可执行验收标准。
- 并行带来的收益大于分发、review、合并成本。

不适合并行的情况：

- 多个任务都要大改同一个核心文件。
- 需求还没澄清。
- 接口契约没确定。
- 没有测试或验证路径。
- 需要用户连续决策。
- 任务 30 分钟内可由一个 agent 稳定完成。
- 只是文案、样式、小配置或小范围 bugfix。

## 标准流程

1. master 使用 `brainstorming` 明确需求和成功标准。
2. master 使用 `writing-plans` 写总计划。
3. master 把计划拆成互不冲突的任务。
4. master 使用 `using-git-worktrees` 为每个任务创建隔离工作区。
5. master 使用 `subagent-driven-development` 或 `dispatching-parallel-agents` 分发任务。
6. worker 完成实现和局部验证。
7. master 对每个 worker 结果使用 `requesting-code-review`。
8. master 根据 `receiving-code-review` 处理反馈。
9. master 合并所有任务。
10. master 使用 `verification-before-completion` 做整体验收。
11. master 如需部署，执行 `rules/quality-gates.md` 的远程部署门禁。
12. master 更新 `PROJECT_STATE.md`。

## 任务分发模板
每个 worker 必须收到以下内容：

```markdown
# 子任务说明

## 背景
[只给与本任务相关的项目背景]

## 目标
[本任务的用户可见目标]

## 文件范围
- 允许修改：
- 禁止修改：

## 接口约束
[与其他任务共享的接口、类型、数据结构]

## 验收标准
- [ ] 本地验证：
- [ ] 用户可见验证：
- [ ] 不破坏：

## 提交要求
- 提交信息：
- 汇报内容：
```

## 汇报模板
每个 worker 完成后必须汇报：

```markdown
## 完成内容
- 

## 修改文件
- 

## 验证结果
- 命令：
- 结果：

## 风险
- 

## 需要 master 合并/决策
- 
```

## 三种实现方案

### 方案 A：当前 Codex 单窗口 master + subagents
适合：同一个 Codex 会话内协调多个子任务。

做法：
- master 在当前窗口完成需求澄清和计划。
- master 调用 subagent 工具分发任务。
- 子 agent 在后台并行执行。
- master 等待结果、review、合并、最终验收。

优点：
- 不需要用户手动开多个窗口。
- master 上下文集中。
- 适合一次性并行开发。

缺点：
- 需要任务边界清晰。
- 并行修改同一文件会增加合并成本。

### 方案 B：多个 Codex thread/worktree
适合：多个较大需求并行推进，每个需求需要较长上下文。

做法：
- master 创建或指派多个 thread。
- 每个 thread 对应一个需求和一个 worktree。
- master 维护总计划和状态文件。
- 各 thread 完成后由 master 合并。

优点：
- 每个需求上下文独立。
- 长任务更稳定。
- 方便暂停和恢复。

缺点：
- 需要更严格的 `PROJECT_STATE.md` 和分支管理。
- master 需要主动收敛结果。

### 方案 C：项目专属编排 skill
适合：长期反复使用同一套“澄清-分发-验收-部署”流程。

做法：
- 用 `skill-creator` 创建 `3003-master-agent-orchestration`。
- skill 固化读取规则、生成计划、创建 worktree、分发任务、review、整体验收、更新状态。
- 后续只要用户说“按 master agent 流程执行”，就进入标准流程。

优点：
- 最规范，最适合长期维护。
- 减少每次临时约定。
- 能把 3003 特有的素材库、成片验证、远程部署规则写死。

缺点：
- 需要先创建和调试项目专属 skill。

## 推荐
短期推荐方案 A：当前窗口 master + subagents。

中期推荐方案 B：每个大需求一个 thread/worktree。

长期推荐方案 C：创建项目专属 `3003-master-agent-orchestration` skill，把流程固化。
