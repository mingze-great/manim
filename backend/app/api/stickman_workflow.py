import json
import re
import uuid
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.ai_video import _job_response, service
from app.api.auth import get_current_user
from app.database import get_db
from app.models.ai_video import AiVideoJob
from app.models.user import User
from app.schemas.ai_video import AiVideoJobCreated, AiVideoJobResponse
from app.services.partner_program import stickman_entitlement_from_user
from app.services.stickman_workflow_assets import find_material_library_asset, public_material_libraries, resolve_material_library
from app.services.stickman_workflow_limits import (
    consume_stickman_quota,
    estimate_script_duration_seconds,
    validate_image_mode,
    validate_script_duration_request,
    validate_stickman_quota,
)


router = APIRouter(prefix="/stickman-workflow", tags=["stickman-workflow"])


class StickmanWorkflowJobCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=120)
    topic: Optional[str] = None
    sceneCount: Optional[int] = Field(default=None, ge=3, le=8)
    voiceId: str = "dayun_manbo"
    materialLibrary: str = "sc1_outputs"
    tone: str = "sharp"
    pace: str = "medium"
    targetPlatform: str = "douyin"
    scriptMode: str = "ai"
    customScript: Optional[str] = None
    targetSeconds: Optional[int] = Field(default=None, ge=1, le=300)
    backgroundMode: str = "default"
    backgroundTemplate: Optional[str] = None
    uploadedBackgroundUrl: Optional[str] = None
    imageMode: str = "material_only"


class StickmanWorkflowDurationEstimateRequest(BaseModel):
    script: str = Field(..., min_length=1)


