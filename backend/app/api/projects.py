from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
import json
import asyncio
import re
import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from pydub import AudioSegment
import imageio_ffmpeg

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.models.project import Project, Conversation
from app.models.task import Task
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ConversationCreate, ConversationResponse, ConversationUpdate, CustomScriptRequest
)
from app.schemas.task import TaskCreate, TaskResponse
from app.api.auth import get_current_user
from app.services.chat import ChatService
from app.services.manim import ManimService
from app.services.stickman_generator import StickmanGenerator as StickmanGeneratorLegacy
from app.services.stickman_generator_v2 import StickmanGenerator as StickmanGeneratorV2
from app.services.explainer_generator import ExplainerGenerator
from app.services.viral_voice_library import get_builtin_viral_voices
from app.services.audio_enhancement import enhance_voice_audio
from app.services.stickman_v2_assets import (
    public_background_templates,
    public_opening_styles,
    public_scene_style_libraries,
    find_asset_file,
    get_background_template,
    render_project_background_from_template,
    resolve_generation_assets,
)
from app.tasks.celery_tasks import generate_chat_celery
MODULE_LABELS = {
    "manim": "思维可视化",
    "math": "数学可视化",
    "stickman": "视频讲解",
    "explainer": "讲解型视频",
}

VOICE_PREVIEW_SAMPLE_TEXT = "你好，这是视频讲解模块的配音试听样本。"


def _build_stickman_generator(project: Project | None = None):
    if project and str(getattr(project, 'stickman_variant', 'legacy') or 'legacy') == 'v2':
        return StickmanGeneratorV2()
    return StickmanGeneratorLegacy()


def _stickman_variant_label(project: Project | None = None):
    return '增强讲解' if project and str(getattr(project, 'stickman_variant', 'legacy') or 'legacy') == 'v2' else '标准讲解'


def _apply_opening_image_override(project: Project, assets: list[dict], flags: dict):
    if not bool(flags.get("opening_intro_enabled", False)):
        return assets, flags
    try:
        preview_asset = json.loads(project.preview_image_asset_json or "null")
    except Exception:
        preview_asset = None
    if not isinstance(preview_asset, dict) or not assets:
        return assets, flags
    opening_scene_path = preview_asset.get("scene_image_path") or preview_asset.get("image_path")
    opening_scene_url = preview_asset.get("scene_image_url") or preview_asset.get("image_url")
    if not opening_scene_path or not opening_scene_url:
        return assets, flags
    first = dict(assets[0])
    first["scene_image_path"] = opening_scene_path
    first["scene_image_url"] = opening_scene_url
    first["scene_image_source"] = preview_asset.get("scene_image_source") or "uploaded_opening_image"
    first["scene_image_model_used"] = preview_asset.get("scene_image_model_used")
    first["error_summary"] = preview_asset.get("error_summary") or "已使用你指定的开头图作为第一幕。"
    updated_assets = list(assets)
    updated_assets[0] = first
    updated_flags = {**flags, "opening_image_locked": True}
    return updated_assets, updated_flags


def _build_explainer_generator():
    return ExplainerGenerator()


def _project_permission_module_key(module_type: str, stickman_variant: str | None = None):
    normalized_module = str(module_type or "manim")
    if normalized_module == "stickman":
        return "stickman_v2" if str(stickman_variant or "legacy") == "v2" else "stickman_legacy"
    if normalized_module in {"explainer", "article", "visual"}:
        return normalized_module
    if normalized_module in {"manim", "math"}:
        return "visual"
    return normalized_module


def _voice_preview_dir():
    preview_dir = Path(__file__).resolve().parents[2] / "uploads" / "voice_previews" / "library"
    preview_dir.mkdir(parents=True, exist_ok=True)
    return preview_dir


def _voice_preview_filename(provider: str, voice: str):
    normalized_provider = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(provider or "default")).strip("_") or "default"
    normalized_voice = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(voice or "voice")).strip("_") or "voice"
    return f"{normalized_provider}__{normalized_voice}.mp3"


def _voice_preview_url(filename: str):
    return f"/api/projects/stickman/voice-previews/{filename}"


def _resolve_voice_preview_request(filename: str):
    stem = Path(filename).stem
    if "__" not in stem:
        raise ValueError("invalid voice preview filename")
    provider, voice_id = stem.split("__", 1)
    provider = provider.strip() or "dashscope_cosyvoice"
    voice_id = voice_id.strip()
    if not voice_id:
        raise ValueError("missing voice id")
    return provider, voice_id


def _attach_voice_preview_urls(voices: list[dict]):
    enriched = []
    for raw_voice in voices or []:
        voice = dict(raw_voice or {})
        if str(voice.get("preview_url") or "").strip():
            enriched.append(voice)
            continue
        provider = str(voice.get("provider") or "dashscope_cosyvoice").strip() or "dashscope_cosyvoice"
        voice_id = str(voice.get("value") or "").strip()
        if not voice_id:
            enriched.append(voice)
            continue
        filename = _voice_preview_filename(provider, voice_id)
        voice["preview_url"] = _voice_preview_url(filename)
        enriched.append(voice)
    return enriched


def _resolve_stickman_generation_inputs(db: Session, project: Project):
    try:
        generation_flags = json.loads(project.generation_flags or "{}")
    except Exception:
        generation_flags = {}
    resolved = resolve_generation_assets(
        db,
        generation_flags,
        str(project.background_image_path) if project.background_image_path else None,
        str(project.style_reference_image_path) if project.style_reference_image_path else None,
        str(project.style_reference_notes) if project.style_reference_notes else None,
    )
    if resolved.get("opening_style_name"):
        generation_flags["opening_style_name"] = resolved["opening_style_name"]
    if resolved.get("background_template_name"):
        generation_flags["background_template_name"] = resolved["background_template_name"]
    return generation_flags, resolved


def _resolve_explainer_generation_inputs(db: Session, project: Project):
    try:
        generation_flags = json.loads(project.generation_flags or "{}")
    except Exception:
        generation_flags = {}
    resolved = resolve_generation_assets(
        db,
        generation_flags,
        str(project.background_image_path) if project.background_image_path else None,
        str(project.style_reference_image_path) if project.style_reference_image_path else None,
        str(project.style_reference_notes) if project.style_reference_notes else None,
    )
    if resolved.get("background_template_name"):
        generation_flags["background_template_name"] = resolved["background_template_name"]
    if resolved.get("scene_style_library"):
        generation_flags["scene_style_library"] = resolved["scene_style_library"]
    else:
        generation_flags.pop("scene_style_library", None)
    if resolved.get("scene_style_library_name"):
        generation_flags["scene_style_library_name"] = resolved["scene_style_library_name"]
    else:
        generation_flags.pop("scene_style_library_name", None)
    return generation_flags, resolved


def _load_generation_flags(raw_value: str | None) -> dict:
    try:
        value = json.loads(raw_value or "{}")
    except Exception:
        value = {}
    return value if isinstance(value, dict) else {}


def _strip_resolved_generation_assets(flags: dict | None) -> dict:
    next_flags = dict(flags or {})
    for key in {"scene_style_library", "scene_style_library_name"}:
        next_flags.pop(key, None)
    return next_flags


