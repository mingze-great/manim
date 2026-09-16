"""OpenClaw 模块的独立配置

不侵入主项目的 config.py。所有配置都以 OPENCLAW_ 开头。
读取顺序：os.environ 优先，其次是主项目 .env / .env.<ENVIRONMENT> / backend/.env。
"""
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass
class OpenClawSettings:
    enabled: bool
    feishu_app_id: str
    feishu_app_secret: str
    feishu_verify_token: str
    feishu_encrypt_key: str
    system_prompt: str
    llm_max_tokens: int
    llm_temperature: float
    # 独立 LLM 通道（不走主站 LLMFactory）
    llm_base_url: str
    llm_api_key: str
    llm_model: str


def _parse_dotenv(path: str) -> dict[str, str]:
    """极简 dotenv 解析：KEY=VALUE，忽略注释和空行。不做变量插值。"""
    out: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip()
                # 去掉包裹的引号
                if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                    v = v[1:-1]
                if k:
                    out[k] = v
    except FileNotFoundError:
        pass
    return out


def _load_env_files() -> dict[str, str]:
    backend_dir = Path(__file__).resolve().parents[2]  # backend/
    root_dir = backend_dir.parent
    env_name = (os.getenv("ENVIRONMENT") or "development").strip().lower() or "development"
    candidates = [
        root_dir / ".env",
        root_dir / f".env.{env_name}",
        backend_dir / ".env",
    ]
    merged: dict[str, str] = {}
    for p in candidates:
        merged.update(_parse_dotenv(str(p)))
    return merged


def _get(env_files: dict[str, str], name: str, default: str = "") -> str:
    v = os.environ.get(name)
    if v is not None and v != "":
        return v
    return env_files.get(name, default)


def _to_bool(val: str, default: bool = False) -> bool:
    if val is None:
        return default
    v = val.strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


@lru_cache()
def get_openclaw_settings() -> OpenClawSettings:
    env = _load_env_files()
    return OpenClawSettings(
        enabled=_to_bool(_get(env, "OPENCLAW_ENABLED", ""), False),
        feishu_app_id=_get(env, "OPENCLAW_FEISHU_APP_ID", "").strip(),
        feishu_app_secret=_get(env, "OPENCLAW_FEISHU_APP_SECRET", "").strip(),
        feishu_verify_token=_get(env, "OPENCLAW_FEISHU_VERIFY_TOKEN", "").strip(),
        feishu_encrypt_key=_get(env, "OPENCLAW_FEISHU_ENCRYPT_KEY", "").strip(),
        system_prompt=_get(
            env,
            "OPENCLAW_SYSTEM_PROMPT",
            "你是 OpenClaw 助手，用简洁准确的中文回答用户问题。",
        ),
        llm_max_tokens=int(_get(env, "OPENCLAW_LLM_MAX_TOKENS", "800") or "800"),
        llm_temperature=float(_get(env, "OPENCLAW_LLM_TEMPERATURE", "0.7") or "0.7"),
        llm_base_url=_get(env, "OPENCLAW_LLM_BASE_URL", "").strip(),
        llm_api_key=_get(env, "OPENCLAW_LLM_API_KEY", "").strip(),
        llm_model=_get(env, "OPENCLAW_LLM_MODEL", "gpt-4o-mini").strip(),
    )
