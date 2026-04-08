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

## 二、服务器架构（双环境）

### 生产环境（152.136.218.74）
| 项目 | 值 |
|------|-----|
| 服务器 IP | `152.136.218.74` |
| SSH 密码 | `010421` |
| 部署路径 | `/opt/manim` |
| 后端端口 | `8000` |
| 数据库 | `/opt/manim/backend/manim.db` (SQLite) |
| HTTPS 域名 | `https://manim.asia` |
| 状态 | ✅ 生产运行，**绝对不能影响** |

### 开发环境（106.52.166.109）
| 项目 | 值 |
|------|-----|
| 服务器 IP | `106.52.166.109` |
| SSH 认证 | SSH 密钥登录 |
| 部署路径 | `/opt/manim-dev` |
| 后端端口 | `8001` |
| 前端端口 | `3000` |
| 数据库 | `/opt/manim-dev/backend/manim_dev.db` (SQLite) |
| 渲染服务 | 端口 8000（服务于生产环境） |
| 状态 | ✅ 开发测试环境 |

### 数据库独立性
```
生产环境数据库：/opt/manim/backend/manim.db (完整数据)
开发环境数据库：/opt/manim-dev/backend/manim_dev.db (部分数据副本)

✅ 两个数据库完全独立，物理隔离
✅ 开发环境操作不会影响生产环境
✅ 生产环境操作不会影响开发环境
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
