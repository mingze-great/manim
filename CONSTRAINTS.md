# 项目全局约束文档

> 本文档定义了项目开发过程中必须遵循的全局约束。所有操作必须在此约束基础上执行。

---

## 一、分支管理

| 分支名 | 用途 | 说明 |
|--------|------|------|
| `main` | **主分支（生产）** | 生产环境部署分支，稳定版本 |
| `develop` | **开发分支** | 开发环境部署分支，日常开发使用 |
| `feature/*` | 功能分支 | 新功能开发 |
| `feature/article-generation` | 公众号文章生成 | 已保留，待合并 |

**规则：**
1. 所有新功能开发在 `develop` 分支或功能分支进行
2. **开发完成后，先部署到开发环境测试**
3. **用户确认无误后，才能合并到 `main` 并部署到生产环境**
4. `main` 分支只接受用户确认后的合并
5. **永远不要直接修改生产环境服务器（152.136.218.74）**

### 1.1 V2.0 当前标准分支

- `feature/v2-ui-mobile-ux-recover-3003` 作为当前 `v2.0` 标准分支
- 该分支用于复现并部署当前新版 `3003/8003` 的完整行为
- 当前 `3003` 重部署、模板视频跨端口预览、思维可视化对话流式、后台/个人中心/脚本页布局优化，均以该分支为准

### 1.2 V2 后续优化强制流程

后续所有 `v2` 优化、修复、页面调整，必须遵守以下流程，避免本地工作区污染线上版本：

1. **先从当前有效 v2 基线分支新建专用分支**
   - 示例：`feature/v2-xxx-optimization`
   - 不允许直接在已有脏工作区或未整理分支上继续堆改动

2. **新分支创建后立即推送到远程**
   - 目的是先固定基线，保证可回退、可复现、可审计

3. **所有后续优化必须及时提交并推送到远程**
   - 不允许只留在本地工作区
   - 不允许长期依赖“服务器热修但仓库没有”的状态

4. **部署必须以远程分支为来源**
   - 标准做法：服务器 `git fetch` / `git checkout` / `git reset --hard origin/<branch>`
   - 不允许把“本地未推送代码”作为唯一部署来源

5. **只有满足下面条件，才允许认定某个 v2 分支为可部署基线**
   - 已提交到 git
   - 已推送到远程
   - 已按远程分支部署验证通过

6. **运行态配置也要尽量仓库化**
   - nginx 配置文件
   - service 文件
   - deploy 脚本
   - runbook 文档

7. **非 git 数据资产必须有明确同步策略**
   - 例如模板示例视频共享目录
   - 必须通过脚本或文档说明，不能靠人工记忆

### 1.3 远程连接与服务器操作标准

后续所有远程服务器操作，统一遵守以下规则：

1. **统一使用直接连接服务器的方式执行**
   - 默认目标：
     - 生产：`152.136.218.74`
     - 开发：`106.52.166.109`
   - 优先使用可脚本化、可复现的直连方式
   - 不依赖本机临时交互、手工复制粘贴、多窗口人工操作

2. **优先使用仓库内的远程执行/上传脚本**
   - 如：
     - `scripts/remote_exec.py`
     - `scripts/upload_file_remote.py`
   - 目标是让远程操作可重复、可审计、可回放

3. **不要把“只在当前机器上能用的本地连接习惯”当成标准流程**
   - 例如仅依赖本地 SSH alias、临时 agent 状态、手动 shell 会话
   - 标准流程必须能写进脚本或文档并复现

4. **所有正式部署都必须优先使用仓库内的 deploy 脚本或 runbook**
   - 例如：
     - `deploy/deploy-v2-3003.sh`
     - `docs/V2_3003_DEPLOY_RUNBOOK.md`
   - 若线上临时热修不可避免，后续必须回收进仓库

5. **远程服务器运行态变更必须留痕**
   - 例如：
     - nginx 配置
     - systemd service
     - 共享目录策略
   - 必须写入仓库中的配置、脚本或文档，不能只停留在人工记忆中