def _background_source(flags: dict) -> str:
    return str((flags or {}).get("background_image_source") or "").strip()


def _is_template_generated_background(project: Project, flags: dict | None = None) -> bool:
    source = _background_source(flags or _load_generation_flags(project.generation_flags))
    if source == "template_generated":
        return True
    current_path = str(project.background_image_path or "").strip()
    return bool(current_path and Path(current_path).name.startswith(f"project_{project.id}_template_"))


def _is_uploaded_background(project: Project, flags: dict | None = None) -> bool:
    source = _background_source(flags or _load_generation_flags(project.generation_flags))
    if source == "upload":
        return True
    current_path = str(project.background_image_path or "").strip()
    return bool(current_path and Path(current_path).name.startswith(f"project_{project.id}_upload_"))


def _delete_background_file(path: str | None):
    target = str(path or "").strip()
    if not target or not os.path.exists(target):
        return
    try:
        os.remove(target)
    except OSError:
        pass


def _project_query_for_user(db: Session, current_user: User):
    query = db.query(Project)
    if not current_user.is_admin:
        query = query.filter(Project.user_id == current_user.id)
    return query


def _project_video_file_from_url(video_url: str | None) -> Path | None:
    raw = str(video_url or '').strip()
    if not raw:
        return None
    direct = Path(raw)
    if direct.exists() and direct.is_file():
        return direct
    candidate_name = Path(urlsplit(raw).path).name
    if not candidate_name:
        return None
    search_dirs = [
        Path(__file__).resolve().parents[2] / 'videos',
        Path('/opt/manim/backend/videos'),
        Path('/opt/manim-v2/backend/videos'),
    ]
    for search_dir in search_dirs:
        candidate = search_dir / candidate_name
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _resolve_project_video_delivery_url(project: Project) -> str | None:
    video_url = str(getattr(project, 'video_url', '') or '').strip()
    if not video_url:
        return None
    local_file = _project_video_file_from_url(video_url)
    if local_file:
        return str(local_file)
    return video_url


def _normalize_project_video_url(project: Project):
    local_file = _project_video_file_from_url(getattr(project, 'video_url', None))
    if local_file:
        project.video_url = f"/api/videos/{local_file.name}"
    return project


def _project_background_title(project: Project):
    return str(project.title or project.theme or "").strip() or "主题内容"


def _sync_template_background(project: Project, db: Session, flags: dict, force_template: bool = False):
    next_flags = dict(flags or {})
    selected_key = str(next_flags.get("background_template_key") or "").strip()
    current_path = str(project.background_image_path or "").strip()
    uploaded_background = _is_uploaded_background(project, next_flags)
    template_generated_background = _is_template_generated_background(project, next_flags)

    if uploaded_background and current_path and not force_template:
        return next_flags, False

    if not selected_key:
        if template_generated_background and current_path:
            _delete_background_file(current_path)
            project.background_image_path = None
        next_flags.pop("background_image_source", None)
        return next_flags, template_generated_background

    template = get_background_template(db, selected_key)
    template_path = str((template or {}).get("background_image_path") or "").strip()
    if not template_path:
        return next_flags, False

    generated_path = render_project_background_from_template(template_path, _project_background_title(project), project.id)
    if current_path and current_path != generated_path and (template_generated_background or force_template):
        _delete_background_file(current_path)
    project.background_image_path = generated_path
    next_flags["background_image_source"] = "template_generated"
    return next_flags, True


def _invalidate_stickman_visual_outputs(project: Project):
    project.image_assets_json = None
    project.video_url = None
    project.status = "draft"
    project.error_message = None


def _invalidate_explainer_visual_outputs(project: Project):
    project.image_assets_json = None
    project.video_url = None
    project.status = "draft"
    project.error_message = None


def _clear_storyboard_english_subtitles(storyboards: list) -> tuple[list, bool]:
    cleaned_storyboards = []
    changed = False
    for scene in storyboards or []:
        next_scene = dict(scene or {})
        next_lines = []
        for item in list(next_scene.get("subtitle_lines") or []):
            next_item = dict(item or {})
            if str(next_item.get("english") or "").strip():
                changed = True
            next_item.pop("english", None)
            next_lines.append(next_item)
        next_scene["subtitle_lines"] = next_lines
        cleaned_storyboards.append(next_scene)
    return cleaned_storyboards, changed


def _preserve_matching_storyboard_english_subtitles(existing_storyboards: list, incoming_storyboards: list) -> list:
    merged_storyboards = []
    existing_scenes = list(existing_storyboards or [])
    for index, scene in enumerate(incoming_storyboards or []):
        next_scene = dict(scene or {})
        existing_scene = dict(existing_scenes[index] or {}) if index < len(existing_scenes) else {}
        existing_lines = list(existing_scene.get("subtitle_lines") or [])
        existing_english_by_text: dict[str, str] = {}
        for item in existing_lines:
            text = str((item or {}).get("text") or "").strip()
            english = str((item or {}).get("english") or "").strip()
            if text and english and text not in existing_english_by_text:
                existing_english_by_text[text] = english

        next_lines = []
        for item in list(next_scene.get("subtitle_lines") or []):
            next_item = dict(item or {})
            text = str(next_item.get("text") or "").strip()
            if text:
                next_item["text"] = text
                preserved_english = existing_english_by_text.get(text, "")
                current_english = str(next_item.get("english") or "").strip()
                next_item["english"] = current_english or preserved_english
            else:
                next_item.pop("english", None)
            next_lines.append(next_item)
        next_scene["subtitle_lines"] = next_lines
        merged_storyboards.append(next_scene)
    return merged_storyboards


def _invalidate_stickman_english_subtitles(project: Project):
    storyboards = json.loads(project.storyboard_json or "[]")
    cleaned_storyboards, changed = _clear_storyboard_english_subtitles(storyboards)
    if changed:
        project.storyboard_json = json.dumps(cleaned_storyboards, ensure_ascii=False)


def _stickman_visual_settings_changed(project: Project, data: dict) -> bool:
    if "background_image_path" in data:
        next_background = str(data.get("background_image_path") or "").strip()
        current_background = str(project.background_image_path or "").strip()
        if next_background != current_background:
            return True
    if "generation_flags" in data:
        current_flags = _load_generation_flags(project.generation_flags)
        next_flags = _load_generation_flags(data.get("generation_flags"))
        watched_keys = {
            "background_template_key",
            "opening_intro_enabled",
            "opening_style_key",
            "opening_template_key",
            "scene_style_library_key",
        }
        for key in watched_keys:
            if current_flags.get(key) != next_flags.get(key):
                return True
    return False


def _explainer_visual_settings_changed(project: Project, data: dict) -> bool:
    watched_scalar_keys = {"background_image_path", "style_reference_image_path", "style_reference_notes", "final_script", "title"}
    for key in watched_scalar_keys:
        if key in data:
            next_value = str(data.get(key) or "").strip()
            current_value = str(getattr(project, key, None) or "").strip()
            if next_value != current_value:
                return True
    if "generation_flags" in data:
        current_flags = _load_generation_flags(project.generation_flags)
        next_flags = _load_generation_flags(data.get("generation_flags"))
        watched_keys = {
            "background_template_key",
            "scene_style_library_key",
            "opening_hook_mode",
            "visual_style_key",
            "target_duration",
        }
        for key in watched_keys:
            if current_flags.get(key) != next_flags.get(key):
                return True
    return False

