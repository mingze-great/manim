"""WebSocket JWT 鉴权。

复用 app/api/auth.py 的 SECRET_KEY + ALGORITHM。前端在 /api/voice/session 换取 一次性
token（本轮直接就是原 JWT，未来可换成短时一次性签发）。WS 连接必须带 ?token=...
"""
from __future__ import annotations

from typing import Optional

from fastapi import WebSocket, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.api.auth import ALGORITHM, SECRET_KEY, token_blacklist
from app.database import SessionLocal
from app.models.user import User


async def authenticate_ws(ws: WebSocket) -> Optional[User]:
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    if token in token_blacklist:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
    except JWTError:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    if not username:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        return user
    finally:
        db.close()
