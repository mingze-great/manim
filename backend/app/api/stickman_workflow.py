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


def _numeric_job_id(job_id: str) -> int:
    try:
        return int(str(job_id).replace("job_", ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid job id") from exc


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
        },
        "capabilities": {
            "canUseAiImages": bool(current_user.is_admin),
            "canUploadBackground": True,
            "maxVideoSeconds": 60 if not current_user.is_admin else 180,
        },
    }


@router.post("/jobs", response_model=AiVideoJobCreated)
def create_stickman_job(
    payload: StickmanWorkflowJobCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    title = payload.title.strip()
    voice_id = payload.voiceId.strip() or "dayun_manbo"
    voice_provider = "dayun_manbo" if voice_id in {"dayun_manbo", "manbo"} else "dashscope_cosyvoice"
    material_library = resolve_material_library(db, payload.materialLibrary)
    if not material_library:
        raise HTTPException(status_code=400, detail="素材库不可用")
    job_payload = {
        "title": title,
        "prompt": title,
        "requirements": title,
        "creativeBrief": title,
        "script": "",
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
        "customPrompt": (
            f"Use SC1 standalone stickman workflow. The only user-facing input is the title: {title}. "
            "Generate reference-style copy from this title first, then split scenes semantically with the current caption-cue method. "
            "Each semantic segment uses one centered material-library scene image, no zooming or side-by-side layout, "
            "and Chinese subtitles must track the full voice line sentence by sentence. Use the dayun_manbo reference tone by default unless the user chooses another voice. "
            "Summary labels must be short 2-4 character emotional keywords, "
            "revealed cumulatively around the image and cleared only when the segment ends."
        ),
        "workflowSource": "standalone_stickman_workflow",
        "useMaterialLibrary": True,
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
