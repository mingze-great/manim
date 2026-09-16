"""OpenClaw 独立模块 —— 飞书机器人接入

主平台默认不启用本模块。启用方式：在 .env 里设置：
    OPENCLAW_ENABLED=true
    OPENCLAW_FEISHU_APP_ID=...
    OPENCLAW_FEISHU_APP_SECRET=...
    OPENCLAW_FEISHU_VERIFY_TOKEN=...

启用后，路由挂在 /api/openclaw/feishu/webhook，把这个 URL 填进
飞书开发者后台 → 事件订阅回调 URL 即可。

模块可以随时删除，不影响主平台任何功能。
"""
from app.openclaw.router import router, is_enabled

__all__ = ["router", "is_enabled"]