**部署前合并流程：**
```bash
# 1. 提交当前分支的更改
git add . && git commit -m "feat: xxx"

# 2. 推送当前分支
git push origin feature/template-preview-video

# 3. 切换到 main 并合并
git checkout main
git merge feature/template-preview-video

# 4. 推送 main
git push origin main

# 5. 切回开发分支继续开发
git checkout feature/template-preview-video
```

---

## 二、服务器架构（当前真实结构）

### 生产环境（152.136.218.74）
| 站点 | 路径 | 分支 | 入口 | 后端 | 说明 |
|------|------|------|------|------|------|
| 旧站 | `/opt/manim` | `feature/legacy-v2-redirect` | `/` | `8000` | 旧版业务 + 版本分流能力 |
| 新站 | `/opt/manim-v2` | `feature/chat-style-and-reference-code` | `3002` | `8002` | 新版业务 |
| V2.0 测试站 | `/opt/manim-v2-3003-snapshot` | `feature/v2-ui-mobile-ux-recover-3003` | `3003` | `8003` | 当前 v2.0 标准验证环境 |

其他说明：
- 新站服务：`manim-v2-backend.service`
- 新站 worker：`manim-v2-worker.service`
- 新站队列：`manim_v2`
- V2.0 测试站 backend service：`manim-v2-3003-backend.service`
- V2.0 测试站 worker service：`manim-v2-3003-worker.service`
- V2.0 测试站队列：`manim_v2_3003`
- 模板示例视频共享目录：`/opt/manim/shared/videos/template_examples`
- 生产数据库：`/opt/manim/backend/manim.db`
- 生产域名：`https://manim.asia`

### 开发环境（106.52.166.109）
| 站点 | 路径 | 分支 | 入口 | 后端 | 说明 |
|------|------|------|------|------|------|
| 新站 | `/opt/manim-dev` | `feature/chat-style-and-reference-code` | `3000` | `8001` | 开发新版 |
| 旧站 | `/opt/manim-legacy` | `feature/legacy-v2-redirect` | `3002` | `8002` | 开发旧版 |

数据库：
- 开发数据库：`/opt/manim-dev/backend/manim_dev.db`
- 开发新旧站共用这份开发数据库

### 数据库独立性
```
生产环境数据库：/opt/manim/backend/manim.db
开发环境数据库：/opt/manim-dev/backend/manim_dev.db

✅ 生产 / 开发 两套数据库物理隔离
✅ 生产新旧站共用生产数据库
✅ 开发新旧站共用开发数据库
```

### 版本分流规则
```
1. 登录成功后按版本分流
2. 刷新浏览器后立即按版本分流
3. 在线用户每 30 秒重新获取 /auth/me 并自动切版本
4. 管理员永远进入新版
5. 普通 legacy 用户进入旧版
6. 普通 v2 用户进入新版
```

### 新旧版构建/部署检查清单
```
[旧站 legacy]
1. 当前分支必须是 feature/legacy-v2-redirect
2. 入口必须保持 http://<host>/
3. 前端资源必须是 /assets/...
4. API 必须是 /api/...
5. 登录成功 / 刷新恢复 / 30秒轮询 都要把管理员和 v2 用户跳到 http://<host>:3002
6. 首页 index.html 必须包含预分流脚本

[新版 v2]
1. 当前分支必须是 feature/chat-style-and-reference-code
2. 入口必须是 http://<host>:3002/
3. 前端资源必须是 /assets/...
4. API 必须是 /api/...
5. 不允许继续使用 /v2、/v2/api、/v2/assets 作为运行时前缀
6. 登录成功 / 刷新恢复 / 30秒轮询 都要把 legacy 用户跳回 http://<host>/

[发布前必须核对]
1. 旧站产物不能发布到 /opt/manim-v2/frontend/dist
2. 新版产物不能发布到 /opt/manim/frontend/dist
3. 旧站 bundle 必须包含 frontend_version / is_admin / 3002 跳转逻辑
4. 新版 bundle 必须包含 chat/async / chat-styles / latest-task，并且请求必须落到当前站点 /api
5. 生产发布后必须直接验证：
   - http://<host>/
   - http://<host>:3002/
   - /api/auth/login
   - :3002/api/auth/login
   - 管理员从旧站登录是否跳 3002/admin
```

