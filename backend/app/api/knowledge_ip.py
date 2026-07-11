
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

VIDEO_SYNTHESIS_URL = os.getenv("DASHSCOPE_VIDEO_BASE_URL", "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis").strip()
VIDEO_TASK_URL = os.getenv("DASHSCOPE_VIDEO_TASK_URL", "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}").strip()
VIDEO_MATERIAL_MODEL = os.getenv("KNOWLEDGE_IP_VIDEO_MODEL", "happyhorse-1.0-t2v").strip()
VIDEO_MATERIAL_FALLBACK_MODELS = [m.strip() for m in os.getenv("KNOWLEDGE_IP_VIDEO_FALLBACK_MODELS", "wan2.7-t2v,happyhorse-1.1-t2v,wan2.6-t2v").split(",") if m.strip()]
ENABLE_VIDEO_MATERIALS = os.getenv("KNOWLEDGE_IP_ENABLE_VIDEO_MATERIALS", "1").lower() not in {"0", "false", "no"}

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


def _format_seconds(seconds: float | int | None) -> str:
    try:
        value = max(0, float(seconds or 0))
    except Exception:
        value = 0
    if value < 60:
        return f"{value:.1f}秒"
    minutes = int(value // 60)
    rest = int(value % 60)
    return f"{minutes}分{rest}秒"


def _refresh_timing(job: dict[str, Any], next_stage: str) -> None:
    now_ts = time.time()
    now_iso = _now()
    job.setdefault("started_at", now_iso)
    job.setdefault("started_at_ts", now_ts)
    timing = job.setdefault("timing", {"stages": {}})
    stages = timing.setdefault("stages", {})
    previous_stage = job.get("stage")
    previous_started = job.get("stage_started_at_ts")
    if previous_stage and previous_stage != next_stage:
        entry = stages.setdefault(previous_stage, {"started_at": job.get("stage_started_at") or job.get("updated_at") or now_iso})
        if "ended_at" not in entry:
            started_ts = previous_started or job.get("started_at_ts") or now_ts
            entry["ended_at"] = now_iso
            entry["duration_seconds"] = round(max(0, now_ts - float(started_ts)), 1)
            entry["duration_text"] = _format_seconds(entry["duration_seconds"])
    if previous_stage != next_stage:
        stages.setdefault(next_stage, {"started_at": now_iso})
        job["stage_started_at"] = now_iso
        job["stage_started_at_ts"] = now_ts
    timing["elapsed_seconds"] = round(max(0, now_ts - float(job.get("started_at_ts") or now_ts)), 1)
    timing["elapsed_text"] = _format_seconds(timing["elapsed_seconds"])


def _set_stage(job_id: str, stage: str, *, message: str | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    job = _read_job(job_id)
    _refresh_timing(job, stage)
    job["stage"] = stage
    job["progress"] = STAGE_PROGRESS.get(stage, job.get("progress", 0))
    job["message"] = message or STAGE_MESSAGE.get(stage, stage)
    if stage == "failed":
        job["status"] = "failed"
        job["failed_at"] = _now()
    else:
        job.pop("error", None)
        if stage == "completed":
            job["status"] = "completed"
            job["completed_at"] = _now()
            _refresh_timing(job, "completed")
        elif stage == "uploaded":
            job["status"] = "uploaded"
        else:
            job["status"] = "running"
            job.setdefault("started_at", _now())
    if extra:
        job.update(extra)
    _write_job(job)
    return job


def _update_render_progress(job_id: str, render_percent: float) -> None:
    try:
        job = _read_job(job_id)
        if job.get("stage") != "render" or job.get("status") != "running":
            return
        _refresh_timing(job, "render")
        render_percent = max(0.0, min(100.0, float(render_percent)))
        job["render_progress"] = round(render_percent, 1)
        job["progress"] = min(96, 88 + int(render_percent * 0.08))
        elapsed = job.get("timing", {}).get("elapsed_text", "")
        job["message"] = f"正在渲染成片：{render_percent:.1f}%" + (f"，已用时 {elapsed}" if elapsed else "")
        _write_job(job)
    except Exception:
        pass


def _run(cmd: list[str], cwd: Path | None = None, timeout: int | None = None) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout[-3000:] or f"命令失败: {' '.join(cmd)}")
    return proc.stdout


def _run_stream(cmd: list[str], cwd: Path | None = None, timeout: int | None = None, on_line=None) -> str:
    started = time.time()
    proc = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)
    lines: list[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line)
            if on_line:
                on_line(line.rstrip("\n"))
            if timeout and time.time() - started > timeout:
                proc.kill()
                raise TimeoutError(f"命令超时：{' '.join(cmd)}")
        code = proc.wait()
    finally:
        if proc.poll() is None:
            proc.kill()
    output = "".join(lines)
    if code != 0:
        raise RuntimeError(output[-3000:] or f"命令失败: {' '.join(cmd)}")
    return output


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


