# 开发环境迁移到生产环境 Runbook

## 目标

- 保持现有生产分支不受影响
- 将当前开发分支独立部署为新版本环境
- 继续使用生产环境已有业务数据
- 只执行兼容性数据库增量迁移
- 支持后台按用户切换 `legacy` / `v2` 前端版本

## 推荐部署结构

### 老生产环境

- 继续运行当前生产分支
- 继续服务默认全部用户

### 新版本环境

- 独立目录部署当前分支
- 使用独立端口或独立站点
- 连接同一套生产数据库
- 只给 `frontend_version = v2` 的用户使用

## 当前生产落地方式

本次生产实际落地为：

- 旧站：`/opt/manim`
- 新站：`/opt/manim-v2`
- 旧站入口：`/`
- 新站入口：`/v2/`

说明：

- 旧站继续使用生产现有数据库
- 新站共享旧站生产数据库
- 新站后端使用 `8002`
- 新站 Celery 使用独立队列 `manim_v2`
- 新版前端通过 nginx 的 `/v2/` 路由暴露，不影响旧站根路径

## 版本控制方案

用户表新增字段：

- `frontend_version VARCHAR(20) DEFAULT 'legacy'`

允许值：

- `legacy`
- `v2`

## 分流时机规则

只在**登录成功后**做版本分流，不在 `App` 初始化或页面未登录状态下做跨站跳转。

原因：

- 避免旧 token / 本地会话导致用户还未进入登录页就被提前送走
- 保证管理员始终能稳定进入新版站点后台
- 降低双站切换时的缓存和恢复登录干扰

### 新站规则

- 未登录：停留新站登录页
- 管理员：登录成功后永远留在新站
- 普通 `v2`：登录成功后留在新站
- 普通 `legacy`：登录成功后跳老站

### 老站规则

- 未登录：停留老站登录页
- 管理员：登录成功后直接跳新站后台
- 普通 `legacy`：登录成功后留在老站
- 普通 `v2`：登录成功后跳新站

规则：

- 老生产站点服务 `legacy` 用户
- 新版本站点服务 `v2` 用户
- 当前新版本前端支持通过 `VITE_LEGACY_APP_URL` 将 `legacy` 用户自动导向老站

## 迁移前检查

1. 确认当前要发布的 git 分支和 commit
2. 确认生产数据库备份路径
3. 确认 Redis / Celery / nginx / uvicorn 状态
4. 确认生产老站仍正常访问
5. 确认新站点目录、端口、域名或 nginx location

## 数据库迁移清单

只做增量，不覆盖生产已有业务数据。

### users

- 新增 `frontend_version`

### templates

- 新增 `reference_code`

### tasks

- 确保存在 `task_type`
- 确保存在 `log`
- 确保存在 `started_at`
- 确保存在 `completed_at`

### chat_styles

- 新建表 `chat_styles`

## 推荐 SQL / SQLite 迁移示例

```sql
ALTER TABLE users ADD COLUMN frontend_version VARCHAR(20) DEFAULT 'legacy';
ALTER TABLE templates ADD COLUMN reference_code TEXT;
ALTER TABLE tasks ADD COLUMN log TEXT;
ALTER TABLE tasks ADD COLUMN started_at DATETIME;
ALTER TABLE tasks ADD COLUMN completed_at DATETIME;

CREATE TABLE IF NOT EXISTS chat_styles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(50) NOT NULL UNIQUE,
  code VARCHAR(30) NOT NULL UNIQUE,
  description TEXT,
  system_prompt_zh TEXT NOT NULL,
  system_prompt_en TEXT,
  is_default BOOLEAN DEFAULT 0,
  is_active BOOLEAN DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 默认数据初始化

### frontend_version

将所有已有用户初始化为：

```sql
UPDATE users SET frontend_version = 'legacy' WHERE frontend_version IS NULL OR frontend_version = '';
```

### chat_styles

初始化默认风格：

- conservative
- sharp
- radical

如已有同 code 记录，按 code 更新，不重复插入。

## 发布步骤

### 1. 备份

必须备份：

- 生产数据库
- `.env`
- nginx 配置
- 当前静态资源目录

### 2. 部署新版本目录

推荐目录示例：

- `/opt/manim` 老生产
- `/opt/manim-v2` 新版本

### 3. 拉取或导入代码

可选方式：

- `git fetch && git checkout <branch>`
- `git bundle` 导入

### 4. 安装依赖

后端：

```bash
cd /opt/manim-v2/backend
source venv/bin/activate
pip install -r requirements.txt
```

前端：

```bash
cd /opt/manim-v2/frontend
npm install
npm run build
```

### 5. 启动服务

后端：

```bash
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 >> /tmp/backend_v2.log 2>&1 &
```

Celery：

```bash
nohup python -m celery -A celery_app worker --loglevel=info >> /tmp/celery_v2.log 2>&1 &
```

### 6. nginx / 入口配置

推荐：

- 老站继续指向老前端
- 新站指向 v2 前端

可选：

- 子域名，如 `v2.example.com`
- 独立路径，如 `/v2/`

### 7. 环境变量

新版本前端建议配置：

- `VITE_API_BASE_URL`
- `VITE_LEGACY_APP_URL`

老版本前端后续如需支持反向跳转，可补：

- `VITE_V2_APP_URL`

## 验收清单

### 登录与分版本

1. 管理员登录新站正常
2. 管理员登录老站会被导向新站后台
3. `legacy` 用户登录新站会被导向老站
4. `v2` 用户登录老站会被导向新站
5. `v2` 用户登录新站保持在新站
6. `legacy` 用户登录老站保持在老站
7. 后台用户管理可切换 `frontend_version`

### 对话后台任务

1. 发送消息成功创建后台任务
2. 关闭浏览器后任务继续执行
3. 重新进入项目可恢复状态
4. AI 回复最终落库

### 脚本生成后台任务

1. 提交 `generate-code-async`
2. 关闭浏览器后继续执行
3. 回到任务页恢复进度
4. 最终写入项目内容

### 渲染后台任务

1. 提交 `render-async`
2. 关闭浏览器后继续执行
3. 回到任务页恢复进度
4. 最终写入 `video_url`

### 管理后台

1. `chat_styles` 页面正常
2. `AdminTemplates` 可编辑 `reference_code`
3. 用户管理可切前端版本

## 回滚方案

### 代码回滚

新环境有问题时：

1. 不动老生产环境
2. 将测试用户改回 `legacy`
3. 停止 v2 环境服务

### 数据回滚

原则上优先不回滚数据库结构。

原因：

- 新增字段/表通常不影响老代码读取
- 真正的回滚重点是流量切回老站

只有在结构迁移失败且影响老站时，才恢复数据库备份。

## 每次从开发迁移到生产的标准动作

1. 在开发环境验证：对话 / 脚本 / 渲染三条链路
2. 记录本次发布的 branch 与 commit
3. 更新本 Runbook 中的数据库变更项
4. 先部署到新版本生产环境，不覆盖老生产
5. 仅给管理员和测试用户切 `v2`
6. 验证通过后逐步放量

## 记录模板

每次发布建议记录：

- 发布时间
- 分支名
- commit
- 是否包含 DB 迁移
- 是否包含前端版本分流变更
- 验证人
- 回滚点