### 历史问题警示（每次发布前必须复查）
```
1. 新旧版不能混用构建产物
   - 旧站发布前检查 index.html 必须引用 /assets/...
   - 新站发布前检查 index.html 必须引用 /assets/...
   - 新站绝不能继续使用 /v2/assets 或 /v2/api 作为最终生产入口

2. 新版生产入口固定为 3002 端口
   - 新版页面的所有请求都必须落到 http://<host>:3002/api/...
   - 如果浏览器里仍然请求 http://<host>/api/...，说明新版前端包没有更新成功

3. 旧站首页必须包含预分流脚本
   - 管理员 / v2 用户访问根站时，必须在 React 启动前就跳 3002

4. 新版聊天体验要求
   - 文案生成必须是流式输出
   - 不允许把聊天主体验退化成后台轮询任务
   - 发布前检查新版 bundle 中必须包含 chat/stream / sendMessageStream

5. 模板展示检查
   - 发布前检查 /api/templates/active（旧站）与 :3002/api/templates/active（新站）都返回 200
   - 页面如显示“暂无该分类模板”，先确认接口有数据，再检查前端筛选逻辑

6. 渲染环境检查
   - 新版渲染必须复用生产可用的 Manim 环境
   - 发布前检查 3002 后端所在环境能找到 manim 或 python -m manim
   - 首次进入渲染页时状态必须是“未开始”，按钮必须是“开始渲染视频”
```

### 环境数据差异
| 数据表 | 生产环境 | 开发环境 |
|--------|---------|---------|
| users | 26 (含管理员) | 26 (复制) |
| templates | 17 | 17 (复制) |
| projects | 99 | 0 (已清理) |
| articles | 7 | 0 (已清理) |
| conversations | 117 | 0 (已清理) |

---

## 三、开发流程约束

### 3.1 核心约束（必须遵守）

**⛔ 第一优先级：绝对不影响生产环境**
```
1. ❌ 禁止直接修改生产环境服务器（152.136.218.74）
2. ❌ 禁止在生产环境数据库做任何修改
3. ❌ 禁止在生产环境测试未确认的功能
4. ❌ 禁止在生产环境部署未测试的代码
```

**✅ 正确的开发流程：**
```
1. ✅ 所有优化在 develop 分支进行
2. ✅ 部署到开发环境（106.52.166.109）测试
3. ✅ 在开发环境完整测试所有功能
4. ✅ 用户确认无误后，合并到 main
5. ✅ 用户确认后，部署到生产环境（152.136.218.74）
```

### 3.2 开发环境部署流程

**后端部署：**
```bash
# 1. 停止开发环境后端
ssh root@106.52.166.109 "kill $(cat /opt/manim-dev/logs/backend.pid)"

# 2. 更新代码（从本地或 Git）
ssh root@106.52.166.109 "cd /opt/manim-dev && git pull origin develop"

# 3. 清理缓存
ssh root@106.52.166.109 "cd /opt/manim-dev/backend && find . -type d -name '__pycache__' -exec rm -rf {} +"

# 4. 启动后端
ssh root@106.52.166.109 "cd /opt/manim-dev/backend && \
  nohup /opt/manim-dev/backend/venv/bin/python -m uvicorn app.main:app \
  --host 0.0.0.0 --port 8001 > /opt/manim-dev/logs/backend.log 2>&1 & \
  echo \$! > /opt/manim-dev/logs/backend.pid"
```

**前端部署：**
```bash
# 1. 本地构建
cd frontend && npm run build

# 2. 上传到开发环境
scp -r frontend/dist/* root@106.52.166.109:/opt/manim-dev/frontend/dist/

# 3. 重载 Nginx
ssh root@106.52.166.109 "systemctl reload nginx"
```

### 3.3 生产环境部署流程（用户确认后）

```bash
# ⚠️ 仅在用户确认后才执行

# 1. 合并代码
git checkout main
git merge develop
git push origin main

# 2. 部署到生产环境
ssh root@152.136.218.74 "cd /opt/manim && git pull origin main"
ssh root@152.136.218.74 "systemctl restart manim-backend"

# 3. 上传前端（如有修改）
scp -r frontend/dist/* root@152.136.218.74:/opt/manim/frontend/dist/
ssh root@152.136.218.74 "systemctl reload nginx"
```

---

## 四、账号信息（开发环境 & 生产环境）

**说明：开发环境和生产环境账号相同（数据库复制）**

### 管理员账号
| 项目 | 值 |
|------|-----|
| 用户名 | `admin` |
| 密码 | `admin123` |
| 邮箱 | `admin@manim.com |

### 测试账号
| 用户名 | 箱 | 权限 | 可用环境 |
|--------|------|------|---------|
| admin | admin@manim.com | 管理员 | 开发 + 生产 |
| myoung | mylcsd@163.com | 普通用户 | 开发 + 生产 |
| G先生 | 252345415@qq.com | 普通用户 | 开发 + 生产 |

---

## 五、平台命名规范

| 原名称 | 新名称 | 说明 |
|--------|--------|------|
| AI视频 | 思维可视化 | 全局替换，除 AI 对话功能外 |

---

## 六、已完成功能清单

| # | 功能 | 状态 | 文件 |
|---|------|------|------|
| 1 | 时间显示修复（UTC转本地时间） | ✅ 已完成 | 多处 |
| 2 | 用户时长设置（1周/1月/3月/6月/1年/自定义） | ✅ 已完成 | AdminUsers.tsx, admin.py |
| 3 | 过期用户自动禁用定时任务 | ✅ 已完成 | cleanup.py |
| 4 | 作品批量删除功能 | ✅ 已完成 | History/index.tsx, projects.py |
| 5 | 统计可视化页面 | ✅ 已完成 | AdminStatistics.tsx, admin.py |
| 6 | 移除邀请码管理 | ✅ 已完成 | 多处 |
| 7 | 平台名称替换 | ✅ 已完成 | 多处 |
| 8 | 代码生成联动修复（final_script） | ✅ 已完成 | chat.py |
| 9 | 视频渲染进度条修复 | ✅ 已完成 | ProjectTask.tsx |
| 10 | 代码模板选择功能 | ✅ 已完成 | ProjectTask.tsx, AdminTemplates.tsx |
| 11 | 生成代码和视频按钮 | ✅ 已完成 | ProjectChat.tsx |

---

## 七、待完成功能

| # | 功能 | 优先级 | 状态 |
|---|------|--------|------|
| 1 | 完整流程测试 | 高 | 待测试 |
| 2 | 代码模板功能完整测试 | 中 | 待测试 |
| 3 | 服务器数据库迁移（添加 statistics 表） | 中 | 待执行 |

---

## 八、关键代码位置

### 前端
```
frontend/src/pages/
├── ProjectChat.tsx      # 对话页面，生成代码按钮
├── ProjectTask.tsx      # 任务页面，代码生成/视频渲染
├── admin/
│   ├── AdminUsers.tsx   # 用户管理
│   ├── AdminTemplates.tsx # 模板管理
│   └── AdminStatistics.tsx # 数据统计
└── History/index.tsx    # 作品列表，批量删除
```

### 后端
```
backend/app/
├── api/
│   ├── tasks.py         # 代码生成、视频渲染 API
│   ├── auth.py          # 登录认证
│   ├── projects.py      # 项目管理
│   └── admin.py         # 管理后台 API
├── services/
│   ├── chat.py          # 对话服务，final_script 联动
│   └── manim.py         # Manim 代码生成
├── tasks/
│   └── cleanup.py       # 定时任务
└── models/
    ├── user.py          # 用户模型
    ├── template.py      # 模板模型
    └── statistics.py    # 统计数据模型