def _strip_for_label(value: Any, max_chars: int = 5) -> str:
    text = re.sub(r"[AIaiＡＩ]+", "", str(value or ""))
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).strip()
    return (text[:max_chars] or "重点")


def _format_caption_text(words: list[dict[str, Any]]) -> str:
    parts = []
    for word in words:
        token = str(word.get("text") or "")
        punct = str(word.get("punctuation") or "")
        if token:
            parts.append(token + punct)
    return _normalize_text("".join(parts))


def _split_sentence_item(item: dict[str, Any], *, max_chars: int = 22, max_ms: int = 2800) -> list[dict[str, Any]]:
    words = item.get("words") or []
    if not isinstance(words, list) or not words:
        text = _normalize_text(item.get("text") or item.get("sentence") or item.get("content"))
        begin = item.get("begin_time", item.get("start_time", item.get("start")))
        end = item.get("end_time", item.get("end"))
        try:
            start_ms = int(float(begin)); end_ms = int(float(end))
        except Exception:
            return []
        if not text or end_ms <= start_ms:
            return []
        # Fallback: if the ASR provider has no word timing, split only on punctuation and distribute time proportionally.
        pieces = [p for p in re.split(r"(?<=[，。！？；,.!?;])", text) if p]
        if len(pieces) <= 1:
            return [{"startMs": start_ms, "endMs": end_ms, "zh": text, "text": text, "en": ""}]
        total = sum(len(p) for p in pieces) or len(text)
        cursor = start_ms
        out = []
        for index, piece in enumerate(pieces):
            dur = int((end_ms - start_ms) * len(piece) / total)
            next_end = end_ms if index == len(pieces) - 1 else max(cursor + 600, cursor + dur)
            clean = _normalize_text(piece)
            if clean:
                out.append({"startMs": cursor, "endMs": next_end, "zh": clean, "text": clean, "en": ""})
            cursor = next_end
        return out

    chunks: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    hard_punct = set("。！？!?；;")
    soft_punct = set("，,.、")

    def flush() -> None:
        nonlocal current
        if not current:
            return
        text = _format_caption_text(current)
        try:
            start_ms = int(float(current[0].get("begin_time", current[0].get("start_time", 0))))
            end_ms = int(float(current[-1].get("end_time", current[-1].get("end", start_ms))))
        except Exception:
            current = []
            return
        if text and end_ms > start_ms:
            chunks.append({"startMs": start_ms, "endMs": end_ms, "zh": text, "text": text, "en": ""})
        current = []

    for word in words:
        if not str(word.get("text") or "").strip():
            continue
        current.append(word)
        text = _format_caption_text(current)
        punct = str(word.get("punctuation") or "")
        try:
            duration = int(float(word.get("end_time", 0))) - int(float(current[0].get("begin_time", 0)))
        except Exception:
            duration = 0
        should_flush = False
        if punct and any(ch in hard_punct for ch in punct) and len(text) >= 6:
            should_flush = True
        elif punct and any(ch in soft_punct for ch in punct) and (len(text) >= 10 or duration >= 1400):
            should_flush = True
        elif len(text) >= max_chars or duration >= max_ms:
            should_flush = True
        if should_flush:
            flush()
    flush()
    return chunks


