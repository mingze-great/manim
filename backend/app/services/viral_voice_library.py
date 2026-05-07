from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests
from pydub import AudioSegment

from app.config import get_settings

try:
    from app.utils.cos_storage import cos_storage
except Exception:
    cos_storage = None


def _resolve_voice_dir() -> Path:
    settings = get_settings()
    configured = str(getattr(settings, "STICKMAN_VIRAL_VOICE_DIR", "") or "").strip()
    candidates = [configured] if configured else []
    if Path(r"E:\ai\cankao\music\audio_mp3").exists():
        candidates.append(r"E:\ai\cankao\music\audio_mp3")
    candidates.append("/opt/manim-v2-viral-voices")
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    return Path(configured) if configured else Path("/opt/manim-v2-viral-voices")


def _resolve_registry_path(voice_dir: Path) -> Path:
    settings = get_settings()
    configured = str(getattr(settings, "STICKMAN_VIRAL_VOICE_REGISTRY_PATH", "") or "").strip()
    if configured:
        return Path(configured)
    return voice_dir / "cosyvoice_registry.json"


def _load_registry(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _save_registry(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _voice_label(index: int) -> str:
    return f"爆款音色{index}"


def _sample_signature(path: Path) -> str:
    stat = path.stat()
    return f"{path.name}:{int(stat.st_mtime)}:{stat.st_size}"


def _sample_prefix(path: Path) -> str:
    return "bk" + hashlib.md5(path.name.encode("utf-8")).hexdigest()[:6]


def _upload_public_sample(path: Path) -> str:
    if not cos_storage or not getattr(cos_storage, "enabled", False):
        raise RuntimeError("当前配音服务未准备完成，请稍后再试")
    audio = AudioSegment.from_file(path)
    with NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        temp_path = Path(temp_file.name)
    try:
        audio.export(temp_path, format="wav")
        content = temp_path.read_bytes()
        uploaded = cos_storage.upload_image(content, f"voices/preset/{path.stem}_{hashlib.md5(content).hexdigest()[:8]}.wav", content_type="audio/wav")
        if not uploaded:
            raise RuntimeError("当前配音服务未准备完成，请稍后再试")
        return cos_storage.get_public_url(uploaded)
    finally:
        temp_path.unlink(missing_ok=True)


def _create_voice_from_sample(path: Path, index: int) -> dict:
    settings = get_settings()
    api_key = str(getattr(settings, "DASHSCOPE_API_KEY", "") or "").strip()
    if not api_key:
        raise RuntimeError("当前配音服务未准备完成，请稍后再试")
    public_url = _upload_public_sample(path)
    response = requests.post(
        "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "voice-enrollment",
            "input": {
                "action": "create_voice",
                "target_model": "cosyvoice-v3.5-plus",
                "prefix": _sample_prefix(path),
                "url": public_url,
            },
        },
        timeout=120,
    )
    if response.status_code != 200:
        raise RuntimeError(f"创建爆款音色失败: {response.text[:300]}")
    result = response.json()
    output = result.get("output") or {}
    voice_id = output.get("voice_id")
    if not voice_id:
        raise RuntimeError("创建爆款音色失败")
    preview_audio = ((output.get("preview_audio") or {}).get("url")) or public_url
    return {
        "label": _voice_label(index),
        "value": voice_id,
        "provider": "dashscope_cosyvoice",
        "gender": "custom",
        "style": "viral",
        "preview_url": preview_audio,
        "source_file": path.name,
        "signature": _sample_signature(path),
    }


def get_builtin_viral_voices() -> list[dict]:
    voice_dir = _resolve_voice_dir()
    if not voice_dir.exists():
        return []
    registry_path = _resolve_registry_path(voice_dir)
    registry = _load_registry(registry_path)
    voices: list[dict] = []
    changed = False
    files = sorted([path for path in voice_dir.iterdir() if path.is_file() and path.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac", ".ogg"}], key=lambda item: item.name.lower())
    for index, path in enumerate(files, start=1):
        key = path.name
        signature = _sample_signature(path)
        cached = registry.get(key)
        if isinstance(cached, dict) and cached.get("value") and cached.get("signature") == signature:
            voice = dict(cached)
            voice["label"] = _voice_label(index)
            registry[key]["label"] = voice["label"]
            voices.append(voice)
            continue
        try:
            voice = _create_voice_from_sample(path, index)
        except Exception:
            continue
        registry[key] = voice
        voices.append(dict(voice))
        changed = True
    if changed:
        _save_registry(registry_path, registry)
    return voices
