
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/knowledge-ip", tags=["knowledge-ip"])
settings = get_settings()

ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]
RENDER_ROOT = ROOT / "video-render-service" / "remotion-mind-video"
STORAGE_ROOT = BACKEND_ROOT / "storage" / "knowledge_ip"
PUBLIC_INPUT_ROOT = RENDER_ROOT / "public" / "workflow-inputs"
PUBLIC_ASSET_ROOT = RENDER_ROOT / "public" / "workflow-assets"
RENDER_OUTPUT_ROOT = RENDER_ROOT / "renders"

STAGE_PROGRESS = {
    "uploaded": 0,
    "extract_audio": 12,
    "asr": 30,
    "analyze": 48,
    "materials": 68,
    "render": 88,
    "save": 96,
    "completed": 100,
    "failed": 100,
}
STAGE_MESSAGE = {
    "uploaded": "视频已上传，等待开始生成。",
    "extract_audio": "正在提取音频并整理源视频。",
    "asr": "正在识别字幕和时间轴。",
    "analyze": "正在分析内容结构并生成章节。",
    "materials": "正在生成动态包装素材。",
    "render": "正在渲染成片。",
    "save": "正在保存成片。",
    "completed": "包装视频已生成。",
    "failed": "生成失败。",
}

_jobs_lock = threading.Lock()
_running_jobs: set[str] = set()


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _job_dir(job_id: str) -> Path:
    return STORAGE_ROOT / job_id


def _job_json(job_id: str) -> Path:
    return _job_dir(job_id) / "job.json"


def _safe_name(name: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", Path(name or "upload.mp4").name).strip("._")
    return stem or "upload.mp4"


def _public_base_url() -> str:
    value = os.getenv("KNOWLEDGE_IP_PUBLIC_BASE_URL") or os.getenv("PUBLIC_BASE_URL") or "http://152.136.218.74:3003"
    return value.rstrip("/")


def _write_job(job: dict[str, Any]) -> None:
    _job_dir(job["id"]).mkdir(parents=True, exist_ok=True)
    job["updated_at"] = _now()
    _job_json(job["id"]).write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_job(job_id: str) -> dict[str, Any]:
    path = _job_json(job_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="任务不存在")
    return json.loads(path.read_text(encoding="utf-8"))


def _set_stage(job_id: str, stage: str, *, message: str | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    job = _read_job(job_id)
    job["stage"] = stage
    job["progress"] = STAGE_PROGRESS.get(stage, job.get("progress", 0))
    job["message"] = message or STAGE_MESSAGE.get(stage, stage)
    if stage == "failed":
        job["status"] = "failed"
    else:
        job.pop("error", None)
        if stage == "completed":
            job["status"] = "completed"
            job["completed_at"] = _now()
        elif stage == "uploaded":
            job["status"] = "uploaded"
        else:
            job["status"] = "running"
            job.setdefault("started_at", _now())
    if extra:
        job.update(extra)
    _write_job(job)
    return job


def _run(cmd: list[str], cwd: Path | None = None, timeout: int | None = None) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout[-3000:] or f"命令失败: {' '.join(cmd)}")
    return proc.stdout


def _probe_duration_ms(video_path: Path) -> int:
    out = _run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
    ], timeout=60).strip()
    seconds = float(out or 0)
    return max(1000, int(seconds * 1000))


def _normalize_source(job_id: str, input_path: Path) -> Path:
    PUBLIC_INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    out = PUBLIC_INPUT_ROOT / f"{job_id}.mp4"
    _run([
        "ffmpeg", "-y", "-i", str(input_path),
        "-vf", "scale=1080:-2,fps=30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)
    ], timeout=1800)
    return out


def _extract_audio(job_id: str, source_path: Path) -> Path:
    audio_path = _job_dir(job_id) / "audio.wav"
    _run([
        "ffmpeg", "-y", "-i", str(source_path), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio_path)
    ], timeout=900)
    return audio_path