def _captions_from_transcript(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    sentences = []
    if isinstance(transcript.get("transcripts"), list) and transcript["transcripts"]:
        sentences = transcript["transcripts"][0].get("sentences") or []
    if not sentences:
        sentences = transcript.get("sentences") or []
    captions: list[dict[str, Any]] = []
    for item in sentences:
        captions.extend(_split_sentence_item(item))
    captions = [cap for cap in captions if cap.get("zh") and cap.get("endMs", 0) > cap.get("startMs", 0)]
    captions.sort(key=lambda item: item["startMs"])
    if not captions:
        raise RuntimeError("未能根据字幕生成有效分段。请上传有人声且声音清楚的视频。")
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

    def emit() -> None:
        nonlocal group, group_start
        if not group:
            return
        zh = _normalize_text("".join(c["zh"] for c in group))
        idx = len(segments)
        title = _strip_for_label(zh, 10)
        segments.append({
            "id": f"seg_{idx+1:02d}",
            "startMs": group_start,
            "endMs": group[-1]["endMs"],
            "tab": _strip_for_label(zh, 5),
            "title": title,
            "zh": zh,
            "en": group[0].get("en", ""),
            "kind": kinds[idx % len(kinds)],
            "mainTitle": "知识分享",
        })
        group = []

    for cap in captions:
        if not group:
            group_start = cap["startMs"]
        proposed_text = _normalize_text("".join(c["zh"] for c in group + [cap]))
        proposed_ms = cap["endMs"] - group_start
        if group and (proposed_ms > 4600 or len(group) >= 2 or len(proposed_text) > 34):
            emit()
            group_start = cap["startMs"]
        group.append(cap)
    emit()
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
        joined = "".join(item.get("zh") or item.get("title") or "" for item in group)
        tabs.append({"label": _strip_for_label(joined, 5), "startMs": group[0]["startMs"], "endMs": group[-1]["endMs"]})
    while len(tabs) < 4 and tabs:
        tabs.append(tabs[-1] | {"label": f"第{len(tabs)+1}节"})
    return tabs[:4]


def _find_url(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("video_url", "url", "file_url", "download_url"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.startswith("http"):
                return candidate
        for child in value.values():
            found = _find_url(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_url(child)
            if found:
                return found
    return None


def _video_task_endpoint(task_id: str) -> str:
    if "{task_id}" in VIDEO_TASK_URL:
        return VIDEO_TASK_URL.format(task_id=task_id)
    if "/api/v1/" in VIDEO_SYNTHESIS_URL:
        return VIDEO_SYNTHESIS_URL.split("/api/v1/", 1)[0].rstrip("/") + f"/api/v1/tasks/{task_id}"
    return VIDEO_TASK_URL.rstrip("/") + f"/{task_id}"


def _build_material_groups(segments: list[dict[str, Any]], max_ms: int = 12000, max_items: int = 3) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for segment in segments:
        if not current:
            current = [segment]
            continue
        span = int(segment.get("endMs", 0)) - int(current[0].get("startMs", 0))
        if len(current) >= max_items or span > max_ms:
            groups.append(current)
            current = [segment]
        else:
            current.append(segment)
    if current:
        groups.append(current)
    return groups


MATERIAL_STYLE_PROMPT = os.getenv(
    "KNOWLEDGE_IP_MATERIAL_STYLE_PROMPT",
    "???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????"
).strip()


def _material_prompt(group: list[dict[str, Any]]) -> str:
    text = "?".join(_normalize_text(item.get("zh") or item.get("title")) for item in group)
    text = text[:180]
    return (
        f"{MATERIAL_STYLE_PROMPT}?"
        "??16:9?????????????????????????????logo??????????????"
        f"???????{text}?"
        "???????????????????????????????????"
    )


def _submit_video_material(prompt: str, model: str, duration: int = 5) -> str:
    api_key = settings.DASHSCOPE_API_KEY or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("未配置素材生成 API Key。")
    payload = {
        "model": model,
        "input": {"prompt": prompt},
        "parameters": {
            "resolution": os.getenv("KNOWLEDGE_IP_VIDEO_RESOLUTION", "1080P"),
            "ratio": "16:9",
            "prompt_extend": True,
            "watermark": False,
            "duration": duration,
        },
    }
    resp = requests.post(
        VIDEO_SYNTHESIS_URL,
        headers={"X-DashScope-Async": "enable", "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if resp.status_code >= 400:
        body = resp.text[:1000]
        if "AllocationQuota.FreeTierOnly" in body or "free quota" in body.lower() or "????" in body:
            raise RuntimeError("?????????????????????????????????????????")
        raise RuntimeError(f"???????? {resp.status_code}?{body}")
    data = resp.json()
    task_id = (data.get("output") or {}).get("task_id") or data.get("task_id")
    if not task_id:
        raise RuntimeError(f"素材视频任务提交失败：{json.dumps(data, ensure_ascii=False)[:500]}")
    return task_id


def _wait_video_material(task_id: str, timeout_seconds: int = 1800) -> str:
    api_key = settings.DASHSCOPE_API_KEY or os.getenv("DASHSCOPE_API_KEY")
    deadline = time.time() + timeout_seconds
    endpoint = _video_task_endpoint(task_id)
    last_payload: Any = None
    while time.time() < deadline:
        resp = requests.get(endpoint, headers={"Authorization": f"Bearer {api_key}"}, timeout=60)
        if resp.status_code >= 400:
            body = resp.text[:1000]
            if "AllocationQuota.FreeTierOnly" in body or "free quota" in body.lower() or "????" in body:
                raise RuntimeError("?????????????????????????????????????????")
            raise RuntimeError(f"?????????? {resp.status_code}?{body}")
        data = resp.json()
        last_payload = data
        status = str((data.get("output") or {}).get("task_status") or data.get("task_status") or "").upper()
        if status in {"SUCCEEDED", "SUCCESS", "COMPLETED"}:
            url = _find_url(data)
            if not url:
                raise RuntimeError(f"素材视频生成成功但没有返回下载地址：{json.dumps(data, ensure_ascii=False)[:500]}")
            return url
        if status in {"FAILED", "CANCELED", "UNKNOWN"}:
            raise RuntimeError(f"素材视频生成失败：{json.dumps(data, ensure_ascii=False)[:500]}")
        time.sleep(8)
    raise TimeoutError(f"素材视频生成超时：{json.dumps(last_payload, ensure_ascii=False)[:500]}")


def _download_material(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        with output.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)
    if output.stat().st_size < 1024:
        raise RuntimeError("素材视频下载异常。")


def _generate_material_videos(job_id: str, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not ENABLE_VIDEO_MATERIALS:
        return segments
    groups = _build_material_groups(segments)
    models = [VIDEO_MATERIAL_MODEL, *VIDEO_MATERIAL_FALLBACK_MODELS]
    out_dir = PUBLIC_ASSET_ROOT / job_id / "materials"
    for index, group in enumerate(groups, start=1):
        _set_stage(job_id, "materials", message=f"正在生成素材视频：{index}/{len(groups)}")
        prompt = _material_prompt(group)
        last_error: Exception | None = None
        output = out_dir / f"material_{index:02d}.mp4"
        if output.exists() and output.stat().st_size > 1024:
            rel = f"workflow-assets/{job_id}/materials/{output.name}"
            for segment in group:
                segment["materialSrc"] = rel
            continue
        for model in models:
            try:
                task_id = _submit_video_material(prompt, model)
                video_url = _wait_video_material(task_id)
                _download_material(video_url, output)
                rel = f"workflow-assets/{job_id}/materials/{output.name}"
                for segment in group:
                    segment["materialSrc"] = rel
                    segment["materialPrompt"] = prompt
                last_error = None
                break
            except Exception as exc:
                last_error = exc
        if last_error:
            message = str(last_error)
            if "AllocationQuota.FreeTierOnly" in message or "free quota" in message.lower():
                raise RuntimeError("素材视频模型额度不可用：请在阿里控制台关闭“免费额度用完即停”或开通付费后再生成。")
            raise RuntimeError(f"素材视频生成失败：{last_error}")
    return segments


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
    log_path = _job_dir(job_id) / "render.log"

    def handle_line(line: str) -> None:
        with log_path.open("a", encoding="utf-8") as log:
            log.write(line + "\n")
        match = re.search(r"progress\s+([0-9.]+)%", line)
        if match:
            _update_render_progress(job_id, float(match.group(1)))

    output = _run_stream([
        "node", "scripts/render-knowledge-ip-package.js", "render", f"--job={job_id}"
    ], cwd=RENDER_ROOT, timeout=7200, on_line=handle_line)
    matches = re.findall(r"output\s+(.+\.mp4)", output)
    if not matches:
        raise RuntimeError(f"Remotion 成片还没有生成：{output[-2000:]}")
    path = Path(matches[-1].strip())
    if not path.exists() or path.stat().st_size < 1024:
        raise RuntimeError("Remotion 成片文件异常，请重新生成。")
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

        _set_stage(job_id, "materials", message="正在生成动态素材视频。")
        segments = _generate_material_videos(job_id, segments)
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
