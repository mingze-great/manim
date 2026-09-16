# OpenClaw 模块

独立子模块，把飞书机器人接到项目的 LLM 能力上。**不启用时对主平台零影响**。

## 目录结构

```
openclaw/
├── __init__.py      # 对外暴露 router / is_enabled
├── config.py        # 独立配置（OPENCLAW_* 环境变量）
├── feishu.py        # 飞书 OpenAPI 客户端 + 事件解析
├── service.py       # 业务逻辑：user_text → LLM → 回复
├── router.py        # FastAPI 路由：/api/openclaw/*
└── README.md
```

## 3 分钟接入指南

### 第 1 步：飞书开发者后台申请自建应用

1. 进 https://open.feishu.cn/app → 创建企业自建应用
2. 「凭证与基础信息」 → 记下 **App ID** 和 **App Secret**
3. 「事件与回调 → 事件配置」→ 请求网址填：
   ```
   https://<你的域名>/api/openclaw/feishu/webhook
   ```
4. 复制页面上的 **Verification Token**
5. 「事件配置」→ 添加事件 `im.message.receive_v1`（接收消息）
6. 「权限管理」→ 至少开通：
   - `im:message`（读取用户发给机器人的消息）
   - `im:message.group_at_msg`（读取群聊 @ 消息）
   - `im:message:send_as_bot`（以机器人身份发消息）
7. 「版本管理与发布」→ 创建版本 → 提交审核（企业内自建应用通常管理员一键通过）

### 第 2 步：在 `backend/.env` 里加 4 行

```env
OPENCLAW_ENABLED=true
OPENCLAW_FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
OPENCLAW_FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENCLAW_FEISHU_VERIFY_TOKEN=xxxxxxxxxxxxxxxx
```

**可选参数**（都有默认值，不配就用默认）：

```env
OPENCLAW_FEISHU_ENCRYPT_KEY=              # 若在飞书后台开启了 Encrypt Key 才填，需要 pip install pycryptodome
OPENCLAW_SYSTEM_PROMPT=你是 OpenClaw 助手，用简洁准确的中文回答用户问题。
OPENCLAW_LLM_MAX_TOKENS=800
OPENCLAW_LLM_TEMPERATURE=0.7
```

### 第 3 步：重启后端

```bash
# docker-compose 部署
docker-compose restart backend

# 系统 service 部署
systemctl restart manim
```

启动日志里能看到：
```
[openclaw] 模块已启用，路由挂载在 /api/openclaw/*
```

### 第 4 步：验证

```bash
curl https://<你的域名>/api/openclaw/health
# 期望：{"enabled":true,"feishu_configured":true,"encrypt_enabled":false,"verify_token_set":true}
```

然后回飞书后台点「事件配置」的**保存/验证**按钮，飞书会向你的 webhook 发一次 URL 验证请求，看到「验证通过」就 OK。

### 第 5 步：使用

在飞书任意群里 @机器人 说话，或直接单聊机器人：
- 「@OpenClaw 什么是傅里叶变换」→ 机器人调 LLM 回复

## 关闭 / 卸载

- 关闭：`.env` 里 `OPENCLAW_ENABLED=false`，重启即可
- 彻底卸载：删除 `backend/app/openclaw/` 目录，并删除 `main.py` 里那段 `try: from app.openclaw ...` 加载代码

## 依赖

- 常规：`httpx`（已在主 requirements.txt）
- 可选：`pycryptodome`（**只有开启加密订阅时**需要 `pip install pycryptodome`）

## 依赖的主平台能力

只依赖 `app.utils.llm_factory.LLMFactory`，跟主平台的 chat/manim/project 业务完全无耦合。删除本模块不影响主平台。
