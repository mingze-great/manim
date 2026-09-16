"""Voice 模块配置。

跟 openclaw 一样，走独立 dotenv 解析，不侵入主 config。VOICE_ 前缀。
外部接入相关的钥匙（火山引擎、Porcupine）默认全空，工程期不需要。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass
class VoiceSettings:
    enabled: bool
    # provider 选择：mock | volc （工程期默认 mock）
    provider: str
    # 唤醒词（写死给前端展示；实际唤醒逻辑在浏览器）
    wake_word: str
    # LLM 复用 openclaw 的通道（hyhawang）；单独也允许覆盖
    llm_model: str
    llm_system_prompt: str
    # 火山引擎（Deferred；工程期不填也能跑）
    volc_app_id: str
    volc_access_token: str
    volc_asr_cluster: str
    volc_tts_cluster: str
    volc_voice_type: str


def _parse_dotenv(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                    v = v[1:-1]
                if k:
                    out[k] = v
    except FileNotFoundError:
        pass
    return out


def _load_env_files() -> dict[str, str]:
    backend_dir = Path(__file__).resolve().parents[2]
    root_dir = backend_dir.parent
    env_name = (os.getenv("ENVIRONMENT") or "development").strip().lower() or "development"
    merged: dict[str, str] = {}
    for p in [root_dir / ".env", root_dir / f".env.{env_name}", backend_dir / ".env"]:
        merged.update(_parse_dotenv(str(p)))
    return merged


def _get(env: dict[str, str], name: str, default: str = "") -> str:
    v = os.environ.get(name)
    if v is not None and v != "":
        return v
    return env.get(name, default)


def _to_bool(v: str, default: bool = False) -> bool:
    if not v:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@lru_cache()
def get_voice_settings() -> VoiceSettings:
    env = _load_env_files()
    return VoiceSettings(
        enabled=_to_bool(_get(env, "VOICE_ENABLED", "true"), True),
        provider=_get(env, "VOICE_PROVIDER", "mock").strip().lower() or "mock",
        wake_word=_get(env, "VOICE_WAKE_WORD", "小曼").strip() or "小曼",
        llm_model=_get(env, "VOICE_LLM_MODEL", "").strip(),
        llm_system_prompt=_get(
            env,
            "VOICE_LLM_SYSTEM_PROMPT",
            "你是「小曼」，一个亲切、机敏的中文语音助手。回答简短口语化，一般不超过三句话，"
            "适合朗读，避免列表和 markdown。用户在语音场景下不会看到你的文字，只会听到。",
        ),
        volc_app_id=_get(env, "VOLC_APP_ID", "").strip(),
        volc_access_token=_get(env, "VOLC_ACCESS_TOKEN", "").strip(),
        volc_asr_cluster=_get(env, "VOLC_ASR_CLUSTER", "").strip(),
        volc_tts_cluster=_get(env, "VOLC_TTS_CLUSTER", "").strip(),
        volc_voice_type=_get(env, "VOLC_VOICE_TYPE", "").strip(),
    )


def is_enabled() -> bool:
    return get_voice_settings().enabled
