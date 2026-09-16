"""语音助手路由。

  GET  /api/voice/health         provider / 唤醒词等元信息
  POST /api/voice/session        换一次性 ws token（工程期直接返回当前 JWT）
  WS   /api/voice/ws?token=...   全双工语音会话
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.auth import get_current_user, oauth2_scheme
from app.voice.config import get_voice_settings, is_enabled  # noqa: F401
from app.voice.session import VoiceSession
from app.voice.ws_auth import authenticate_ws

router = APIRouter(prefix="/voice", tags=["voice"])


def _build_providers(settings):
    if settings.provider == "volc":
        from app.voice.providers_volc import build_providers
    else:
        from app.voice.providers_mock import build_providers
    return build_providers(settings)


@router.get("/health")
async def health() -> dict[str, Any]:
    s = get_voice_settings()
    return {
        "enabled": s.enabled,
        "provider": s.provider,
        "wake_word": s.wake_word,
        "volc_configured": bool(s.volc_app_id and s.volc_access_token),
    }


@router.post("/session")
async def create_session(
    token: Annotated[str, Depends(oauth2_scheme)],
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """工程期偷懒：直接把浏览器手上的 JWT 当 ws-token 回给它。
    未来若要签发一次性 short-lived token，只改这里。
    """
    s = get_voice_settings()
    return {
        "ws_token": token,
        "wake_word": s.wake_word,
        "provider": s.provider,
    }


@router.websocket("/ws")
async def voice_ws(ws: WebSocket) -> None:
    await ws.accept()
    user = await authenticate_ws(ws)
    if user is None:
        return

    settings = get_voice_settings()
    try:
        providers = _build_providers(settings)
    except Exception as e:  # noqa: BLE001
        await ws.send_json({"type": "error", "detail": f"provider 初始化失败: {type(e).__name__}: {e}"})
        await ws.close()
        return

    session = VoiceSession(ws, settings, providers)
    try:
        await session.run()
    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        try:
            await ws.send_json({"type": "error", "detail": f"session crashed: {type(e).__name__}: {e}"})
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass
