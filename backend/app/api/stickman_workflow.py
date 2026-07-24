from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.ai_video import _job_response, service
from app.api.auth import get_current_user
from app.database import get_db
from app.models.ai_video import AiVideoJob
from app.models.user import User
from app.schemas.ai_video import AiVideoJobCreated, AiVideoJobResponse
from app.services.stickman_workflow_assets import public_material_libraries, resolve_material_library
from app.services.stickman_workflow_limits import validate_image_mode, validate_script_duration_request


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


def _numeric_job_id(job_id: str) -> int:
    try:
        return int(str(job_id).replace("job_", ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid job id") from exc


def _max_video_seconds(user: User) -> int:
    return 180 if user.is_admin else 60


@router.get("/config")
def get_stickman_workflow_config(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return {
        "materialLibraries": public_material_libraries(db),
        "voices": [
            {"label": "曼波参考音色", "value": "dayun_manbo", "provider": "dayun_tools"},
            {"label": "中文女", "value": "中文女", "provider": "dashscope_cosyvoice"},
            {"label": "中文男", "value": "中文男", "provider": "dashscope_cosyvoice"},
        ],
        "defaults": {
            "voiceId": "dayun_manbo",
            "materialLibrary": "sc1_outputs",
            "imageMode": "material_only",
            "scriptMode": "ai",
        },
        "capabilities": {
            "canUseAiImages": bool(current_user.is_admin),
            "canUploadBackground": True,
            "maxVideoSeconds": _max_video_seconds(current_user),
        },
    }


@router.post("/jobs", response_model=AiVideoJobCreated)
def create_stickman_job(
    payload: StickmanWorkflowJobCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    title = payload.title.strip()
    custom_script = str(payload.customScript or "").strip()
    max_seconds = _max_video_seconds(current_user)
    try:
        resolved_seconds = validate_script_duration_request(custom_script, payload.targetSeconds, max_seconds)
        image_mode = validate_image_mode(payload.imageMode, bool(current_user.is_admin))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    voice_id = payload.voiceId.strip() or "dayun_manbo"
    voice_provider = "dayun_manbo" if voice_id in {"dayun_manbo", "manbo"} else "dashscope_cosyvoice"
    material_library = resolve_material_library(db, payload.materialLibrary)
    if not material_library:
        raise HTTPException(status_code=400, detail="素材库不可用")

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
        "useMaterialLibrary": image_mode == "material_only",
        "imageMode": image_mode,
        "backgroundMode": payload.backgroundMode,
        "backgroundTemplate": payload.backgroundTemplate,
        "uploadedBackgroundUrl": payload.uploadedBackgroundUrl,
        "materialImagesPerScene": 1,
    }
    if payload.sceneCount is not None:
        job_payload["sceneCount"] = payload.sceneCount
    job = service.create_generation_job(db, current_user.id, job_payload)
    return AiVideoJobCreated(jobId=f"job_{job.id}", projectId=job.project_id, status=job.status)


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
