# 3002 / 3003 Rollback Runbook

目标：

- 当新的优化发布后出现问题时，可以快速、安全地回退
- 区分 `3003` 预发布回退和 `3002` 正式环境回退
- 区分“代码回退”与“按稳定快照重建”
- 避免临时凭记忆操作，降低误覆盖风险

## 这份文档解决什么问题

现有文档可以支持：

- 从远程稳定分支重建
- 标准部署
- 3003 标准重发

但如果你在后续开发中遇到：

- 新功能上线后页面异常
- 接口报错
- worker 异常
- 多模块联调互相污染
- 需要快速恢复到上一稳定状态

更适合直接看这份回退文档，而不是在多份文档里临时拼步骤。

## 先记住一句话

1. `3003` 出问题：优先回退到上一个已验证通过的 `3003` 基线
2. `3002` 出问题：优先回退到最近一个稳定 `repro/3002-*`
3. 如果只是某次发布提交有问题，可以直接回到指定 commit
4. 如果环境已经混乱，优先按稳定分支重新部署，不要手工猜着修

## 当前推荐基线概念

- `3003`：预发布验证环境
- `3002`：正式环境
- `repro/3002-*`：正式环境稳定快照
- `feature/*`：功能开发分支
- `release/3003-current`：建议后续作为 3003 集成验证线

## 回退策略怎么选

### 场景 1：你刚发了一个新优化到 3003，发现有问题

处理方式：

- 直接把 `3003` 回退到“上一个确认正常的 commit / 分支”
- 不要急着动 `3002`

适用：

- 预发布联调失败
- 前端白屏
- 接口 500
- worker 不跑
- SSE / 资源链路异常

### 场景 2：3003 验证通过后发到 3002，结果 3002 出问题

处理方式：

- 直接把 `3002` 回退到最近一个稳定 `repro/3002-*`
- 不要继续在生产机上临时改代码

适用：

- 正式环境接口异常
- 正式页面功能不可用
- 生产任务队列异常
- 生产资源或模板链路异常

### 场景 3：服务器目录已经混乱，不确定现在到底跑的是什么

处理方式：

- 不做增量修补
- 直接按稳定基线重新部署
- 必要时重新 clone / reset / build / restart

适用：

- 分支和 commit 对不上
- dist / app / 静态资源混杂
- 本地工作区污染后误发
- 多次手工覆盖后状态不可信

## 标准回退前检查

无论回退 `3002` 还是 `3003`，都先做这几个检查：

```bash
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
systemctl is-active manim-v2-backend.service || true
systemctl is-active manim-v2-worker.service || true
systemctl is-active manim-v2-3003-backend.service || true
systemctl is-active manim-v2-3003-worker.service || true
```

再至少确认：

- 当前目标机器目录
- 当前运行端口
- 当前目标服务名
- 你要回退到哪个 commit / 哪个 repro 分支

## 3003 回退

### 目标

把 `3003` 回退到最近一次验证通过的基线。

当前目录和服务通常是：

- 目录：`/opt/manim-v2-3003-snapshot`
- 后端服务：`manim-v2-3003-backend.service`
- worker 服务：`manim-v2-3003-worker.service`
- 前端端口：`3003`
- 后端端口：`8003`

### 推荐方式 A：按稳定 commit 回退

如果你知道要回退的 commit，例如：

- `12fbd6a6e2b1efeea9398421b8205e05af367f32`

执行：

```bash
cd /opt/manim-v2-3003-snapshot
git fetch origin
git checkout <branch>
git reset --hard 12fbd6a6e2b1efeea9398421b8205e05af367f32
bash deploy/deploy-v2-3003.sh
```

说明：

- `<branch>` 可以是当前 3003 使用的分支
- 如果后续建议改为 `release/3003-current`，则这里优先切回那个集成分支

### 推荐方式 B：按稳定分支重拉

如果你已经有明确的稳定 3003 集成分支，例如：

- `release/3003-current`

执行：

```bash
cd /opt/manim-v2-3003-snapshot
git fetch origin
git checkout release/3003-current
git reset --hard origin/release/3003-current
bash deploy/deploy-v2-3003.sh
```

### 回退后验证

```bash
curl -fsS http://127.0.0.1:8003/health
curl -I http://127.0.0.1:3003/
cd /opt/manim-v2-3003-snapshot
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
```

至少确认：

- `8003/health` 正常
- `3003` 首页返回 `200`
- 登录正常
- 关键功能链路正常

## 3002 回退

### 目标

把正式环境快速恢复到最近一个稳定快照。

当前正式环境通常是：

- 目录：`/opt/manim-v2`
- 后端服务：`manim-v2-backend.service`
- worker 服务：`manim-v2-worker.service`
- 前端端口：`3002`
- 后端端口：`8002`

### 推荐方式：直接回退到稳定 repro 分支

例如当前稳定快照是：

- `repro/3002-12fbd6a6`

执行：

```bash
cd /opt/manim-v2
git fetch origin repro/3002-12fbd6a6
git checkout repro/3002-12fbd6a6
git reset --hard origin/repro/3002-12fbd6a6
```

然后按正式部署文档重新部署：

- 参考 `docs/V2_3002_STANDARD_DEPLOY.md`

如果当前服务器就是走 Git 拉取部署，也可以在 reset 后重新 build / restart。

### 回退后验证

```bash
curl -fsS http://127.0.0.1:8002/health
curl -I http://127.0.0.1:3002/
cd /opt/manim-v2
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
```

至少确认：

- `8002/health` 正常
- `3002` 首页返回 `200`
- 登录正常
- 关键业务流程恢复

## 如果只是本地开发分支做坏了

如果问题只在本地工作区，还没发到服务器：

1. 不要污染当前工作区继续修
2. 直接从稳定基线新建一个新的工作区
3. 把需要的改动有选择地摘过去

例如你现在推荐的方式就是：

- 基线工作区保持干净
- 每个模块一个独立工作区
- 每个模块一个独立 `feature/*` 分支

这样本地“回退”的正确方式通常不是硬救脏分支，而是：

- 重新从稳定基线开一个新工作区继续做

## 什么时候直接看 repro 文档就够了

如果你的目标是：

- 在新机器上恢复稳定版
- 在新目录上复刻稳定版
- 彻底摆脱当前混乱工作区

那直接使用下面文档就够：

- `docs/REPRO_3002_FROM_REMOTE.md`
- `docs/V2_3002_STANDARD_DEPLOY.md`
- `docs/V2_3003_DEPLOY_RUNBOOK.md`

也就是说：

- “恢复稳定状态”可以看 repro / deploy 文档
- “线上出了问题要快速撤回”更建议直接看这份 rollback runbook

## 最推荐的长期做法

为了让回退始终简单，后续固定遵守这几条：

1. 不要在脏工作区直接发布
2. 每个模块独立 worktree / workspace
3. `3003` 只做集成验证
4. `3002` 只接收已经在 `3003` 验证通过的内容
5. 每次 `3002` 发布成功后，都新建一个新的 `repro/3002-<sha7>`
6. 不要覆盖旧的 repro 分支

这样回退时你永远只需要回答一个问题：

“我要退回哪个稳定快照？”

而不是：

“服务器现在到底被我改成什么样了？”

## 关联文档

- `docs/REPRO_3002_FROM_REMOTE.md`
- `docs/V2_3002_STANDARD_DEPLOY.md`
- `docs/V2_3003_DEPLOY_RUNBOOK.md`
- `docs/V2_3003_REMOTE_REDEPLOY_VERIFICATION.md`
