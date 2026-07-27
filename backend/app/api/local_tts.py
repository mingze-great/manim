import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from app.services.ai_video import AI_VIDEO_STORAGE_ROOT
from app.services.local_tts_queue import LocalTTSQueue


router = APIRouter(prefix="/local-tts", tags=["local-tts"])


def _queue() -> LocalTTSQueue:
    queue_root = Path(os.getenv("LOCAL_TTS_QUEUE_ROOT", AI_VIDEO_STORAGE_ROOT / "local-tts-queue"))
    return LocalTTSQueue(queue_root)


def _token_from_header(authorization: str | None, x_local_tts_token: str | None) -> str:
    raw = str(authorization or "").strip()
    if raw.lower().startswith("bearer "):
        return raw.split(" ", 1)[1].strip()
    return str(x_local_tts_token or "").strip()


@router.get("/status")
def local_tts_status():
    queue = _queue()
    return {"enabled": queue.enabled()}


@router.post("/claim")
def claim_local_tts_request(
    authorization: Annotated[str | None, Header()] = None,
    x_local_tts_token: Annotated[str | None, Header()] = None,
):
    queue = _queue()
    queue.require_token(_token_from_header(authorization, x_local_tts_token))
    request = queue.claim_next()
    if not request:
        return {"request": None}
    return {"request": request}


@router.post("/{request_id}/complete")
async def complete_local_tts_request(
    request_id: str,
    authorization: Annotated[str | None, Header()] = None,
    x_local_tts_token: Annotated[str | None, Header()] = None,
    file: UploadFile = File(...),
):
    queue = _queue()
    queue.require_token(_token_from_header(authorization, x_local_tts_token))
    return await queue.complete_request(request_id, file)


@router.post("/{request_id}/fail")
def fail_local_tts_request(
    request_id: str,
    error: Annotated[str, Form()] = "本地配音失败",
    authorization: Annotated[str | None, Header()] = None,
    x_local_tts_token: Annotated[str | None, Header()] = None,
):
    queue = _queue()
    queue.require_token(_token_from_header(authorization, x_local_tts_token))
    if not request_id:
        raise HTTPException(status_code=400, detail="缺少 request_id")
    return queue.fail_request(request_id, error)
