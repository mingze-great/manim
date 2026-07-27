import json
import os
import shutil
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from pydub import AudioSegment


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class LocalTTSQueue:
    _lock = threading.Lock()

    def __init__(self, root: Path, token: str = ""):
        self.root = Path(root).resolve()
        self.token = str(token or os.getenv("LOCAL_TTS_WORKER_TOKEN") or "").strip()
        self.lease_seconds = int(os.getenv("LOCAL_TTS_LEASE_SECONDS", "180"))
        self.root.mkdir(parents=True, exist_ok=True)

    def enabled(self) -> bool:
        return bool(self.token)

    def require_token(self, token: str | None) -> None:
        if not self.enabled():
            raise HTTPException(status_code=503, detail="Local TTS queue is not configured")
        if str(token or "").strip() != self.token:
            raise HTTPException(status_code=401, detail="Invalid local TTS worker token")

    def request_dir(self, request_id: str) -> Path:
        safe_id = str(request_id or "").strip()
        if not safe_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in safe_id):
            raise ValueError("Invalid local TTS request id")
        return self.root / safe_id

    def request_path(self, request_id: str) -> Path:
        return self.request_dir(request_id) / "request.json"

    def create_request(
        self,
        *,
        text: str,
        voice: str,
        job_id: str,
        scene_index: int,
        cue_index: int | None = None,
        prompt_text: str = "",
    ) -> dict[str, Any]:
        if not self.enabled():
            raise RuntimeError("LOCAL_TTS_WORKER_TOKEN is not configured; local TTS worker is disabled")
        clean_text = str(text or "").strip()
        if not clean_text:
            raise RuntimeError("Local TTS request text is empty")
        request_id = f"tts_{job_id}_{scene_index + 1:02d}_{(cue_index or 0) + 1:02d}_{uuid.uuid4().hex[:10]}"
        request_dir = self.request_dir(request_id)
        request_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "requestId": request_id,
            "status": "pending",
            "jobId": job_id,
            "sceneIndex": scene_index,
            "cueIndex": cue_index,
            "text": clean_text,
            "voice": str(voice or "dayun_manbo"),
            "promptText": str(prompt_text or os.getenv("SC1_COSYVOICE_PROMPT_TEXT") or "焦虑不是敌人，它只是先替你把危险放大。"),
            "createdAt": utc_now_iso(),
            "updatedAt": utc_now_iso(),
            "attempts": 0,
        }
        with self._lock:
            self._write_payload(request_id, payload)
        return payload

    def claim_next(self) -> dict[str, Any] | None:
        with self._lock:
            now = datetime.utcnow()
            candidates: list[tuple[datetime, str]] = []
            for request_file in self.root.glob("*/request.json"):
                payload = self._read_payload_path(request_file)
                if not payload:
                    continue
                status = str(payload.get("status") or "")
                if status == "completed":
                    continue
                if status == "leased":
                    lease_until = self._parse_iso(str(payload.get("leaseUntil") or ""))
                    if lease_until and lease_until > now:
                        continue
                if status not in {"pending", "leased"}:
                    continue
                created_at = self._parse_iso(str(payload.get("createdAt") or "")) or now
                candidates.append((created_at, str(payload.get("requestId") or request_file.parent.name)))
            if not candidates:
                return None
            candidates.sort(key=lambda item: item[0])
            _, request_id = candidates[0]
            payload = self._read_payload(request_id)
            if not payload:
                return None
            status = str(payload.get("status") or "")
            if status == "completed":
                return None
            if status == "leased":
                lease_until = self._parse_iso(str(payload.get("leaseUntil") or ""))
                if lease_until and lease_until > now:
                    return None
            payload["status"] = "leased"
            payload["attempts"] = int(payload.get("attempts") or 0) + 1
            payload["leaseUntil"] = (now + timedelta(seconds=self.lease_seconds)).replace(microsecond=0).isoformat() + "Z"
            payload["updatedAt"] = utc_now_iso()
            self._write_payload(request_id, payload)
            return payload

    async def complete_request(self, request_id: str, file: UploadFile) -> dict[str, Any]:
        with self._lock:
            request_dir = self.request_dir(request_id)
            payload = self._read_payload(request_id)
            if not payload:
                raise HTTPException(status_code=404, detail="Local TTS request not found")
            if str(payload.get("status") or "") == "completed":
                completed_path = request_dir / "completed.wav"
                return {
                    "requestId": request_id,
                    "status": "completed",
                    "audioBytes": completed_path.stat().st_size if completed_path.exists() else 0,
                }
            suffix = Path(file.filename or "").suffix.lower() or ".wav"
            if suffix not in {".wav", ".mp3", ".m4a", ".aac", ".ogg"}:
                raise HTTPException(status_code=400, detail="Only wav/mp3/m4a/aac/ogg audio is supported")
            raw_path = request_dir / f"uploaded{suffix}"
            with raw_path.open("wb") as output:
                shutil.copyfileobj(file.file, output)
            if raw_path.stat().st_size <= 0:
                raise HTTPException(status_code=400, detail="Uploaded audio is empty")
            completed_path = request_dir / "completed.wav"
            try:
                audio = AudioSegment.from_file(raw_path)
                audio = audio.set_channels(1).set_frame_rate(22050)
                audio.export(completed_path, format="wav")
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Audio conversion failed: {exc}") from exc
            payload["status"] = "completed"
            payload["audioPath"] = str(completed_path)
            payload["audioBytes"] = completed_path.stat().st_size
            payload["updatedAt"] = utc_now_iso()
            self._write_payload(request_id, payload)
            return {"requestId": request_id, "status": "completed", "audioBytes": payload["audioBytes"]}

    def fail_request(self, request_id: str, error: str) -> dict[str, Any]:
        with self._lock:
            payload = self._read_payload(request_id)
            if not payload:
                raise HTTPException(status_code=404, detail="Local TTS request not found")
            if str(payload.get("status") or "") == "completed":
                return {"requestId": request_id, "status": "completed"}
            payload["status"] = "failed"
            payload["error"] = str(error or "Local TTS failed")[:1000]
            payload["updatedAt"] = utc_now_iso()
            self._write_payload(request_id, payload)
            return {"requestId": request_id, "status": "failed"}

    def wait_for_audio(self, request_id: str, timeout_seconds: int) -> Path:
        import time

        deadline = time.time() + max(5, int(timeout_seconds))
        request_dir = self.request_dir(request_id)
        while time.time() < deadline:
            payload = self._read_payload(request_id)
            if payload and payload.get("status") == "failed":
                raise RuntimeError(f"Local TTS worker failed: {payload.get('error') or 'unknown error'}")
            completed_path = request_dir / "completed.wav"
            if completed_path.exists() and completed_path.stat().st_size > 0:
                return completed_path
            time.sleep(1.0)
        raise RuntimeError("Local TTS worker timed out; please make sure the local CosyVoice worker is running")

    def _read_payload(self, request_id: str) -> dict[str, Any] | None:
        return self._read_payload_path(self.request_path(request_id))

    def _read_payload_path(self, path: Path) -> dict[str, Any] | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _write_payload(self, request_id: str, payload: dict[str, Any]) -> None:
        request_dir = self.request_dir(request_id)
        request_dir.mkdir(parents=True, exist_ok=True)
        target = request_dir / "request.json"
        tmp = request_dir / f"request.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(target)

    def _parse_iso(self, value: str) -> datetime | None:
        try:
            return datetime.fromisoformat(value.replace("Z", ""))
        except Exception:
            return None
