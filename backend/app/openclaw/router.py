"""OpenClaw 路由入口 —— 只暴露 /openclaw/health 和 /openclaw/feishu/webhook

飞书开发者后台配置：
  事件订阅回调 URL: https://<你的域名>/api/openclaw/feishu/webhook
  订阅事件:         im.message.receive_v1
  权限:             im:message、im:message.group_at_msg、im:message:send_as_bot
"""
import asyncio
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.openclaw.config import get_openclaw_settings
from app.openclaw.feishu import FeishuClient, extract_user_text
from app.openclaw.service import answer, split_for_feishu

router = APIRouter(prefix="/openclaw", tags=["openclaw"])


# ---- 简易内存去重：event_id -> 处理时间戳 ----
# 飞书事件订阅在 3s 内没拿到 2xx 会重试（3s、15s、60s 三次），要按 event_id 幂等
_SEEN_EVENTS: dict[str, float] = {}
_SEEN_MAX = 2048
_SEEN_TTL = 600  # 10 分钟


def _seen_or_mark(event_id: str) -> bool:
    if not event_id:
        return False
    now = time.time()
    if len(_SEEN_EVENTS) > _SEEN_MAX:
        cutoff = now - _SEEN_TTL
        for k, ts in list(_SEEN_EVENTS.items()):
            if ts < cutoff:
                _SEEN_EVENTS.pop(k, None)
    if event_id in _SEEN_EVENTS:
        return True
    _SEEN_EVENTS[event_id] = now
    return False


def is_enabled() -> bool:
    cfg = get_openclaw_settings()
    return cfg.enabled


@router.get("/health")
async def health() -> dict[str, Any]:
    cfg = get_openclaw_settings()
    return {
        "enabled": cfg.enabled,
        "feishu_configured": bool(cfg.feishu_app_id and cfg.feishu_app_secret),
        "encrypt_enabled": bool(cfg.feishu_encrypt_key),
        "verify_token_set": bool(cfg.feishu_verify_token),
        "seen_cache_size": len(_SEEN_EVENTS),
    }


@router.post("/feishu/webhook")
async def feishu_webhook(request: Request) -> dict[str, Any]:
    cfg = get_openclaw_settings()
    if not cfg.feishu_app_id or not cfg.feishu_app_secret:
        raise HTTPException(500, "OpenClaw 未配置 FEISHU_APP_ID / FEISHU_APP_SECRET")

    client = FeishuClient(cfg)
    raw = await request.body()
    print(f"[openclaw.feishu] webhook raw body ({len(raw)}B): {raw[:400]!r}")
    try:
        import json as _json
        body = _json.loads(raw or b"{}")
    except Exception:
        raise HTTPException(400, "invalid json body")
    body = client.decrypt_body(body)
    print(f"[openclaw.feishu] webhook decoded keys: {list(body.keys())}")

    # 1) URL 验证握手（兼容 v1: 顶层 type/challenge；v2: header.event_type + event.challenge）
    header_early = body.get("header") or {}
    is_v1_handshake = body.get("type") == "url_verification"
    is_v2_handshake = header_early.get("event_type") == "url_verification"
    if is_v1_handshake or is_v2_handshake:
        if not client.verify_token(body):
            raise HTTPException(401, "invalid verify token")
        challenge = body.get("challenge") or (body.get("event") or {}).get("challenge") or ""
        return {"challenge": challenge}

    # 2) 事件回调 v2 —— 校验 token
    if not client.verify_token(body):
        raise HTTPException(401, "invalid verify token")

    header = body.get("header") or {}
    event_type = header.get("event_type")
    event_id = header.get("event_id", "")
    print(f"[openclaw.feishu] event_type={event_type} event_id={event_id}")

    if event_type != "im.message.receive_v1":
        print(f"[openclaw.feishu] ignored (unsupported event_type={event_type})")
        return {"code": 0, "msg": "ignored"}

    # 幂等：飞书 3 次重试同一 event_id，只处理一次
    if _seen_or_mark(event_id):
        print(f"[openclaw.feishu] duplicate event_id={event_id}")
        return {"code": 0, "msg": "duplicate"}

    event_obj = body.get("event") or {}
    msg_meta = event_obj.get("message") or {}
    sender_id = ((event_obj.get("sender") or {}).get("sender_id") or {}).get("open_id")
    print(
        f"[openclaw.feishu] msg meta: chat_type={msg_meta.get('chat_type')} "
        f"msg_type={msg_meta.get('message_type')} mentions={len(msg_meta.get('mentions') or [])} "
        f"chat_id={msg_meta.get('chat_id')} sender={sender_id} "
        f"content_preview={(msg_meta.get('content') or '')[:200]!r}"
    )
    extracted = extract_user_text(event_obj)
    if extracted is None:
        print("[openclaw.feishu] not text / not addressed to bot -> skip")
        return {"code": 0, "msg": "not text"}
    message_id, user_text = extracted
    chat_id = msg_meta.get("chat_id")
    print(f"[openclaw.feishu] will answer: message_id={message_id} chat={chat_id} text={user_text!r}")

    # 后台处理（不阻塞飞书 3s 超时）
    asyncio.create_task(_handle_and_reply(client, message_id, user_text, cfg, chat_id, sender_id))
    return {"code": 0, "msg": "ok"}


async def _handle_and_reply(
    client: FeishuClient, message_id: str, user_text: str, cfg, chat_id: str | None = None,
    sender_open_id: str | None = None,
) -> None:
    try:
        replies = await answer(user_text, cfg, chat_id=chat_id, fs_client=client, user_open_id=sender_open_id)
        # answer() 返回 list[str]，合并为单条飞书消息（超长再切片）。
        combined = "\n".join(replies) if replies else "(空回复)"
        for i, chunk in enumerate(split_for_feishu(combined)):
            if i > 0:
                chunk = f"（续 {i + 1}）\n{chunk}"
            await client.reply_text(message_id, chunk)
    except Exception as e:  # noqa: BLE001
        print(f"[openclaw.router] 回复失败: {type(e).__name__}: {e}")
        try:
            await client.reply_text(message_id, f"处理失败：{type(e).__name__}")
        except Exception:
            pass
