# Rebuild Workspace From 3002 Base

目标：

- 不依赖当前本地脏 worktree
- 直接从远程重建一个干净工作区
- 严格以当前 `3002` 最新稳定态作为开发基线
- 让其他 AI 可以拿这份文档直接开始执行

## 结论

如果要基于当前 `3002` 最新版继续开发，统一使用下面这组基线：

- 远程稳定分支：`repro/3002-12fbd6a6`
- 冻结稳定提交：`12fbd6a6e2b1efeea9398421b8205e05af367f32`
- 说明：这是当前 `3002` 对应的稳定快照，也是 `3003` 已复现对齐的基线

不要直接基于当前本地脏 worktree 继续开发。

## 什么时候用这份文档

- 想从远程重新拉一个干净目录
- 想确保开发起点和当前 `3002` 一致
- 想让别的 AI / 别的机器不碰你当前本地工作区，直接开始做事

## 标准做法

推荐做法不是直接在 `repro/3002-12fbd6a6` 上开发，而是：

1. 从远程拉取 `repro/3002-12fbd6a6`
2. 硬定位到提交 `12fbd6a6e2b1efeea9398421b8205e05af367f32`
3. 基于它新建一个自己的开发分支

这样做的原因：

- `repro` 分支负责冻结线上稳定态
- 你的新分支负责继续开发
- 后面如果还要复现/回滚，基线不会被污染

## 推荐分支命名

新开发分支建议命名为：

- `feature/<your-task>-on-3002-base`

例如：

- `feature/fix-english-subtitle-regression-on-3002-base`
- `feature/new-admin-permission-flow-on-3002-base`
- `feature/next-acceptance-iteration-on-3002-base`

## Windows 干净工作区重建步骤

假设新的干净目录是：

- `E:\ai\agent_stickman_v2_3002_clean`

### 1. 克隆仓库

PowerShell：

```powershell
Test-Path -LiteralPath "E:\ai"
git clone git@github.com:mingze-great/manim.git "E:\ai\agent_stickman_v2_3002_clean"
```

### 2. 切到仓库目录

```powershell
Set-Location -LiteralPath "E:\ai\agent_stickman_v2_3002_clean"
```

### 3. 拉取 3002 稳定基线

```powershell
git fetch origin repro/3002-12fbd6a6
git checkout -B repro/3002-12fbd6a6 FETCH_HEAD
git reset --hard 12fbd6a6e2b1efeea9398421b8205e05af367f32
```

### 4. 基于该基线创建新的开发分支

把下面的 `<your-branch-name>` 换成你的实际任务分支名：

```powershell
git checkout -B <your-branch-name>
```

例如：

```powershell
git checkout -B feature/next-acceptance-iteration-on-3002-base
```

### 5. 验证当前基线是否正确

```powershell
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git status -sb
```

预期：

- 当前分支是你刚创建的新开发分支
- `git rev-parse HEAD` 输出：`12fbd6a6e2b1efeea9398421b8205e05af367f32`
- 工作区是干净的

## Linux / 服务器侧干净工作区重建步骤

假设目标目录是：

- `/opt/manim-v2-dev-from-3002`

```bash
git clone git@github.com:mingze-great/manim.git /opt/manim-v2-dev-from-3002
cd /opt/manim-v2-dev-from-3002
git fetch origin repro/3002-12fbd6a6
git checkout -B repro/3002-12fbd6a6 FETCH_HEAD
git reset --hard 12fbd6a6e2b1efeea9398421b8205e05af367f32
git checkout -B feature/next-acceptance-iteration-on-3002-base
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git status -sb
```

## 给其他 AI 的直接执行指令

可以直接把下面这段发给其他 AI：

```text
不要使用当前本地脏工作区。请从远程 GitHub 重建一个干净工作区，并严格以当前 3002 稳定态作为开发基线。

固定基线：
- 远程分支：repro/3002-12fbd6a6
- 固定提交：12fbd6a6e2b1efeea9398421b8205e05af367f32

执行要求：
1. 新建干净目录克隆仓库。
2. fetch origin repro/3002-12fbd6a6。
3. checkout 到 repro/3002-12fbd6a6。
4. hard reset 到 12fbd6a6e2b1efeea9398421b8205e05af367f32。
5. 基于该提交新建一个 feature 分支继续开发，不要直接在 repro 分支上改。
6. 开始开发前输出当前分支名、HEAD 提交和 git status -sb。
```

## 如果你就是要在当前 3002 基线上继续开发

最推荐的实际起点是：

- 基线：`repro/3002-12fbd6a6`
- 提交：`12fbd6a6e2b1efeea9398421b8205e05af367f32`
- 新分支：你自己的 `feature/*-on-3002-base`

不要用下面这些作为“当前 3002 稳定开发起点”：

- 当前本地脏 worktree
- `feature/stickman-v2-viral-hook-optimization-acceptance`

原因：

- `feature/stickman-v2-viral-hook-optimization-acceptance` 现在已经继续前进到文档和运维流程更新
- 它适合继续主开发线，不适合作为“严格对齐当前 3002 线上效果”的冻结起点

## 关联文档

- `docs/REPRO_3002_FROM_REMOTE.md`
- `docs/V2_3002_STANDARD_DEPLOY.md`
- `docs/GITHUB_SSH_PUSH_WORKFLOW.md`
