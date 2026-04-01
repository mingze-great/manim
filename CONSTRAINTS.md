# 项目全局约束文档

> 本文档定义了项目开发过程中必须遵循的全局约束。所有操作必须在此约束基础上执行。

---

## 一、分支管理

| 分支名 | 用途 | 说明 |
|--------|------|------|
| `feature-chat-render-button` | 稳定版本分支 | **禁止修改**，远程纯净分支 |
| `feature-local-test` | 远程备份分支 | 用于远程备份 |
| `feature-dev-local` | 本地开发分支 | 日常开发使用 |
| `feature-global-constraints` | 约束文档分支 | 当前分支，存放约束文档 |

**规则：**
1. 所有新功能开发在 `feature-dev-local` 分支进行
2. 功能完成后合并到 `feature-chat-render-button` 进行测试
3. 测试通过后合并到 `master` 触发 CI/CD 部署
4. **永远不要直接修改 `feature-chat-render-button` 分支**

---

## 二、部署架构

| 项目 | 值 |
|------|-----|
| 服务器 IP | `106.52.166.109` |
| SSH 用户 | `root` |
| SSH 私钥 | `~/.ssh/id_rsa` |
| 部署路径 | `/opt/manim` |
| 后端服务 | `systemctl restart manim` |
| 数据库 | `sqlite:///./manim.db` |
| HTTPS 域名 | `https://manim.asia` |

**部署方式：**
1. GitHub Actions CI/CD（push 到 master 触发）
2. 手动部署：SSH 连接服务器，拉取代码，重启服务

---

## 三、账号信息

### 管理员账号
| 项目 | 值 |
|------|-----|
| 用户名 | `admin` |
| 密码 | `admin123` |
| 邮箱 | `admin@manim.com` |

### 数据库用户
| 用户名 | 邮箱 | 权限 |
|--------|------|------|
| admin | admin@manim.com | 管理员 |
| myoung | mylcsd@163.com | 普通用户 |
| G先生 | 252345415@qq.com | 普通用户 |
| yuliiiii | 623918645@qq.com | 普通用户 |

---

## 四、平台命名规范

| 原名称 | 新名称 | 说明 |
|--------|--------|------|
| AI视频 | 思维可视化 | 全局替换，除 AI 对话功能外 |

---

## 五、已完成功能清单

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

## 六、待完成功能

| # | 功能 | 优先级 | 状态 |
|---|------|--------|------|
| 1 | 完整流程测试 | 高 | 待测试 |
| 2 | 代码模板功能完整测试 | 中 | 待测试 |
| 3 | 服务器数据库迁移（添加 statistics 表） | 中 | 待执行 |

---

## 七、关键代码位置

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

## 八、约束规则

### 8.1 开发约束
1. **本地测试优先**：所有修改先在本地测试，确认无误后再部署
2. **不修改远程纯净分支**：`feature-chat-render-button` 禁止直接修改
3. **保持数据完整**：不删除服务器数据库中的用户数据
4. **代码风格**：不添加注释（除非明确要求）
5. **最小修改原则**：修改或优化某个功能时，只能改动该功能相关的代码，**绝对不能修改其他已有的功能代码**。如果发现需要修改其他功能，必须先询问用户确认

### 8.2 部署约束
1. **手动部署流程**：
   ```bash
   # 构建前端
   cd frontend && npm run build
   
   # 上传前端
   scp -i ~/.ssh/id_rsa -r frontend/dist/* root@106.52.166.109:/opt/manim/frontend/dist/
   
   # 重启后端
   ssh -i ~/.ssh/id_rsa root@106.52.166.109 "systemctl restart manim"
   ```

2. **CI/CD 部署**：合并到 master 后自动触发

### 8.3 数据库约束
1. 实际使用数据库：`/opt/manim/backend/manim.db`
2. 修改表结构前先备份
3. 添加新列使用 `ALTER TABLE`，不删除已有数据

### 8.4 分支合并规范

1. **最小修改原则**
   - 修改时不要动之前已有的分支
   - 不要修改需求之外的内容
   - 修改某个功能时，只能改动该功能相关的代码

2. **分支及时合并**
   - 分支修改完成后必须及时合并
   - 保证所有更新内容不会在下一次更新时丢失
   - 更新内容必须基于之前所有可用的最新版本

3. **合并流程**
   - 新功能开发完成后，先合并到主开发分支
   - 确保合并后的代码包含所有之前的更新
   - 合并前检查是否有冲突，及时解决

---

## 九、更新日志

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

---

## 十、快速命令参考

```bash
# 切换分支
git checkout feature-chat-render-button

# 查看状态
git status && git log --oneline -3

# SSH 连接服务器
ssh -i ~/.ssh/id_rsa root@106.52.166.109

# 重启后端服务
ssh -i ~/.ssh/id_rsa root@106.52.166.109 "systemctl restart manim"

# 查看后端日志
ssh -i ~/.ssh/id_rsa root@106.52.166.109 "journalctl -u manim --no-pager -n 50"

# 构建并部署前端
cd frontend && npm run build && scp -i ~/.ssh/id_rsa -r dist/* root@106.52.166.109:/opt/manim/frontend/dist/

# 测试 API
curl -sk https://manim.asia/health
```

---

*最后更新：2026-03-24*