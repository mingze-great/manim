"""飞书通道适配器

负责：
1. 处理飞书事件订阅的 URL 验证握手 / verify token 校验 / 消息解密
2. 通过 tenant_access_token 回复消息（token 模块级缓存，避免每次 webhook 都换取）
"""
import asyncio
import base64
import hashlib
import json
import time
from typing import Any, Optional

import httpx

from app.openclaw.config import OpenClawSettings

FEISHU_OPEN_API = "https://open.feishu.cn/open-apis"


# ---- 模块级 tenant_access_token 缓存 ----
_TOKEN_CACHE: dict[str, tuple[str, float]] = {}  # app_id -> (token, expire_at)
_TOKEN_LOCK = asyncio.Lock()


class FeishuClient:
    def __init__(self, cfg: OpenClawSettings):
        self.cfg = cfg

    # ---- 消息加密解密 ----
    def decrypt_body(self, body: dict) -> dict:
        """若开启了加密订阅（encrypt_key 有值），飞书发过来会是 {"encrypt": "..."}."""
        if not self.cfg.feishu_encrypt_key or "encrypt" not in body:
            return body
        try:
            from Crypto.Cipher import AES  # pycryptodome
        except ImportError as e:
            raise RuntimeError(
                "已配置 OPENCLAW_FEISHU_ENCRYPT_KEY 但未安装 pycryptodome。\n"
                "请执行: pip install pycryptodome"
            ) from e
        cipher_bytes = base64.b64decode(body["encrypt"])
        key = hashlib.sha256(self.cfg.feishu_encrypt_key.encode()).digest()
        iv, ct = cipher_bytes[:16], cipher_bytes[16:]
        aes = AES.new(key, AES.MODE_CBC, iv)
        plain = aes.decrypt(ct)
        plain = plain[: -plain[-1]]  # PKCS7 unpad
        return json.loads(plain.decode("utf-8"))

    def verify_token(self, body: dict) -> bool:
        if not self.cfg.feishu_verify_token:
            return True
        token = body.get("token") or body.get("header", {}).get("token")
        return token == self.cfg.feishu_verify_token

    # ---- OpenAPI ----
    async def get_tenant_access_token(self) -> str:
        app_id = self.cfg.feishu_app_id
        now = time.time()
        cached = _TOKEN_CACHE.get(app_id)
        if cached and cached[1] > now + 60:
            return cached[0]

        async with _TOKEN_LOCK:
            cached = _TOKEN_CACHE.get(app_id)
            if cached and cached[1] > now + 60:
                return cached[0]

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{FEISHU_OPEN_API}/auth/v3/tenant_access_token/internal",
                    json={
                        "app_id": app_id,
                        "app_secret": self.cfg.feishu_app_secret,
                    },
                )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"tenant_access_token 获取失败: {data}")
            token = data["tenant_access_token"]
            expire_at = now + int(data.get("expire", 7200))
            _TOKEN_CACHE[app_id] = (token, expire_at)
            return token

    async def reply_text(self, message_id: str, text: str, retries: int = 2) -> None:
        """回复文本消息。飞书 code=99991663 表示 tenant_token 失效，会自动 refresh 重试一次。"""
        last_err: Optional[str] = None
        for attempt in range(retries + 1):
            token = await self.get_tenant_access_token()
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        f"{FEISHU_OPEN_API}/im/v1/messages/{message_id}/reply",
                        headers={"Authorization": f"Bearer {token}"},
                        json={
                            "msg_type": "text",
                            "content": json.dumps({"text": text}, ensure_ascii=False),
                        },
                    )
            except httpx.HTTPError as e:
                last_err = f"HTTP {type(e).__name__}: {e}"
                await asyncio.sleep(0.5 * (attempt + 1))
                continue

            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    return
                if data.get("code") in (99991663, 99991664, 99991665):  # token 相关错误
                    _TOKEN_CACHE.pop(self.cfg.feishu_app_id, None)
                    last_err = f"token expired: {data}"
                    continue
                last_err = f"reply failed: {data}"
                break  # 业务错误不重试
            last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
            await asyncio.sleep(0.5 * (attempt + 1))

        print(f"[openclaw.feishu] reply 失败: {last_err}")

    async def send_to_chat(self, chat_id: str, text: str, retries: int = 2) -> bool:
        """向指定 chat_id 主动发消息（不 reply 某条），用于 boss 向员工群派单。"""
        last_err: Optional[str] = None
        for attempt in range(retries + 1):
            token = await self.get_tenant_access_token()
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        f"{FEISHU_OPEN_API}/im/v1/messages?receive_id_type=chat_id",
                        headers={"Authorization": f"Bearer {token}"},
                        json={
                            "receive_id": chat_id,
                            "msg_type": "text",
                            "content": json.dumps({"text": text}, ensure_ascii=False),
                        },
                    )
            except httpx.HTTPError as e:
                last_err = f"HTTP {type(e).__name__}: {e}"
                await asyncio.sleep(0.5 * (attempt + 1))
                continue

            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    return True
                if data.get("code") in (99991663, 99991664, 99991665):
                    _TOKEN_CACHE.pop(self.cfg.feishu_app_id, None)
                    last_err = f"token expired: {data}"
                    continue
                last_err = f"send failed: {data}"
                break
            last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
            await asyncio.sleep(0.5 * (attempt + 1))

        print(f"[openclaw.feishu] send_to_chat({chat_id}) 失败: {last_err}")
        return False

    async def chat_info(self, chat_id: str) -> Optional[dict]:
        """查询 chat 信息 —— 用来验证 bot 是否有权访问该群。"""
        token = await self.get_tenant_access_token()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{FEISHU_OPEN_API}/im/v1/chats/{chat_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.HTTPError as e:
            print(f"[openclaw.feishu] chat_info 网络失败: {e}")
            return None
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("code") != 0:
            print(f"[openclaw.feishu] chat_info 业务错误: {data}")
            return None
        return data.get("data")


def extract_user_text(event: dict) -> Optional[tuple[str, str]]:
    """从 im.message.receive_v1 事件里提取 (message_id, 去掉 @ 的纯文本)。
    非文本消息返回 None。
    """
    message = event.get("message") or {}
    message_id = message.get("message_id")
    if not message_id or message.get("message_type") != "text":
        return None
    try:
        content = json.loads(message.get("content", "{}"))
    except json.JSONDecodeError:
        return None
    text: str = content.get("text", "")
    for mention in message.get("mentions") or []:
        key = mention.get("key", "")
        if key:
            text = text.replace(key, "")
    return message_id, text.strip()