```

---

## 九、约束规则（核心）

### 9.1 开发约束（最高优先级）

**⛔ 生产环境保护（绝对不能违反）**
```
1. ❌ 禁止直接修改生产环境（152.136.218.74）
2. ❌ 禁止在生产环境测试未确认的功能
3. ❌ 禁止绕过开发环境直接部署到生产环境
4. ❌ 禁止在生产环境数据库做任何修改
```

**✅ 正确流程（必须遵守）**
```
1. ✅ 所有优化在 develop 分支进行
2. ✅ 部署到开发环境（106.52.166.109）测试
3. ✅ 用户确认无误后，才能合并到 main
4. ✅ 用户确认后，才能部署到生产环境（152.136.218.74）
```

### 9.2 代码修改约束

1. **最小修改原则**：修改某个功能时，只能改动该功能相关的代码，**绝对不能修改其他已有的功能代码**
2. **不添加注释**：除非用户明确要求
3. **保持数据完整**：不删除数据库中的用户数据
4. **本地测试优先**：所有修改先在本地测试，确认无误后再部署到开发环境

### 9.3 部署约束

**开发环境部署：**
```bash
# 后端
ssh root@106.52.166.109 "systemctl restart manim-dev"

# 前端
cd frontend && npm run build
scp -r frontend/dist/* root@106.52.166.109:/opt/manim-dev/frontend/dist/
ssh root@106.52.166.109 "systemctl reload nginx"
```

**生产环境部署（仅用户确认后）：**
```bash
# ⚠️ 必须用户确认后才执行
ssh root@152.136.218.74 "systemctl restart manim-backend"
```

### 9.4 数据库约束

1. **两个数据库完全独立**：
   - 生产：`/opt/manim/backend/manim.db`
   - 开发：`/opt/manim-dev/backend/manim_dev.db`
   
2. **开发环境数据库操作**：
   - 可以修改、测试、清理
   - 不影响生产环境
   
3. **生产环境数据库**：
   - ❌ 禁止修改表结构
   - ❌ 禁止删除数据
   - ✅ 仅读取或备份

### 9.5 分支合并规范

1. **最小修改原则**
   - 修改时不要动之前已有的分支
   - 不要修改需求之外的内容
   - 修改某个功能时，只能改动该功能相关的代码

2. **分支及时合并**
   - 功能开发完成后，先部署到开发环境测试
   - 用户确认无误后，合并到 main 分支
   - 保证所有更新内容不会在下一次更新时丢失

3. **合并流程**
   ```bash
   # 开发完成后
   git checkout develop
   git merge feature/xxx
   git push origin develop
   
   # 部署到开发环境测试
   # 用户确认后
   
   git checkout main
   git merge develop
   git push origin main
   
   # 部署到生产环境（用户确认）
   ```

---

## 十、更新日志

| 日期 | 更新内容 |
|------|----------|
| 2026-03-24 | 创建约束文档 |
| 2026-03-24 | 修复数据库连接问题（manim.db vs manim_platform.db） |
| 2026-03-24 | 修复 CI/CD health-check HTTPS 问题 |
| 2026-03-24 | 添加"生成代码和视频"按钮 |
| 2026-03-24 | 合并本地开发修改到 feature-global-constraints 分支 |
| 2026-03-24 | 添加统计数据模型和页面 |
| 2026-03-24 | 添加"最小修改原则"约束规则 |
| 2026-04-01 | 添加分支合并规范约束 |
| 2026-04-02 | 更新分支结构，添加部署前合并到 main 分支的规则 |
| 2026-04-07 | 添加开发环境约束（106.52.166.109） |
| 2026-04-07 | 强制要求：所有优化先在开发环境测试，用户确认后才能部署生产环境 |
| 2026-04-07 | 添加双环境架构说明（生产 vs 开发） |
| 2026-04-07 | 添加数据库独立性约束 |

---

## 十一、快速命令参考

### 开发环境命令

```bash
# SSH 连接开发环境
ssh root@106.52.166.109

# 重启开发环境后端
ssh root@106.52.166.109 "kill $(cat /opt/manim-dev/logs/backend.pid) && \
  cd /opt/manim-dev/backend && \
  nohup venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > /opt/manim-dev/logs/backend.log 2>&1 & \
  echo \$! > /opt/manim-dev/logs/backend.pid"

# 查看开发环境日志
ssh root@106.52.166.109 "tail -50 /opt/manim-dev/logs/backend.log"

# 测试开发环境 API
curl http://106.52.166.109:8001/health
curl http://106.52.166.109:3000/api/health

# 部署前端到开发环境
cd frontend && npm run build
scp -r dist/* root@106.52.166.109:/opt/manim-dev/frontend/dist/
ssh root@106.52.166.109 "systemctl reload nginx"
```

### 生产环境命令（⚠️ 仅用户确认后执行）

```bash
# SSH 连接生产环境
ssh root@152.136.218.74

# 重启生产环境后端（⚠️ 仅用户确认）
ssh root@152.136.218.74 "systemctl restart manim-backend"

# 查看生产环境日志
ssh root@152.136.218.74 "journalctl -u manim-backend --no-pager -n 50"

# 测试生产环境 API
curl http://152.136.218.74:8000/health
curl https://manim.asia/health

# 部署前端到生产环境（⚠️ 仅用户确认）
cd frontend && npm run build
scp -r dist/* root@152.136.218.74:/opt/manim/frontend/dist/
ssh root@152.136.218.74 "systemctl reload nginx"
```

### Git 操作

```bash
# 切换到开发分支
git checkout develop

# 提交开发分支
git add . && git commit -m "feat: xxx"
git push origin develop

# 合并到 main（用户确认后）
git checkout main
git merge develop
git push origin main
```

---

*最后更新：2026-04-07*

---

## 十二、服务器架构变更记录

### 2026-04-02：双服务器架构调整

**变更前：**
- 新服务器 (152.136.218.74)：独立运行
- 旧服务器 (106.52.166.109)：独立运行
- 问题：两台服务器分离，数据不同步

**变更后：**
- **新服务器 (152.136.218.74)**：生产环境，处理所有生产请求
- **旧服务器 (106.52.166.109)**：开发环境，开发测试使用

**配置详情：**

```
用户访问流程：
生产环境：http://152.136.218.74/* 或 https://manim.asia/*
开发环境：http://106.52.166.109:3000/*
```

**数据迁移：**
- 数据库：已迁移到新服务器（SQLite）
- 视频：使用 COS 存储，两台服务器共享
- 用户数据：已同步，无需额外操作

**注意事项：**
- 旧服务器到期时间：2026-05-02
- 旧服务器渲染服务（8000端口）继续为生产环境服务
- 开发环境已独立部署（8001端口后端，3000端口前端）

---

### 2026-04-07：开发环境部署

**部署目标：**
- 在旧服务器（106.52.166.109）部署独立的开发测试环境
- 完全不影响生产环境（152.136.218.74）

**部署结果：**
```
开发环境：
├── 后端：端口 8001（FastAPI）
├── 前端：端口 3000（Nginx 托管）
├── 数据库：manim_dev.db（生产数据库副本，已清理项目/文章数据）
└── 渲染服务：端口 8000（继续服务生产环境）

生产环境：
├── 后端：端口 8000（FastAPI）
├── 前端：HTTPS manim.asia（Nginx托管）
├── 数据库：manim.db（完整数据）
```

**数据库独立性：**
- 生产数据库：`/opt/manim/backend/manim.db`（2.2MB，26用户，99项目，7文章）
- 开发数据库：`/opt/manim-dev/backend/manim_dev.db`（26用户，17模板，已清理其他数据）
- ✅ 两个数据库物理隔离，完全独立

**核心约束：**
1. ❌ 禁止直接修改生产环境
2. ✅ 所有优化先在开发环境测试
3. ✅ 用户确认后才能部署到生产环境
