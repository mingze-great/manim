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
from app.services.audio_enhancement import enhance_voice_audio
from app.tasks.celery_tasks import generate_chat_celery


MODULE_LABELS = {
    "manim": "思维可视化",
    "math": "数学可视化",
    "stickman": "视频讲解",
    "explainer": "讲解型视频",
}


def _build_stickman_generator(project: Project | None = None):
    if project and str(getattr(project, 'stickman_variant', 'legacy') or 'legacy') == 'v2':
        return StickmanGeneratorV2()
    return StickmanGeneratorLegacy()


def _stickman_variant_label(project: Project | None = None):
    return '增强讲解' if project and str(getattr(project, 'stickman_variant', 'legacy') or 'legacy') == 'v2' else '标准讲解'


def _apply_opening_image_override(project: Project, assets: list[dict], flags: dict):
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

router = APIRouter(prefix="/projects", tags=["projects"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/stickman/voice-library")
def get_stickman_voice_library(
    current_user: Annotated[User, Depends(get_current_user)],
): 
    generator = StickmanGeneratorLegacy()
    voices = generator.get_tts_voice_library()
    custom_voices = current_user.get_custom_voices() if hasattr(current_user, 'get_custom_voices') else []
    return {"voices": voices + custom_voices}


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


@router.post("", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    MAX_PROJECTS = 3
    module_key = str(project.module_type or "manim")
    if module_key in ("manim", "math"):
        module_key = "visual"
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
    return projects


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
    
    for key, value in data.items():
        setattr(project, key, value)
    
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
        script_data = generator.build_storyboards_from_script_text(str(project.theme), project_final_script)
    else:
        script_data = generator.generate_script_data(str(project.theme), int(project.storyboard_count or 3), opening_template_key=str(generation_flags.get("opening_template_key") or "hook_question"))
    project.final_script = script_data.get("script")
    project.storyboard_json = json.dumps(script_data.get("storyboards") or [], ensure_ascii=False)
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
    project.storyboard_json = json.dumps(storyboards, ensure_ascii=False)
    if isinstance(final_script, str):
        project.final_script = final_script
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
        allowed, reason = current_user.can_use_module('stickman', db)
        if not allowed:
            raise HTTPException(status_code=403, detail=reason or '系统繁忙，请稍后再试')
    
    generator = _build_stickman_generator(project)
    try:
        generation_flags = json.loads(project.generation_flags or "{}")
    except Exception:
        generation_flags = {}
    assets, flags = generator.generate_images(
        storyboards,
        str(project.aspect_ratio or "16:9"),
        project_id,
        topic=str(project.theme),
        background_image_path=str(project.background_image_path) if project.background_image_path else None,
        style_reference_image_path=str(project.style_reference_image_path) if project.style_reference_image_path else None,
        style_reference_notes=str(project.style_reference_notes) if project.style_reference_notes else None,
        generation_flags=generation_flags,
    )
    assets, flags = _apply_opening_image_override(project, assets, flags)
    flags["stickman_variant"] = str(getattr(project, 'stickman_variant', 'legacy') or 'legacy')
    flags["stickman_variant_label"] = _stickman_variant_label(project)
    project.image_assets_json = json.dumps(assets, ensure_ascii=False)
    project.generation_flags = json.dumps(flags, ensure_ascii=False)
    
    if not getattr(project, 'quota_consumed', False):
        current_user.increment_module_usage('stickman')
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
    preview_index = 0
    preview_scene = storyboards[preview_index]
    asset, _ = generator.regenerate_single_image(
        preview_scene,
        preview_index + 1,
        str(project.aspect_ratio or "16:9"),
        project_id,
        None,
        str(project.background_image_path) if project.background_image_path else None,
        str(project.style_reference_image_path) if project.style_reference_image_path else None,
        str(project.style_reference_notes) if project.style_reference_notes else None,
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
    image_path = base_dir / f"project_{project_id}_{uuid.uuid4().hex}{suffix}"
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
    asset, used_fallback = generator.regenerate_single_image(
        storyboards[scene_index],
        scene_index + 1,
        str(project.aspect_ratio or "16:9"),
        project_id,
        prompt_override if isinstance(prompt_override, str) else None,
        str(project.background_image_path) if project.background_image_path else None,
        str(project.style_reference_image_path) if project.style_reference_image_path else None,
        str(project.style_reference_notes) if project.style_reference_notes else None,
    )
    while len(assets) <= scene_index:
        assets.append({})
    assets[scene_index] = asset
    flags = json.loads(project.generation_flags or "{}")
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
    result = generator.generate_storyboard_data(
        str(project.theme),
        int(project.storyboard_count or 6),
        opening_hook_mode,
        visual_style_key,
        target_duration,
    )
    project.title = str(result.get("title") or project.title)
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
        project.generation_flags = json.dumps({**old_flags, **payload.get("generation_flags")}, ensure_ascii=False)
    project.storyboard_json = json.dumps(storyboards, ensure_ascii=False)
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
        allowed, reason = current_user.can_use_module('explainer', db)
        if not allowed:
            raise HTTPException(status_code=403, detail=reason or '系统繁忙，请稍后再试')
    try:
        generation_flags = json.loads(project.generation_flags or "{}")
    except Exception:
        generation_flags = {}
    generator = _build_explainer_generator()
    synced_storyboards, assets, flags = generator.generate_images(
        str(project.theme),
        storyboards,
        str(project.aspect_ratio or "16:9"),
        project_id,
        None,
        str(project.background_image_path) if project.background_image_path else None,
        str(project.style_reference_image_path) if project.style_reference_image_path else None,
        str(project.style_reference_notes) if project.style_reference_notes else None,
        generation_flags,
    )
    project.storyboard_json = json.dumps(synced_storyboards, ensure_ascii=False)
    project.image_assets_json = json.dumps(assets, ensure_ascii=False)
    project.generation_flags = json.dumps(flags, ensure_ascii=False)
    if not getattr(project, 'quota_consumed', False):
        current_user.increment_module_usage('explainer')
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
        generation_flags = json.loads(project.generation_flags or "{}")
    except Exception:
        generation_flags = {}
    generator = _build_explainer_generator()
    updated_scene, asset, used_fallback = generator.regenerate_single_image(
        str(project.theme),
        storyboards,
        scene_index,
        str(project.aspect_ratio or "16:9"),
        project_id,
        payload.get("prompt") if isinstance(payload.get("prompt"), str) else None,
        str(project.background_image_path) if project.background_image_path else None,
        str(project.style_reference_image_path) if project.style_reference_image_path else None,
        str(project.style_reference_notes) if project.style_reference_notes else None,
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

    if project.module_type not in {"stickman", "explainer"}:
        raise HTTPException(status_code=400, detail="Only stickman or explainer projects support background image")

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

    if project.background_image_path and os.path.exists(project.background_image_path):
        try:
            os.remove(project.background_image_path)
        except OSError:
            pass

    project.background_image_path = str(image_path)
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
        video_title=project.theme
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
