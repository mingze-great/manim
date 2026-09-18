# Manim Platform · 视频生成 + 飞书协作 + 语音助手

一个面向真实用户的多模态创作平台，围绕三条主线组织：

1. **Manim 视频生成** —— 用户输入主题，与大模型多轮对话优化脚本，系统自动生成 Manim 动画代码并渲染为视频，支持模板、进度推送、OSS 存储与历史管理。
2. **虾仁花旦飞书 Bot（`openclaw`）** —— 独立飞书机器人 + 员工队伍，覆盖 AI 热点日推、日程助手、平台健康监控、HR 招人向导等场景。
3. **「小曼」语音助手（`/voice`）** —— 深色 HUD 页面，vendored Ashley MIT 头盔（PMREM + 装配粒子 + 眼部发光 shader），全双工 WS pipeline，可挂载火山 ASR/TTS 与 Porcupine 唤醒词。

线上环境：
- 生产：<https://www.lazymedia.cn>
- Staging（本仓库当前迭代目标）：<https://152.136.218.74:3003>

## 模块地图

```
backend/app/
├── api/            REST 路由（视频、用户、模型、鉴权、admin）
├── services/       视频生成核心业务
├── tasks/          Celery 任务：脚本生成 → 代码生成 → 渲染 → OSS 上传
├── models/         SQLAlchemy 模型
├── openclaw/       飞书 bot、员工分派、AI 热点、日程、监控、HR、状态持久化
└── voice/          「小曼」WS pipeline：session / providers（mock + volc 骨架）/ 鉴权

frontend/src/pages/
├── Creator/  Dashboard/  ProjectChat/  ProjectTask/  History/  ...
└── Voice/    小曼页面（Ashley helmet + timeline + audio capture + ws client）
```

## 技术栈

**后端** FastAPI · SQLAlchemy · Celery + Redis · pydantic-settings · APScheduler · httpx · 阿里云 OSS · 大模型 SDK（OpenAI 兼容 / 火山）

**前端** React 18 · TypeScript · Vite · Ant Design · Zustand · Tailwind · Framer Motion · Three.js（自研 Ashley helmet vendored 渲染流水线）

## 快速开始

### 前置要求

- Python 3.11+ · Node.js 18+ · Redis · Manim · 阿里云 OSS 账号
- 可选：飞书自建应用、火山引擎语音、Picovoice Porcupine

### 本地起动

```bash
git clone <repo>
cd manim
cp .env.example .env    # 填 OSS、大模型、飞书、火山 等配置

# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Celery worker（另一个终端）
cd backend
celery -A celery_app worker --loglevel=info

# 前端
cd frontend
npm install
npm run dev
```

Docker 一键：

```bash
docker-compose up -d
```

## 使用流程

### 视频生成
1. 登录 → 新建项目 → 输入主题
2. 与 AI 多轮对话优化脚本
3. 选择模板 → 提交渲染
4. 任务面板查进度 → 预览 / 下载

### 飞书 bot（openclaw）
- 群内命令：`/hire`、`/fire`、`/team`、`/model`、`/monitor now`、`/schedule add|list|done|del`
- AI 热点 每日 09:00 自动推送到 `AI热点` 群
- 平台健康 每日 09:15 自动巡检，异常时红灯报警
- 详细协议见 `backend/app/openclaw/README.md`

### 小曼语音助手 `/voice`
- 页面就绪后按住 <kbd>Space</kbd> 说话 → 松开触发一次会话
- 状态机：`idle → listening → thinking → speaking`，Ashley helmet 联动脉动 / 摆头 / 眼部发光
- 工程期默认走 `providers_mock`（ASR 假回复 + 真 LLM + 静音 TTS），火山 access token 到位后切换 `VOICE_PROVIDER=volc`

## 生产部署

- 生产（Ubuntu 20.04 + systemd）：`www.lazymedia.cn`，服务名 `manim-v2-backend`，端口 8002
- Staging：`/opt/manim-v2-3003-snapshot`，服务名 `manim-v2-3003-backend`，端口 3003
- 前端产物 `frontend/dist/` 由 nginx 直出，`/api` 反代至后端；`/api/voice/ws` 需要 nginx 打开 WS Upgrade

CI/CD：仅 `master` 触发发布流水线；`feature/*` 分支手动 rsync 到 staging 验证。

## API 文档

在线：<https://www.lazymedia.cn/docs>（生产）· <https://152.136.218.74:3003/docs>（staging）

## 分支约定

- 日常开发在 `feature/<topic>` 分支
- 未验证的变更禁止 merge `master`（会触发生产发布）
- 语音 / 飞书 bot 相关工作集中在 `feature/openclaw`
