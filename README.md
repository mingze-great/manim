# Manim 视频生成平台

一个面向真实用户部署发布的 Web 平台，核心流程为：用户先输入视频主题，并与大模型多轮对话持续优化脚本思路与画面内容；确认满意后，系统基于主题自动生成 Manim 动画代码，后台完成代码执行、渲染与视频生成，并将结果返回前端，支持任务进度查看、视频预览、成品下载与历史记录管理。

## 功能特性

- 用户注册/登录认证
- 多轮对话优化视频脚本
- 支持模板选择（系统预设 + 用户自定义）
- 自动生成 Manim 动画代码
- Celery 异步任务队列
- 视频渲染进度实时推送
- 阿里云 OSS 视频存储
- 响应式 Web 界面

## 技术栈

### 后端
- FastAPI
- SQLAlchemy + SQLite
- Celery + Redis
- OpenAI API
- 阿里云 OSS

### 前端
- React 18 + TypeScript
- Vite
- Ant Design
- Zustand
- Tailwind CSS

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- Redis
- Manim
- 阿里云 OSS 账号

### 安装部署

1. 克隆项目
```bash
git clone <repository-url>
cd manim-video-platform
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 填入你的配置
```

3. 启动后端
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

4. 启动 Celery Worker
```bash
cd backend
celery -A celery_app worker --loglevel=info
```

5. 启动前端
```bash
cd frontend
npm install
npm run dev
```

### Docker 部署

```bash
docker-compose up -d
```

## 使用流程

1. 注册/登录账号
2. 创建新项目，输入视频主题
3. 与 AI 对话优化脚本
4. 确认脚本后选择模板
5. 生成视频，查看进度
6. 预览并下载成品

## API 文档

启动后访问: http://localhost:8000/docs