def _numeric_job_id(job_id: str) -> int:
    try:
        return int(str(job_id).replace("job_", ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid job id") from exc


def _max_video_seconds(user: User) -> int:
    if user.is_admin:
        return 300
    return stickman_entitlement_from_user(user)["max_video_seconds"]


def _stickman_entitlement(user: User) -> dict:
    if user.is_admin:
        return {
            "material_mode": "material_only",
            "visible_image_modes": ["material_only", "ai_image"],
            "can_choose_image_mode": True,
            "can_use_ai_images": True,
            "max_video_seconds": 300,
            "allowed_libraries": [],
        }
    return stickman_entitlement_from_user(user)


def _visible_libraries_for_user(db: Session, user: User) -> list[dict]:
    return public_material_libraries(db)


def _scene_styles_for_user(db: Session, user: User) -> list[dict]:
    return [
        {
            "key": item.get("key"),
            "label": item.get("name") or item.get("key"),
            "name": item.get("name") or item.get("key"),
            "description": item.get("description") or "",
            "sampleImageUrl": item.get("image_url"),
            "image_url": item.get("image_url"),
        }
        for item in _visible_libraries_for_user(db, user)
    ]


def _ensure_material_library_allowed(material_library: dict, entitlement: dict) -> None:
    if not entitlement.get("enforce_allowed_libraries"):
        return
    allowed = {str(item).strip() for item in entitlement.get("allowed_libraries") or [] if str(item).strip()}
    if allowed and str(material_library.get("key") or "") not in allowed:
        raise HTTPException(status_code=400, detail="当前套餐不支持该素材库")


def _stickman_permission_for_user(user: User) -> dict:
    permissions = user.get_module_permissions()
    permission = dict(permissions.get("stickman_v2") or {})
    permission.setdefault("enabled", True)
    permission.setdefault("daily_limit", 2)
    permission.setdefault("period", "monthly")
    permission.setdefault("max_video_seconds", 60)
    return permission


def _resolve_allowed_image_mode(requested_mode: str, entitlement: dict) -> str:
    visible_modes = [str(item).strip() for item in entitlement.get("visible_image_modes") or [] if str(item).strip()]
    if not visible_modes:
        visible_modes = ["material_only"]
    requested = str(requested_mode or entitlement.get("material_mode") or visible_modes[0]).strip() or visible_modes[0]
    if requested == "hybrid":
        requested = "material_only" if "material_only" in visible_modes else visible_modes[0]
    if requested not in visible_modes:
        raise ValueError("当前账号不支持该图片模式")
    return validate_image_mode(requested, bool(entitlement.get("can_use_ai_images")))


def _ensure_stickman_account_allowed(user: User, permission: dict) -> None:
    if user.is_admin:
        return
    if not user.is_active:
        raise HTTPException(status_code=403, detail="当前账号已被禁用")
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="当前账号暂未审核通过")
    if user.is_expired() and not (permission.get("quota_mode") == "count_package" and permission.get("unlimited_time")):
        raise HTTPException(status_code=403, detail="当前账号已过期")


def _persist_stickman_permission(db: Session, user: User, permission: dict) -> None:
    if user.is_admin:
        return
    permissions = user.get_module_permissions()
    permissions["stickman_v2"] = permission
    user.set_module_permissions(permissions)
    record = user.get_module_permission_record(db, "stickman_v2")
    if record:
        record.enabled = bool(permission.get("enabled", True))
        record.quota_limit = int(permission.get("daily_limit") or permission.get("total_video_limit") or 0)
        record.quota_used = int(permission.get("used_today") or permission.get("used_total_videos") or 0)
        record.period = str(permission.get("period") or ("lifetime" if permission.get("quota_mode") == "count_package" else "monthly"))


def _background_templates() -> list[dict[str, str]]:
    return [
        {"key": "default", "name": "默认白纸", "description": "接近参考视频的简洁白底", "preview": "paper"},
        {"key": "warm_paper", "name": "暖色纸感", "description": "偏温暖的纸面背景", "preview": "warm"},
        {"key": "cool_grid", "name": "冷静网格", "description": "偏理性的浅色网格", "preview": "grid"},
        {"key": "soft_gradient", "name": "柔和渐变", "description": "轻微渐变的低干扰背景", "preview": "gradient"},
    ]


def _voice_options() -> list[dict[str, str]]:
    return [
        {"label": "曼波参考音色", "value": "dayun_manbo", "provider": "dayun_tools", "previewUrl": "/api/stickman-workflow/voices/dayun_manbo/preview"},
        {"label": "中文女", "value": "中文女", "provider": "dashscope_cosyvoice", "previewUrl": "/api/stickman-workflow/voices/dayun_manbo/preview"},
        {"label": "中文男", "value": "中文男", "provider": "dashscope_cosyvoice", "previewUrl": "/api/stickman-workflow/voices/dayun_manbo/preview"},
    ]


@router.get("/config")
def get_stickman_workflow_config(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    entitlement = _stickman_entitlement(current_user)
    scene_styles = _scene_styles_for_user(db, current_user)
    return {
        "materialLibraries": _visible_libraries_for_user(db, current_user),
        "sceneStyles": scene_styles,
        "backgroundTemplates": _background_templates(),
        "voices": _voice_options(),
        "defaults": {
            "voiceId": "dayun_manbo",
            "materialLibrary": "sc1_outputs",
            "sceneStyle": "sc1_outputs",
            "imageMode": entitlement.get("material_mode") or "material_only",
            "scriptMode": "ai",
        },
        "capabilities": {
            "canUseAiImages": bool(entitlement.get("can_use_ai_images")),
            "visibleImageModes": entitlement.get("visible_image_modes") or ["material_only"],
            "canChooseImageMode": bool(entitlement.get("can_choose_image_mode")),
            "canUploadBackground": True,
            "materialMode": entitlement.get("material_mode") or "material_only",
            "maxVideoSeconds": _max_video_seconds(current_user),
        },
    }


@router.get("/assets/material-libraries/{library_key}/{filename}")
def get_stickman_workflow_material_library_preview_asset(
    library_key: str,
    filename: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    visible_keys = {str(item.get("key") or "") for item in _visible_libraries_for_user(db, current_user)}
    if str(library_key or "") not in visible_keys:
        raise HTTPException(status_code=404, detail="素材库不可用")
    asset_path = find_material_library_asset(db, filename, library_key)
    if not asset_path or not asset_path.exists():
        raise HTTPException(status_code=404, detail="预览图不存在")
    return FileResponse(asset_path)


@router.get("/voices/{voice_id}/preview")
def preview_stickman_voice(
    voice_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    candidates = [
        Path(str(Path.cwd())) / "outputs" / "dayun_tools_manbo_tts_test.mp3",
        Path(str(Path.cwd())) / "storage" / "voice-references" / "dayun_tools_manbo_tts_test.mp3",
        Path(str(Path.cwd())) / "backend" / "storage" / "voice-references" / "dayun_tools_manbo_tts_test.mp3",
        Path(__file__).resolve().parents[2] / "outputs" / "dayun_tools_manbo_tts_test.mp3",
        Path(__file__).resolve().parents[2].parent / "outputs" / "dayun_tools_manbo_tts_test.mp3",
        Path(__file__).resolve().parents[2] / "storage" / "voice-references" / "dayun_tools_manbo_tts_test.mp3",
        Path(__file__).resolve().parents[2].parent / "backend" / "storage" / "voice-references" / "dayun_tools_manbo_tts_test.mp3",
        Path(__file__).resolve().parents[2] / "outputs" / "cosyvoice_zero_shot_sample.wav",
        Path(__file__).resolve().parents[2].parent / "outputs" / "cosyvoice_zero_shot_sample.wav",
        Path(__file__).resolve().parents[2] / "storage" / "voice-references" / "cosyvoice_zero_shot_sample.wav",
    ]
    for path in candidates:
        if path.exists() and path.is_file():
            media_type = "audio/mpeg" if path.suffix.lower() == ".mp3" else "audio/wav"
            return FileResponse(path, media_type=media_type, filename=path.name)
    raise HTTPException(status_code=404, detail="当前服务器未配置声音试听文件")


@router.post("/duration-estimate")
def estimate_stickman_script_duration(
    payload: StickmanWorkflowDurationEstimateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    estimated_seconds = estimate_script_duration_seconds(payload.script)
    max_video_seconds = _max_video_seconds(current_user)
    return {
        "estimatedSeconds": estimated_seconds,
        "maxVideoSeconds": max_video_seconds,
        "allowed": estimated_seconds <= max_video_seconds,
    }


@router.post("/backgrounds")
async def upload_stickman_background(
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=400, detail="仅支持 png、jpg、jpeg、webp 图片")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="背景图不能超过 8MB")
    safe_suffix = ".jpg" if suffix == ".jpeg" else suffix
    filename = f"stickman_bg_u{current_user.id}_{uuid.uuid4().hex[:12]}{safe_suffix}"
    if not re.fullmatch(r"[\w.-]+", filename):
        raise HTTPException(status_code=400, detail="文件名不安全")
    upload_dir = Path(__file__).resolve().parents[2] / "uploads" / "background_images"
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / filename).write_bytes(content)
    return {"url": f"/api/background-images/{filename}", "filename": filename}


@router.post("/jobs", response_model=AiVideoJobCreated)
def create_stickman_job(
    payload: StickmanWorkflowJobCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    title = payload.title.strip()
    custom_script = str(payload.customScript or "").strip()
    max_seconds = _max_video_seconds(current_user)
    entitlement = _stickman_entitlement(current_user)
    permission = _stickman_permission_for_user(current_user)
    try:
        resolved_seconds = validate_script_duration_request(custom_script, payload.targetSeconds, max_seconds)
        image_mode = _resolve_allowed_image_mode(payload.imageMode, entitlement)
        _ensure_stickman_account_allowed(current_user, permission)
        validate_stickman_quota(permission, resolved_seconds or payload.targetSeconds or 60)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    voice_id = payload.voiceId.strip() or "dayun_manbo"
    voice_provider = "dayun_manbo" if voice_id in {"dayun_manbo", "manbo"} else "dashscope_cosyvoice"
    material_library = resolve_material_library(db, payload.materialLibrary)
    if not material_library:
        raise HTTPException(status_code=400, detail="素材库不可用")
    _ensure_material_library_allowed(material_library, entitlement)

    script_source = "user" if custom_script else "generated"
    script_text = custom_script if custom_script else ""
    creative_brief = title if not custom_script else f"按用户文案生成火柴人成片，标题：{title}"
    custom_prompt = (
        f"Use SC1 standalone stickman workflow. Title: {title}. "
        "If scriptSource is user, do not rewrite the narration; split the user script into synchronized caption cues. "
        "If targetSeconds is provided, generate reference-style psychology copy that fits that duration. "
        "Each semantic segment uses one centered material-library scene image, no zooming or side-by-side layout, "
        "and Chinese subtitles must track the full voice line sentence by sentence. Use the dayun_manbo reference tone by default unless the user chooses another voice. "
        "Summary labels must be short 2-4 character emotional keywords, revealed cumulatively around the image and cleared only when the segment ends."
    )
    job_payload = {
        "title": title,
        "prompt": script_text or title,
        "requirements": script_text or title,
        "creativeBrief": creative_brief,
        "script": script_text,
        "scriptSource": script_source,
        "targetSeconds": resolved_seconds or None,
        "videoType": "knowledge_ip_stickman",
        "contentType": "knowledge_ip_stickman",
        "style": "sc1_stickman",
        "visualStyle": "sc1_stickman",
        "aspectRatio": "16:9",
        "voiceProvider": voice_provider,
        "voiceId": voice_id,
        "materialLibrary": material_library.get("key") or "sc1_outputs",
        "materialLibraryPath": material_library.get("base_path") or "",
        "materialLibraryManifest": material_library.get("material_json_path") or "",
        "materialLibraryName": material_library.get("name") or "",
        "subtitleMode": "keywords",
        "targetPlatform": payload.targetPlatform,
        "tone": payload.tone,
        "pace": payload.pace,
        "goal": "standalone_sc1_stickman_workflow",
        "customPrompt": custom_prompt,
        "workflowSource": "standalone_stickman_workflow",
        "useMaterialLibrary": image_mode in {"material_only", "hybrid"},
        "imageMode": image_mode,
        "backgroundMode": payload.backgroundMode,
        "backgroundTemplate": payload.backgroundTemplate,
        "uploadedBackgroundUrl": payload.uploadedBackgroundUrl,
        "materialImagesPerScene": 1,
    }
    if payload.sceneCount is not None:
        job_payload["sceneCount"] = payload.sceneCount
    job = service.create_generation_job(db, current_user.id, job_payload)
    consume_stickman_quota(permission, resolved_seconds or payload.targetSeconds or 60)
    _persist_stickman_permission(db, current_user, permission)
    db.commit()
    return AiVideoJobCreated(jobId=f"job_{job.id}", projectId=job.project_id, status=job.status)


@router.get("/jobs", response_model=list[AiVideoJobResponse])
def list_stickman_jobs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 30,
):
    limit = max(1, min(int(limit or 30), 100))
    query = db.query(AiVideoJob)
    if not current_user.is_admin:
        query = query.filter(AiVideoJob.user_id == current_user.id)
    jobs = query.order_by(AiVideoJob.created_at.desc()).limit(200).all()
    workflow_jobs = []
    for job in jobs:
        try:
            input_payload = json.loads(job.input_payload or "{}")
        except Exception:
            input_payload = {}
        if input_payload.get("workflowSource") == "standalone_stickman_workflow":
            workflow_jobs.append(service.reconcile_stale_job(db, job))
        if len(workflow_jobs) >= limit:
            break
    return [_job_response(job) for job in workflow_jobs]


@router.get("/jobs/{job_id}", response_model=AiVideoJobResponse)
def get_stickman_job(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    numeric_id = _numeric_job_id(job_id)
    query = db.query(AiVideoJob).filter(AiVideoJob.id == numeric_id)
    if not current_user.is_admin:
        query = query.filter(AiVideoJob.user_id == current_user.id)
    job = query.first()
    if not job:
        raise HTTPException(status_code=404, detail="Stickman workflow job not found")
    job = service.reconcile_stale_job(db, job)
    return _job_response(job)