router = APIRouter(prefix="/projects", tags=["projects"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/stickman/voice-library")
def get_stickman_voice_library(
    current_user: Annotated[User, Depends(get_current_user)],
):
    generator = StickmanGeneratorLegacy()
    voices = generator.get_tts_voice_library()
    custom_voices = current_user.get_custom_voices() if hasattr(current_user, 'get_custom_voices') else []
    try:
        builtin_viral_voices = get_builtin_viral_voices()
    except Exception:
        builtin_viral_voices = []
    merged = builtin_viral_voices + voices + custom_voices
    return {"voices": _attach_voice_preview_urls(merged)}


@router.get("/stickman/voice-previews/{filename}")
def get_stickman_voice_preview_file(
    filename: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    preview_dir = _voice_preview_dir().resolve()
    preview_path = (preview_dir / Path(filename).name).resolve()
    if preview_path.parent != preview_dir:
        raise HTTPException(status_code=404, detail="试听音频不存在")
    if not preview_path.exists():
        try:
            provider, voice_id = _resolve_voice_preview_request(preview_path.name)
            generator = StickmanGeneratorV2()
            generator._generate_audio(VOICE_PREVIEW_SAMPLE_TEXT, str(preview_path), provider, voice_id, "+0%")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"试听音频生成失败: {exc}") from exc
    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="试听音频不存在")
    return FileResponse(preview_path, media_type="audio/mpeg", filename=preview_path.name)


@router.post("/stickman/preview-voice")
def preview_stickman_voice(
    payload: dict,
    current_user: Annotated[User, Depends(get_current_user)],
):
    generator = StickmanGeneratorLegacy()
    sample_text = str(payload.get("text") or "你好，这是一段视频讲解项目的配音试听。")
    provider = str(payload.get("tts_provider") or "dashscope_cosyvoice")
    voice = str(payload.get("tts_voice") or "longshuo_v3")
    rate = str(payload.get("tts_rate") or "+0%")

    temp_dir = Path(__file__).resolve().parents[2] / "uploads" / "voice_previews"
    temp_dir.mkdir(parents=True, exist_ok=True)
    preview_path = temp_dir / f"preview_{uuid.uuid4().hex[:12]}.mp3"
    generator._generate_audio(sample_text, str(preview_path), provider, voice, rate)
    return FileResponse(preview_path, media_type="audio/mpeg", filename=preview_path.name)


@router.get("/stickman/v2-config")
def get_stickman_v2_config(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return {
        "opening_styles": public_opening_styles(db),
        "background_templates": public_background_templates(db),
        "scene_style_libraries": public_scene_style_libraries(db),
    }


@router.get("/stickman/v2-assets/{kind}/{filename}")
def get_stickman_v2_public_asset(
    kind: str,
    filename: str,
    db: Annotated[Session, Depends(get_db)],
):
    if kind not in {"opening_styles", "background_templates", "scene_style_libraries"}:
        raise HTTPException(status_code=404, detail="资源不存在")
    asset_path = find_asset_file(db, kind, filename)
    if not asset_path or not asset_path.exists():
        raise HTTPException(status_code=404, detail="资源不存在")
    return FileResponse(asset_path)


@router.post("", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    MAX_PROJECTS = 3
    module_key = _project_permission_module_key(str(project.module_type or "manim"), str(project.stickman_variant or "legacy"))
    stickman_storyboard_limit = 20 if current_user.is_admin else 6
    if module_key == "stickman":
        if str(project.stickman_variant or "legacy") not in {"legacy", "v2"}:
            raise HTTPException(status_code=400, detail="stickman_variant 仅支持 legacy 或 v2")
        project.storyboard_count = max(2, min(int(project.storyboard_count or 3), stickman_storyboard_limit))
    elif module_key == "explainer":
        project.storyboard_count = max(3, min(int(project.storyboard_count or 6), 10))
    allowed, reason = current_user.can_use_module(module_key, db)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason or f"系统繁忙，请稍后再试")

    if not current_user.is_admin:
        project_count = db.query(Project).filter(Project.user_id == current_user.id).count()
        if project_count >= MAX_PROJECTS:
            raise HTTPException(
                status_code=400,
                detail=f"作品数量已达上限({MAX_PROJECTS}个)，请下载后删除旧作品"
            )
    
    new_project = Project(
        user_id=current_user.id,
        title=project.title,
        theme=project.theme,
        category=project.category,
        module_type=project.module_type,
        stickman_variant=(project.stickman_variant or "legacy") if project.module_type == "stickman" else "legacy",
        storyboard_count=project.storyboard_count,
        aspect_ratio=project.aspect_ratio,
        generation_mode=project.generation_mode,
        voice_source=project.voice_source,
        tts_provider=project.tts_provider,
        tts_voice=project.tts_voice,
        tts_rate=project.tts_rate,
        background_image_path=project.background_image_path,
    )
    if project.module_type == "stickman" and project.stickman_variant == "v2":
        new_project.generation_flags = json.dumps({}, ensure_ascii=False)
    elif project.module_type == "explainer":
        new_project.generation_flags = json.dumps({}, ensure_ascii=False)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    projects = db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.created_at.desc()).all()
    return [_normalize_project_video_url(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return _normalize_project_video_url(project)


@router.get("/{project_id}/video-download")
def download_project_video(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = _project_query_for_user(db, current_user).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    delivery_url = _resolve_project_video_delivery_url(project)
    if not delivery_url:
        raise HTTPException(status_code=404, detail="视频不存在")
    local_path = Path(str(delivery_url))
    if not local_path.exists():
        raise HTTPException(status_code=404, detail="视频不存在")
    return FileResponse(local_path, media_type='video/mp4', filename=local_path.name)


@router.post("/{project_id}/render-template-background", response_model=ProjectResponse)
def render_project_template_background(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = _project_query_for_user(db, current_user).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if str(project.module_type or "") not in {"stickman", "explainer"}:
        raise HTTPException(status_code=400, detail="当前项目不支持背景模板生成")

    flags = _load_generation_flags(project.generation_flags)
    template_key = str(flags.get("background_template_key") or "").strip()
    if not template_key:
        raise HTTPException(status_code=400, detail="请先选择背景模板")

    next_flags, changed = _sync_template_background(project, db, flags, force_template=True)
    project.generation_flags = json.dumps(next_flags, ensure_ascii=False)
    if changed:
        if str(project.module_type or "") == "explainer":
            _invalidate_explainer_visual_outputs(project)
        else:
            _invalidate_stickman_visual_outputs(project)
    db.commit()
    db.refresh(project)
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.module_type == "stickman":
        data = project_update.model_dump(exclude_unset=True)
        if "stickman_variant" in data and data["stickman_variant"] is not None:
            data["stickman_variant"] = str(data["stickman_variant"])
            if data["stickman_variant"] not in {"legacy", "v2"}:
                raise HTTPException(status_code=400, detail="stickman_variant 仅支持 legacy 或 v2")
        if "storyboard_count" in data and data["storyboard_count"] is not None:
            limit = 20 if current_user.is_admin else 6
            data["storyboard_count"] = max(2, min(int(data["storyboard_count"]), limit))
    elif project.module_type == "explainer":
        data = project_update.model_dump(exclude_unset=True)
        if "storyboard_count" in data and data["storyboard_count"] is not None:
            data["storyboard_count"] = max(3, min(int(data["storyboard_count"]), 10))
    else:
        data = project_update.model_dump(exclude_unset=True)

    if "generation_flags" in data:
        data["generation_flags"] = json.dumps(
            _strip_resolved_generation_assets(_load_generation_flags(data.get("generation_flags"))),
            ensure_ascii=False,
        )
    
    invalidate_stickman_visuals = project.module_type == "stickman" and _stickman_visual_settings_changed(project, data)
    invalidate_explainer_visuals = project.module_type == "explainer" and _explainer_visual_settings_changed(project, data)

    for key, value in data.items():
        setattr(project, key, value)

    if project.module_type in {"stickman", "explainer"} and any(key in data for key in {"generation_flags", "theme", "title"}):
        flags, background_changed = _sync_template_background(project, db, _load_generation_flags(project.generation_flags))
        project.generation_flags = json.dumps(flags, ensure_ascii=False)
        if background_changed:
            if project.module_type == "stickman":
                invalidate_stickman_visuals = True
            else:
                invalidate_explainer_visuals = True

    if invalidate_stickman_visuals:
        _invalidate_stickman_visual_outputs(project)
    if project.module_type == "stickman" and "final_script" in data:
        _invalidate_stickman_english_subtitles(project)
    if invalidate_explainer_visuals:
        _invalidate_explainer_visual_outputs(project)
    
    db.commit()
    db.refresh(project)
    return project


def _get_stickman_project(db: Session, current_user: User, project_id: int) -> Project:
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.module_type != "stickman":
        raise HTTPException(status_code=400, detail="Only stickman projects support this operation")
    return project


def _get_explainer_project(db: Session, current_user: User, project_id: int) -> Project:
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.module_type != "explainer":
        raise HTTPException(status_code=400, detail="Only explainer projects support this operation")
    return project


@router.post("/{project_id}/stickman/script", response_model=ProjectResponse)
def generate_stickman_script(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = _get_stickman_project(db, current_user, project_id)
    generator = _build_stickman_generator(project)
    try:
        generation_flags = json.loads(project.generation_flags or "{}")
    except Exception:
        generation_flags = {}
    project_final_script = str(project.final_script or "").strip()
    if project_final_script and hasattr(generator, "build_storyboards_from_script_text"):
        script_data = generator.build_storyboards_from_script_text(
            str(project.theme),
            project_final_script,
            include_intro_scene=bool(generation_flags.get("opening_intro_enabled", False)),
        )
        project.final_script = script_data.get("script") or project_final_script
    else:
        if str(getattr(project, 'stickman_variant', 'legacy') or 'legacy') == 'v2':
            script_data = generator.generate_script_data(
                str(project.theme),
                int(project.storyboard_count or 3),
                opening_template_key=str(generation_flags.get("opening_template_key") or "hook_question"),
                include_intro_scene=bool(generation_flags.get("opening_intro_enabled", False)),
            )
        else:
            script_data = generator.generate_script_data(str(project.theme), int(project.storyboard_count or 3), opening_template_key=str(generation_flags.get("opening_template_key") or "hook_question"))
        project.final_script = project_final_script or script_data.get("script")
    cleaned_storyboards, _ = _clear_storyboard_english_subtitles(script_data.get("storyboards") or [])
    project.storyboard_json = json.dumps(cleaned_storyboards, ensure_ascii=False)
    _invalidate_stickman_visual_outputs(project)
    project.status = "draft"
    project.error_message = None
    db.commit()
    db.refresh(project)
    return project


@router.put("/{project_id}/stickman/storyboards", response_model=ProjectResponse)
def update_stickman_storyboards(
    project_id: int,
    payload: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = _get_stickman_project(db, current_user, project_id)
    storyboards = payload.get("storyboards") or []
    final_script = payload.get("final_script")
    if not isinstance(storyboards, list) or not storyboards:
        raise HTTPException(status_code=400, detail="storyboards 不能为空")
    existing_storyboards = json.loads(project.storyboard_json or "[]")
    merged_storyboards = _preserve_matching_storyboard_english_subtitles(existing_storyboards, storyboards)
    project.storyboard_json = json.dumps(merged_storyboards, ensure_ascii=False)
    if isinstance(final_script, str):
        project.final_script = final_script
    _invalidate_stickman_visual_outputs(project)
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/stickman/english-subtitles", response_model=ProjectResponse)
def generate_stickman_english_subtitles(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = _get_stickman_project(db, current_user, project_id)
    storyboards = json.loads(project.storyboard_json or "[]")
    if not storyboards:
        raise HTTPException(status_code=400, detail="请先生成并确认分镜")

    generator = _build_stickman_generator(project)
    updated_storyboards = []
    pending_texts = []
    for scene in storyboards:
        clone = dict(scene)
        subtitle_lines = list(clone.get("subtitle_lines") or [])
        narration_text = str(clone.get("scene_narration") or clone.get("narration") or "").strip()
        if not subtitle_lines and narration_text:
            subtitle_lines = [{"text": narration_text}]

        next_lines = []
        for item in subtitle_lines:
            text = str((item or {}).get("text") or "").strip()
            if not text:
                continue
            next_item = dict(item or {})
            next_item["text"] = text
            next_item["english"] = generator._sanitize_english_subtitle(
                str((item or {}).get("english") or "").strip()
            )
            if not next_item["english"]:
                pending_texts.append(text)
            next_lines.append(next_item)

        clone["subtitle_lines"] = next_lines
        updated_storyboards.append(clone)

    translated_map = generator._translate_subtitles_to_english_batch(pending_texts)
    for scene in updated_storyboards:
        next_lines = []
        for item in scene.get("subtitle_lines") or []:
            text = str((item or {}).get("text") or "").strip()
            english = generator._sanitize_english_subtitle(str((item or {}).get("english") or "").strip())
            if not english and text:
                english = translated_map.get(text, "")
            next_item = dict(item or {})
            next_item["english"] = english
            next_lines.append(next_item)
        scene["subtitle_lines"] = next_lines

    project.storyboard_json = json.dumps(updated_storyboards, ensure_ascii=False)
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/stickman/images", response_model=ProjectResponse)
def generate_stickman_images(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = _get_stickman_project(db, current_user, project_id)
    storyboards = json.loads(project.storyboard_json or "[]")
    if not storyboards:
        raise HTTPException(status_code=400, detail="请先生成并确认分镜")
    
    if not getattr(project, 'quota_consumed', False):
        allowed, reason = current_user.can_use_module(_project_permission_module_key('stickman', str(getattr(project, 'stickman_variant', 'legacy') or 'legacy')), db)
        if not allowed:
            raise HTTPException(status_code=403, detail=reason or '系统繁忙，请稍后再试')
    
    generator = _build_stickman_generator(project)
    generation_flags, resolved_inputs = _resolve_stickman_generation_inputs(db, project)
    if resolved_inputs.get("scene_style_library"):
        generation_flags["scene_style_library"] = resolved_inputs["scene_style_library"]
    if resolved_inputs.get("scene_style_library_name"):
        generation_flags["scene_style_library_name"] = resolved_inputs["scene_style_library_name"]
    assets, flags = generator.generate_images(
        storyboards,
        str(project.aspect_ratio or "16:9"),
        project_id,
        topic=str(project.theme),
        background_image_path=resolved_inputs.get("background_image_path"),
        style_reference_image_path=resolved_inputs.get("style_reference_image_path"),
        style_reference_notes=resolved_inputs.get("style_reference_notes"),
        generation_flags=generation_flags,
    )
    assets, flags = _apply_opening_image_override(project, assets, flags)
    flags["stickman_variant"] = str(getattr(project, 'stickman_variant', 'legacy') or 'legacy')
    flags["stickman_variant_label"] = _stickman_variant_label(project)
    project.image_assets_json = json.dumps(assets, ensure_ascii=False)
    project.generation_flags = json.dumps(flags, ensure_ascii=False)
    
    if not getattr(project, 'quota_consumed', False):
        current_user.increment_module_usage(_project_permission_module_key('stickman', str(getattr(project, 'stickman_variant', 'legacy') or 'legacy')))
        project.quota_consumed = True
    
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/stickman/preview-image", response_model=ProjectResponse)
def generate_stickman_preview_image(
    project_id: int,
    payload: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = _get_stickman_project(db, current_user, project_id)
    storyboards = json.loads(project.storyboard_json or "[]")
    if not storyboards:
        raise HTTPException(status_code=400, detail="请先生成并确认分镜")

    preview_count = int(project.preview_regen_count or 0)
    if not current_user.is_admin and preview_count >= 2:
        raise HTTPException(status_code=403, detail="每个项目最多生成2次预览图，已达上限")

    generator = _build_stickman_generator(project)
    generation_flags, resolved_inputs = _resolve_stickman_generation_inputs(db, project)
    preview_index = 0
    preview_scene = storyboards[preview_index]
    asset, _ = generator.regenerate_single_image(
        preview_scene,
        preview_index + 1,
        str(project.aspect_ratio or "16:9"),
        project_id,
        None,
        resolved_inputs.get("background_image_path"),
        resolved_inputs.get("style_reference_image_path"),
        resolved_inputs.get("style_reference_notes"),
    )
    if isinstance(asset, dict):
        asset["stickman_variant"] = str(getattr(project, 'stickman_variant', 'legacy') or 'legacy')
    project.preview_image_asset_json = json.dumps(asset, ensure_ascii=False)
    project.preview_regen_count = preview_count + 1
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/stickman/opening-image", response_model=ProjectResponse)
async def upload_stickman_opening_image(
    project_id: int,
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    project = _get_stickman_project(db, current_user, project_id)
    suffix = Path(file.filename or "opening.png").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=400, detail="仅支持 png/jpg/jpeg/webp 图片")
    base_dir = Path(__file__).resolve().parents[2] / "uploads" / "stickman_images" / "opening_images"
    base_dir.mkdir(parents=True, exist_ok=True)
    image_path = base_dir / f"project_{project_id}_upload_{uuid.uuid4().hex}{suffix}"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="图片文件为空")
    with open(image_path, "wb") as buffer:
        buffer.write(content)
    project.preview_image_asset_json = json.dumps({
        "scene_id": 1,
        "scene_image_path": str(image_path),
        "scene_image_url": f"/api/stickman-images/{image_path.name}",
        "scene_image_source": "uploaded_opening_image",
        "image_path": str(image_path),
        "image_url": f"/api/stickman-images/{image_path.name}",
        "used_fallback": False,
        "error_summary": "已上传开头图，生成时会直接作为第一幕使用。",
    }, ensure_ascii=False)
    project.preview_regen_count = 0
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/stickman/images/{scene_index}/regenerate", response_model=ProjectResponse)
def regenerate_stickman_image(
    project_id: int,
    scene_index: int,
    payload: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = _get_stickman_project(db, current_user, project_id)
    if not current_user.is_admin:
        raise HTTPException(status_code=400, detail="正式分镜图不支持重生，请先修改文案或使用预览图确认风格")
    storyboards = json.loads(project.storyboard_json or "[]")
    assets = json.loads(project.image_assets_json or "[]")
    if not (0 <= scene_index < len(storyboards)):
        raise HTTPException(status_code=404, detail="分镜不存在")
    generator = _build_stickman_generator(project)
    prompt_override = payload.get("prompt")
    generation_flags, resolved_inputs = _resolve_stickman_generation_inputs(db, project)
    asset, used_fallback = generator.regenerate_single_image(
        storyboards[scene_index],
        scene_index + 1,
        str(project.aspect_ratio or "16:9"),
        project_id,
        prompt_override if isinstance(prompt_override, str) else None,
        resolved_inputs.get("background_image_path"),
        resolved_inputs.get("style_reference_image_path"),
        resolved_inputs.get("style_reference_notes"),
    )
    while len(assets) <= scene_index:
        assets.append({})
    assets[scene_index] = asset
    flags = dict(generation_flags)
    flags[f"scene_{scene_index + 1}_fallback"] = used_fallback
    project.image_assets_json = json.dumps(assets, ensure_ascii=False)
    project.generation_flags = json.dumps(flags, ensure_ascii=False)
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/explainer/storyboard", response_model=ProjectResponse)
def generate_explainer_storyboard(
    project_id: int,
    payload: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = _get_explainer_project(db, current_user, project_id)
    generator = _build_explainer_generator()
    try:
        generation_flags = json.loads(project.generation_flags or "{}")
    except Exception:
        generation_flags = {}
    opening_hook_mode = str(payload.get("opening_hook_mode") or generation_flags.get("opening_hook_mode") or "hook_question")
    visual_style_key = str(payload.get("visual_style_key") or generation_flags.get("visual_style_key") or "deep_blue_emotional")
    target_duration_value = payload.get("target_duration")
    target_duration = int(target_duration_value) if target_duration_value not in (None, "") else None
    source_text = str(project.final_script or "").strip() or str(project.theme)
    result = generator.generate_storyboard_data(
        source_text,
        int(project.storyboard_count or 6),
        opening_hook_mode,
        visual_style_key,
        target_duration,
    )
    project.title = str(project.title or "").strip() or str(project.theme or "").strip()
    project.final_script = result.get("script")
    project.storyboard_json = json.dumps(result.get("storyboards") or [], ensure_ascii=False)
    project.generation_flags = json.dumps({**generation_flags, **(result.get("generation_flags") or {})}, ensure_ascii=False)
    project.status = "draft"
    project.error_message = None
    db.commit()
    db.refresh(project)
    return project


@router.put("/{project_id}/explainer/storyboard", response_model=ProjectResponse)
def update_explainer_storyboard(
    project_id: int,
    payload: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = _get_explainer_project(db, current_user, project_id)
    storyboards = payload.get("storyboards") or []
    if not isinstance(storyboards, list) or not storyboards:
        raise HTTPException(status_code=400, detail="storyboards 不能为空")
    if isinstance(payload.get("title"), str) and payload.get("title").strip():
        project.title = payload.get("title").strip()
    if isinstance(payload.get("final_script"), str):
        project.final_script = payload.get("final_script")
    if isinstance(payload.get("generation_flags"), dict):
        try:
            old_flags = json.loads(project.generation_flags or "{}")
        except Exception:
            old_flags = {}
        project.generation_flags = json.dumps(
            _strip_resolved_generation_assets({**old_flags, **payload.get("generation_flags")}),
            ensure_ascii=False,
        )
    project.storyboard_json = json.dumps(storyboards, ensure_ascii=False)
    _invalidate_explainer_visual_outputs(project)
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/explainer/images", response_model=ProjectResponse)
def generate_explainer_images(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = _get_explainer_project(db, current_user, project_id)
    storyboards = json.loads(project.storyboard_json or "[]")
    if not storyboards:
        raise HTTPException(status_code=400, detail="请先生成并确认分镜")
    if not getattr(project, 'quota_consumed', False):
        allowed, reason = current_user.can_use_module(_project_permission_module_key('explainer'), db)
        if not allowed:
            raise HTTPException(status_code=403, detail=reason or '系统繁忙，请稍后再试')
    try:
        generation_flags, resolved_inputs = _resolve_explainer_generation_inputs(db, project)
    except Exception:
        generation_flags, resolved_inputs = {}, {}
    generator = _build_explainer_generator()
    synced_storyboards, assets, flags = generator.generate_images(
        str(project.theme),
        storyboards,
        str(project.aspect_ratio or "16:9"),
        project_id,
        None,
        resolved_inputs.get("background_image_path"),
        resolved_inputs.get("style_reference_image_path"),
        resolved_inputs.get("style_reference_notes"),
        generation_flags,
    )
    project.storyboard_json = json.dumps(synced_storyboards, ensure_ascii=False)
    project.image_assets_json = json.dumps(assets, ensure_ascii=False)
    project.generation_flags = json.dumps(flags, ensure_ascii=False)
    if not getattr(project, 'quota_consumed', False):
        current_user.increment_module_usage(_project_permission_module_key('explainer'))
        project.quota_consumed = True
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/explainer/images/{scene_index}/regenerate", response_model=ProjectResponse)
def regenerate_explainer_image(
    project_id: int,
    scene_index: int,
    payload: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = _get_explainer_project(db, current_user, project_id)
    storyboards = json.loads(project.storyboard_json or "[]")
    assets = json.loads(project.image_assets_json or "[]")
    if not (0 <= scene_index < len(storyboards)):
        raise HTTPException(status_code=404, detail="分镜不存在")
    try:
        generation_flags, resolved_inputs = _resolve_explainer_generation_inputs(db, project)
    except Exception:
        generation_flags, resolved_inputs = {}, {}
    generator = _build_explainer_generator()
    updated_scene, asset, used_fallback = generator.regenerate_single_image(
        str(project.theme),
        storyboards,
        scene_index,
        str(project.aspect_ratio or "16:9"),
        project_id,
        payload.get("prompt") if isinstance(payload.get("prompt"), str) else None,
        resolved_inputs.get("background_image_path"),
        resolved_inputs.get("style_reference_image_path"),
        resolved_inputs.get("style_reference_notes"),
        generation_flags,
    )
    storyboards[scene_index] = updated_scene
    while len(assets) <= scene_index:
        assets.append({})
    assets[scene_index] = asset
    generation_flags[f"scene_{scene_index + 1}_fallback"] = used_fallback
    project.storyboard_json = json.dumps(storyboards, ensure_ascii=False)
    project.image_assets_json = json.dumps(assets, ensure_ascii=False)
    project.generation_flags = json.dumps(generation_flags, ensure_ascii=False)
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/voice-reference", response_model=ProjectResponse)
async def upload_voice_reference(
    project_id: int,
    file: UploadFile = File(...),
    source: str = Form("upload"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.module_type not in {"stickman", "explainer"}:
        raise HTTPException(status_code=400, detail="Only stickman or explainer projects support voice upload")

    suffix = Path(file.filename or "voice.wav").suffix.lower()
    if suffix not in {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".webm"}:
        raise HTTPException(status_code=400, detail="仅支持 mp3/wav/m4a/aac/ogg/webm 音频文件")

    base_dir = Path(__file__).resolve().parents[2] / "uploads" / "voice_references"
    base_dir.mkdir(parents=True, exist_ok=True)
    raw_path = base_dir / f"project_{project_id}_{uuid.uuid4().hex}{suffix}"
    normalized_path = raw_path.with_suffix(".mp3")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="音频文件为空")

    with open(raw_path, "wb") as buffer:
        buffer.write(content)

    try:
        duration_ms = enhance_voice_audio(str(raw_path), str(normalized_path), imageio_ffmpeg.get_ffmpeg_exe(), output_format='mp3')
    except Exception as exc:
        if raw_path.exists():
            os.remove(raw_path)
        raise HTTPException(status_code=400, detail=f"音频处理失败: {exc}") from exc
    finally:
        if raw_path.exists():
            os.remove(raw_path)

    if project.voice_file_path and os.path.exists(project.voice_file_path):
        try:
            os.remove(project.voice_file_path)
        except OSError:
            pass

    project.voice_file_path = str(normalized_path)
    project.voice_duration = duration_ms
    project.voice_source = source if source in {"upload", "record"} else "upload"
    db.commit()
    db.refresh(project)
    return project


@router.post("/stickman/custom-voice")
async def create_custom_voice(
    file: UploadFile = File(...),
    label: str = Form(...),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    suffix = Path(file.filename or 'voice.wav').suffix.lower()
    if suffix not in {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.webm'}:
        raise HTTPException(status_code=400, detail='仅支持 mp3/wav/m4a/aac/ogg/webm 音频文件')

    base_dir = Path(__file__).resolve().parents[2] / 'uploads' / 'custom_voice_sources'
    base_dir.mkdir(parents=True, exist_ok=True)
    raw_path = base_dir / f'user_{current_user.id}_{uuid.uuid4().hex}{suffix}'
    normalized_path = raw_path.with_suffix('.mp3')
    clone_source_path = raw_path.with_suffix('.wav')
    content = await file.read()
    with open(raw_path, 'wb') as buffer:
        buffer.write(content)

    try:
        enhanced_ms = enhance_voice_audio(str(raw_path), str(normalized_path), imageio_ffmpeg.get_ffmpeg_exe(), output_format='mp3')
        enhance_voice_audio(str(raw_path), str(clone_source_path), imageio_ffmpeg.get_ffmpeg_exe(), output_format='wav')
        if enhanced_ms < 8000:
            raise HTTPException(status_code=400, detail='样本音频有效时长过短，建议至少录制 8 秒清晰人声后再创建自定义音色')
        from app.utils.cos_storage import cos_storage
        public_url = None
        if cos_storage.enabled:
          with open(clone_source_path, 'rb') as f:
            uploaded = cos_storage.upload_image(f.read(), f'voices/samples/user_{current_user.id}_{uuid.uuid4().hex}.wav', content_type='audio/wav')
            if uploaded:
              public_url = cos_storage.get_public_url(uploaded)
        if not public_url:
            raise HTTPException(status_code=400, detail='当前未启用可访问的音频样本地址，无法创建自定义音色')

        import requests as pyrequests
        api_key = get_settings().DASHSCOPE_API_KEY
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        payload = {
            'model': 'voice-enrollment',
            'input': {
                'action': 'create_voice',
                'target_model': 'cosyvoice-v3.5-plus',
                'prefix': f'u{current_user.id}'[:8],
                'url': public_url,
            },
        }
        response = pyrequests.post('https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization', headers=headers, json=payload, timeout=120)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f'创建自定义音色失败: {response.text[:500]}')
        result = response.json()
        voice_id = (result.get('output') or {}).get('voice_id')
        if not voice_id:
            raise HTTPException(status_code=400, detail=f'创建自定义音色失败: {result}')
        preview_audio = ((result.get('output') or {}).get('preview_audio') or {}).get('url')
        custom_voice = {
            'label': label,
            'value': voice_id,
            'provider': 'dashscope_cosyvoice',
            'gender': 'custom',
            'style': 'personal',
            'preview_url': preview_audio,
        }
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail='用户不存在')
        user.add_custom_voice(custom_voice)
        db.commit()
        return {'message': '自定义音色创建成功', 'voice': custom_voice}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'创建自定义音色异常: {exc}') from exc
    finally:
        if raw_path.exists():
            os.remove(raw_path)
        if clone_source_path.exists():
            os.remove(clone_source_path)


@router.post("/{project_id}/style-reference", response_model=ProjectResponse)
async def upload_style_reference(
    project_id: int,
    file: UploadFile = File(...),
    notes: str = Form(""),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.module_type not in {"stickman", "explainer"}:
        raise HTTPException(status_code=400, detail="Only stickman or explainer projects support style reference")

    suffix = Path(file.filename or "style.png").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=400, detail="仅支持 png/jpg/jpeg/webp 图片")

    base_dir = Path(__file__).resolve().parents[2] / "uploads" / "style_references"
    base_dir.mkdir(parents=True, exist_ok=True)
    image_path = base_dir / f"project_{project_id}_{uuid.uuid4().hex}{suffix}"

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="图片文件为空")
    with open(image_path, "wb") as buffer:
        buffer.write(content)

    if project.style_reference_image_path and os.path.exists(project.style_reference_image_path):
        try:
            os.remove(project.style_reference_image_path)
        except OSError:
            pass

    project.style_reference_image_path = str(image_path)
    project.style_reference_notes = notes or None
    if project.module_type == "explainer":
        generator = _build_explainer_generator().engine
    else:
        generator = _build_stickman_generator(project)
    project.style_reference_profile = generator.extract_style_reference_profile(str(image_path), notes or None)
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/background-image", response_model=ProjectResponse)
async def upload_background_image(
    project_id: int,
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.module_type not in {"manim", "stickman", "explainer"}:
        raise HTTPException(status_code=400, detail="Only manim, stickman or explainer projects support background image")

    suffix = Path(file.filename or "background.png").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=400, detail="仅支持 png/jpg/jpeg/webp 图片")

    base_dir = Path(__file__).resolve().parents[2] / "uploads" / "background_images"
    base_dir.mkdir(parents=True, exist_ok=True)
    image_path = base_dir / f"project_{project_id}_{uuid.uuid4().hex}{suffix}"

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="背景图文件为空")
    with open(image_path, "wb") as buffer:
        buffer.write(content)

    _delete_background_file(project.background_image_path)

    project.background_image_path = str(image_path)
    next_flags = _load_generation_flags(project.generation_flags)
    next_flags["background_image_source"] = "upload"
    project.generation_flags = json.dumps(next_flags, ensure_ascii=False)
    if str(project.module_type or "") == "explainer":
        _invalidate_explainer_visual_outputs(project)
    else:
        _invalidate_stickman_visual_outputs(project)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.query(Conversation).filter(Conversation.project_id == project_id).delete()
    db.query(Task).filter(Task.project_id == project_id).delete()
    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}


@router.post("/batch-delete")
def batch_delete_projects(
    data: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project_ids = data.get("project_ids", [])
    if not project_ids:
        raise HTTPException(status_code=400, detail="No project IDs provided")
    
    deleted_count = 0
    for project_id in project_ids:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()
        if project:
            if project.voice_file_path and os.path.exists(project.voice_file_path):
                try:
                    os.remove(project.voice_file_path)
                except OSError:
                    pass
            db.query(Conversation).filter(Conversation.project_id == project_id).delete()
            db.query(Task).filter(Task.project_id == project_id).delete()
            db.delete(project)
            deleted_count += 1
    
    db.commit()
    return {"message": f"Deleted {deleted_count} projects", "deleted_count": deleted_count}


@router.get("/{project_id}/conversations", response_model=List[ConversationResponse])
def get_conversations(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    conversations = db.query(Conversation).filter(
        Conversation.project_id == project_id
    ).order_by(Conversation.created_at).all()
    return conversations


@router.post("/{project_id}/chat", response_model=ConversationResponse)
@limiter.limit("10/minute")
async def send_message(
    request: Request,
    project_id: int,
    message: ConversationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """发送消息 - 立即返回，不等待AI响应"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    user_message = Conversation(
        project_id=project_id,
        role="user",
        content=message.content
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    return user_message


@router.post("/{project_id}/chat/stream")
async def chat_stream(
    project_id: int,
    message: ConversationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    style_code: str = None
):
    """流式聊天 - SSE 输出"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    theme = str(project.theme)
    
    # 获取模板代码
    template_code = None
    if project.template_id:
        from app.models.template import Template
        template = db.query(Template).filter(Template.id == project.template_id).first()
        if template:
            template_code = template.code
    
    # 提取数据，避免会话问题
    project_manim_code = str(project.manim_code) if project.manim_code else None
    project_final_script = str(project.final_script) if project.final_script else None
    
    user_message = Conversation(
        project_id=project_id,
        role="user",
        content=message.content
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    async def event_generator():
        chat_service = ChatService(db)
        
        full_content = ""
        reasoning_content = ""
        
        try:
            async for chunk in chat_service.stream_process_message(
                project_id, theme, message.content,
                manim_code=project_manim_code,
                template_code=template_code,
                final_script=project_final_script,
                style_code=style_code
            ):
                chunk_type = chunk.get("type")
                
                if chunk_type == "reasoning":
                    reasoning_content += chunk["content"]
                    yield f"data: {json.dumps({'type': 'reasoning', 'content': chunk['content']})}\n\n"
                elif chunk_type == "content":
                    full_content += chunk["content"]
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk['content']})}\n\n"
                elif chunk_type == "final":
                    yield f"data: {json.dumps({'type': 'done', 'content': chunk['content'], 'is_final': True})}\n\n"
                elif chunk_type == "done":
                    ai_msg = Conversation(
                        project_id=project_id,
                        role="assistant",
                        content=full_content
                    )
                    db.add(ai_msg)
                    
                    proj = db.query(Project).filter(Project.id == project_id).first()
                    if proj:
                        if chunk.get("is_final"):
                            proj.status = "chatting_completed"
                        if chunk.get("final_script"):
                            proj.final_script = chunk["final_script"]
                    
                    db.commit()
                    
                    result = {
                        'type': 'done', 
                        'content': full_content, 
                        'is_final': chunk.get('is_final', False)
                    }
                    if chunk.get("code_updated"):
                        result['code_updated'] = True
                        result['updated_code'] = chunk['updated_code']
                        result['has_template'] = project.template_id is not None
                    
                    yield f"data: {json.dumps(result)}\n\n"
                elif chunk_type == "error":
                    yield f"data: {json.dumps({'type': 'error', 'error': chunk['error']})}\n\n"
                
                await asyncio.sleep(0.01)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/{project_id}/chat/async")
async def chat_async(
    project_id: int,
    message: ConversationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    style_code: str = None
):
    """后台异步聊天，可关闭页面后继续生成"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    user_message = Conversation(
        project_id=project_id,
        role="user",
        content=message.content
    )
    db.add(user_message)

    task = Task(
        project_id=project_id,
        user_id=current_user.id,
        task_type="chat_generation",
        status="pending",
        progress=0
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    celery_result = generate_chat_celery.delay(task.id, project_id, message.content, style_code)
    task.celery_task_id = celery_result.id
    db.commit()

    return {
        "task_id": task.id,
        "celery_task_id": celery_result.id,
        "message": "对话生成已开始，可关闭页面"
    }


@router.get("/{project_id}/chat/latest-task")
async def get_latest_chat_task(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    task = db.query(Task).filter(
        Task.project_id == project_id,
        Task.user_id == current_user.id,
        Task.task_type == "chat_generation"
    ).order_by(Task.created_at.desc()).first()

    if not task:
        return {
            "task_id": None,
            "status": None,
            "progress": 0,
            "message": None,
            "error": None
        }

    task_message = task.error_message
    if not task_message and task.log:
        lines = [line.strip() for line in task.log.splitlines() if line.strip()]
        task_message = lines[-1] if lines else None

    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress or 0,
        "message": task_message,
        "error": task.error_message
    }


@router.get("/{project_id}/chat/pending")
async def get_pending_response(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """获取AI响应 - 前端轮询此接口"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 获取最新的用户消息
    last_user = db.query(Conversation).filter(
        Conversation.project_id == project_id,
        Conversation.role == "user"
    ).order_by(Conversation.created_at.desc()).first()
    
    if not last_user:
        return {"status": "no_message"}
    
    # 检查是否已有AI回复
    last_ai = db.query(Conversation).filter(
        Conversation.project_id == project_id,
        Conversation.role == "assistant",
        Conversation.created_at > last_user.created_at
    ).order_by(Conversation.created_at.asc()).first()
    
    if last_ai:
        # 已处理过，返回已有回复
        if last_ai.content.startswith("【"):
            return {
                "status": "completed",
                "response": last_ai,
                "has_final_script": True
            }
        return {"status": "completed", "response": last_ai}
    
    # 生成AI响应
    try:
        chat_service = ChatService(db)
        project_theme = str(project.theme)
        response = await chat_service.process_message(project_id, project_theme, last_user.content)
        
        assistant_message = Conversation(
            project_id=project_id,
            role="assistant",
            content=response["content"]
        )
        db.add(assistant_message)
        
        if response.get("is_final"):
            project.final_script = response.get("final_script")
            project.status = "chatting_completed"
        
        db.commit()
        db.refresh(assistant_message)
        
        return {
            "status": "completed",
            "response": assistant_message,
            "has_final_script": response.get("is_final", False)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/{project_id}/regenerate-code")
async def regenerate_code(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """重新生成代码（基于最新的final_script）"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.final_script:
        raise HTTPException(status_code=400, detail="No final script to generate code from")
    
    manim_service = ManimService(db)
    template_code = ""
    if project.template_id:
        from app.models.template import Template
        template = db.query(Template).filter(Template.id == project.template_id).first()
        if template:
            template_code = template.code
    
    manim_code = await manim_service.generate_code(
        project.final_script,
        template_code=template_code,
        video_title=str(project.title or "").strip() or str(project.theme or "").strip()
    )
    
    project.manim_code = manim_code
    project.status = "chatting"
    db.commit()
    
    return {"message": "代码已重新生成", "code_updated": True}


@router.post("/{project_id}/optimize-code")
async def optimize_code(
    project_id: int,
    feedback: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """根据用户反馈优化代码"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.manim_code:
        raise HTTPException(status_code=400, detail="No code to optimize")
    
    # 使用AI根据反馈优化代码
    manim_service = ManimService(db)
    optimized_code = await manim_service.optimize_code(
        project.manim_code,
        project.final_script or "",
        feedback
    )
    
    project.manim_code = optimized_code
    db.commit()
    
    return {"message": "代码已根据反馈优化", "code_updated": True}


@router.post("/{project_id}/optimize-code/stream")
async def optimize_code_stream(
    project_id: int,
    feedback: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """流式优化代码 - 用于渲染失败后的一键修复"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.manim_code:
        raise HTTPException(status_code=400, detail="No code to optimize")
    
    # 在生成器外部提取数据，避免会话问题
    current_code = str(project.manim_code)
    current_final_script = str(project.final_script or "")
    
    async def event_generator():
        manim_service = ManimService(db)
        
        try:
            yield f"data: {json.dumps({'type': 'progress', 'message': '正在分析错误...'})}\n\n"
            await asyncio.sleep(0.3)
            
            yield f"data: {json.dumps({'type': 'progress', 'message': '正在修复代码...'})}\n\n"
            
            optimized_code = await manim_service.optimize_code(
                current_code,
                current_final_script,
                feedback
            )
            
            yield f"data: {json.dumps({'type': 'code', 'code': optimized_code})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.put("/conversations/{conv_id}")
async def update_conversation(
    conv_id: int,
    data: ConversationUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """修改对话内容"""
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    project = db.query(Project).filter(Project.id == conv.project_id).first()
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")
    
    conv.content = data.content
    
    if conv.role == 'assistant':
        project.final_script = data.content
    
    db.commit()
    
    return {
        "message": "更新成功",
        "conversation": {
            "id": conv.id,
            "content": conv.content,
            "role": conv.role
        },
        "final_script_updated": conv.role == 'assistant'
    }


@router.post("/{project_id}/use-custom-script")
async def use_custom_script(
    project_id: int,
    data: CustomScriptRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """使用自定义文案"""
    from app.services.script_formatter import ScriptFormatter
    
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")
    
    final_script = data.script
    
    # 如果启用自动格式化，且不是标准格式，则转换
    if data.auto_format and not ScriptFormatter.is_formatted_script(data.script):
        try:
            final_script = await ScriptFormatter.format_user_script(data.script)
        except Exception as e:
            # 格式化失败，使用原始文案
            print(f"Script formatting failed: {e}")
    
    project.final_script = final_script
    project.status = "chatting_completed"
    if str(project.module_type or "") == "stickman":
        _invalidate_stickman_english_subtitles(project)
        _invalidate_stickman_visual_outputs(project)
    if str(project.module_type or "") == "explainer":
        _invalidate_explainer_visual_outputs(project)

    conv = Conversation(
        project_id=project_id,
        role="user",
        content=f"[自定义文案]\n{final_script}"
    )
    db.add(conv)
    
    db.commit()
    
    return {
        "message": "文案已保存",
        "final_script": final_script,
        "formatted": data.auto_format and final_script != data.script
    }