def _dashscope_asr(job_id: str) -> dict[str, Any]:
    api_key = settings.DASHSCOPE_API_KEY or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY，无法调用 Paraformer 识别字幕。")
    try:
        import dashscope
        from dashscope.audio.asr import Transcription
    except Exception as exc:
        raise RuntimeError(f"DashScope SDK 不可用：{exc}") from exc

    dashscope.api_key = api_key
    audio_url = f"{_public_base_url()}/api/knowledge-ip/public/{job_id}/audio.wav"
    response = Transcription.async_call(
        model="paraformer-v2",
        file_urls=[audio_url],
        api_key=api_key,
        language_hints=["zh"],
        disfluency_removal_enabled=True,
        diarization_enabled=False,
        timestamp_alignment_enabled=True,
    )
    wait_response = Transcription.wait(response, api_key=api_key)
    status_code = getattr(wait_response, "status_code", None)
    if status_code and int(status_code) >= 400:
        raise RuntimeError(f"Paraformer 提交失败：{getattr(wait_response, 'message', wait_response)}")
    output = getattr(wait_response, "output", None) or (wait_response.get("output") if isinstance(wait_response, dict) else None) or {}
    if "SUCCESS_WITH_NO_VALID_FRAGMENT" in json.dumps(output, ensure_ascii=False):
        raise RuntimeError("字幕识别失败：没有检测到清晰人声，请上传有人声且声音更清楚的视频。")

    def find_transcription_url(value: Any) -> str | None:
        if isinstance(value, dict):
            for key in ("transcription_url", "url"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.startswith("http"):
                    return candidate
            for child in value.values():
                found = find_transcription_url(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = find_transcription_url(child)
                if found:
                    return found
        return None

    transcription_url = find_transcription_url(output)
    if not transcription_url:
        raise RuntimeError("字幕识别失败：Paraformer 没有返回可用转写结果，请稍后重试或更换视频。")
    result = requests.get(transcription_url, timeout=120)
    result.raise_for_status()
    return result.json()


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip()


def _captions_from_transcript(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    sentences = []
    if isinstance(transcript.get("transcripts"), list) and transcript["transcripts"]:
        sentences = transcript["transcripts"][0].get("sentences") or []
    if not sentences:
        sentences = transcript.get("sentences") or []
    captions: list[dict[str, Any]] = []
    for item in sentences:
        text = _normalize_text(item.get("text") or item.get("sentence") or item.get("content"))
        begin = item.get("begin_time", item.get("start_time", item.get("start")))
        end = item.get("end_time", item.get("end_time", item.get("end")))
        try:
            start_ms = int(float(begin))
            end_ms = int(float(end))
        except Exception:
            continue
        if text and end_ms > start_ms:
            captions.append({"startMs": start_ms, "endMs": end_ms, "zh": text, "text": text, "en": ""})
    if not captions:
        raise RuntimeError("未能根据字幕生成有效分段。未能根据字幕生成有效分段。知识分享")
    return captions


def _translate_captions(captions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    api_key = settings.DASHSCOPE_API_KEY or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        return captions
    # Keep this lightweight. If translation fails, Chinese captions still remain exact ASR output.
    try:
        payload = {
            "model": settings.DASHSCOPE_CHAT_MODEL or "qwen3.5-plus",
            "messages": [
                {"role": "system", "content": "Translate Chinese short-video subtitles into concise natural English. Return a JSON array of strings only."},
                {"role": "user", "content": json.dumps([c["zh"] for c in captions[:120]], ensure_ascii=False)},
            ],
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        url = (settings.DASHSCOPE_BASE_URL or "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/") + "/chat/completions"
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        match = re.search(r"\[[\s\S]*\]", content)
        translations = json.loads(match.group(0) if match else content)
        for item, en in zip(captions, translations):
            item["en"] = str(en).strip()
    except Exception:
        pass
    return captions


def _segments_from_captions(captions: list[dict[str, Any]], duration_ms: int) -> list[dict[str, Any]]:
    kinds = ["arrow", "shell", "phone", "cards", "tree", "compare", "paths", "door"]
    segments: list[dict[str, Any]] = []
    group: list[dict[str, Any]] = []
    group_start = captions[0]["startMs"] if captions else 0
    for cap in captions:
        if not group:
            group_start = cap["startMs"]
        group.append(cap)
        current_len = cap["endMs"] - group_start
        if current_len >= 6500 or len(group) >= 3:
            zh = "".join(c["zh"] for c in group)
            idx = len(segments)
            segments.append({
                "id": f"seg_{idx+1:02d}",
                "startMs": group_start,
                "endMs": group[-1]["endMs"],
                "tab": _normalize_text(zh)[:6] or f"?{idx+1}?",
                "title": _normalize_text(zh)[:14] or f"?{idx+1}?",
                "zh": _normalize_text(zh),
                "en": group[0].get("en", ""),
                "kind": kinds[idx % len(kinds)],
                "mainTitle": "知识分享",
            })
            group = []
    if group:
        zh = "".join(c["zh"] for c in group)
        idx = len(segments)
        segments.append({
            "id": f"seg_{idx+1:02d}",
            "startMs": group_start,
            "endMs": max(group[-1]["endMs"], duration_ms),
            "tab": _normalize_text(zh)[:6] or f"?{idx+1}?",
            "title": _normalize_text(zh)[:14] or f"?{idx+1}?",
            "zh": _normalize_text(zh),
            "en": group[0].get("en", ""),
            "kind": kinds[idx % len(kinds)],
            "mainTitle": "知识分享",
        })
    if segments:
        segments[0]["startMs"] = 0
        segments[-1]["endMs"] = max(segments[-1]["endMs"], duration_ms)
    return segments


def _top_tabs(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not segments:
        return []
    groups = min(4, len(segments))
    size = max(1, (len(segments) + groups - 1) // groups)
    tabs = []
    for idx in range(groups):
        group = segments[idx * size:(idx + 1) * size]
        if not group:
            continue
        tabs.append({"label": group[0]["title"][:8], "startMs": group[0]["startMs"], "endMs": group[-1]["endMs"]})
    while len(tabs) < 4 and tabs:
        tabs.append(tabs[-1] | {"label": f"?{len(tabs)+1}?"})
    return tabs[:4]


def _write_props(job_id: str, duration_ms: int, captions: list[dict[str, Any]], segments: list[dict[str, Any]]) -> Path:
    out_dir = PUBLIC_ASSET_ROOT / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    props = {
        "sourceVideo": f"workflow-inputs/{job_id}.mp4",
        "materialTrackSrc": None,
        "durationMs": duration_ms,
        "speakerCrop": {"scale": 1.18, "y": -2},
        "segments": segments,
        "topTabs": _top_tabs(segments),
        "captions": captions,
    }
    props_path = out_dir / "remotion_props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
    return props_path


def _render(job_id: str) -> Path:
    output = _run([
        "node", "scripts/render-knowledge-ip-package.js", "render", f"--job={job_id}"
    ], cwd=RENDER_ROOT, timeout=7200)
    matches = re.findall(r"output\s+(.+\.mp4)", output)
    if not matches:
        raise RuntimeError(f"Remotion 成片还没有生成?{output[-2000:]}")
    path = Path(matches[-1].strip())
    if not path.exists() or path.stat().st_size < 1024:
        raise RuntimeError("Remotion 正在生成动态包装素材。")
    (_job_dir(job_id) / "render.log").write_text(output, encoding="utf-8")
    return path


def _run_job(job_id: str) -> None:
    with _jobs_lock:
        if job_id in _running_jobs:
            return
        _running_jobs.add(job_id)
    try:
        job = _read_job(job_id)
        input_path = Path(job["input_path"])
        _set_stage(job_id, "extract_audio")
        source_path = _normalize_source(job_id, input_path)
        duration_ms = _probe_duration_ms(source_path)
        _extract_audio(job_id, source_path)

        _set_stage(job_id, "asr")
        transcript = _dashscope_asr(job_id)
        (_job_dir(job_id) / "transcript.json").write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
        captions = _translate_captions(_captions_from_transcript(transcript))

        _set_stage(job_id, "analyze")
        segments = _segments_from_captions(captions, duration_ms)
        if not segments:
            raise RuntimeError("未能根据字幕生成有效分段。")

        _set_stage(job_id, "materials", message="正在生成动态包装素材。当前版本使用实时动态图形包装，后续接入 AI 小视频素材。")
        _write_props(job_id, duration_ms, captions, segments)

        _set_stage(job_id, "render")
        output_path = _render(job_id)

        _set_stage(job_id, "save")
        result_url = f"/api/knowledge-ip/jobs/{job_id}/video"
        _set_stage(job_id, "completed", extra={"result_url": result_url, "output_path": str(output_path), "duration_ms": duration_ms, "caption_count": len(captions), "segment_count": len(segments)})
    except Exception as exc:
        try:
            _set_stage(job_id, "failed", message=str(exc), extra={"error": str(exc)})
        except Exception:
            pass
    finally:
        with _jobs_lock:
            _running_jobs.discard(job_id)


@router.post("/uploads")
async def upload_video(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if not (file.content_type or "").startswith("video/"):
        raise HTTPException(status_code=400, detail="成片还没有生成")
    job_id = f"kip_{uuid.uuid4().hex[:12]}"
    job_dir = _job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    filename = _safe_name(file.filename or "upload.mp4")
    input_path = job_dir / filename
    with input_path.open("wb") as target:
        shutil.copyfileobj(file.file, target)
    size = input_path.stat().st_size
    job = {
        "id": job_id,
        "user_id": current_user.id,
        "status": "uploaded",
        "stage": "uploaded",
        "progress": 0,
        "message": STAGE_MESSAGE["uploaded"],
        "filename": filename,
        "size": size,
        "input_path": str(input_path),
        "created_at": _now(),
        "updated_at": _now(),
    }
    _write_job(job)
    return _public_job(job)


@router.post("/jobs/{job_id}/start")
def start_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
):
    job = _read_job(job_id)
    if not current_user.is_admin and job.get("user_id") != current_user.id:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.get("status") == "running":
        return _public_job(job)
    if job.get("status") == "completed":
        return _public_job(job)
    _set_stage(job_id, "extract_audio")
    background_tasks.add_task(_run_job, job_id)
    return _public_job(_read_job(job_id))


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    job = _read_job(job_id)
    if not current_user.is_admin and job.get("user_id") != current_user.id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _public_job(job)


@router.get("/jobs/{job_id}/video")
def get_video(job_id: str):
    job = _read_job(job_id)
    output = job.get("output_path")
    if not output or not Path(output).exists():
        raise HTTPException(status_code=404, detail="成片还没有生成")
    return FileResponse(output, media_type="video/mp4", filename=f"knowledge-ip-{job_id}.mp4")


@router.get("/public/{job_id}/audio.wav")
def public_audio(job_id: str):
    audio = _job_dir(job_id) / "audio.wav"
    if not audio.exists():
        raise HTTPException(status_code=404, detail="成片还没有生成?")
    return FileResponse(audio, media_type="audio/wav")


def _public_job(job: dict[str, Any]) -> dict[str, Any]:
    keys = ["id", "status", "stage", "progress", "message", "filename", "size", "created_at", "updated_at", "completed_at", "result_url", "duration_ms", "caption_count", "segment_count", "error"]
    return {key: job.get(key) for key in keys if key in job}
