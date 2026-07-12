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


router = APIRouter(prefix="/stickman-workflow", tags=["stickman-workflow"])


class StickmanWorkflowJobCreate(BaseModel):
    topic: str = Field(..., min_length=2, max_length=120)
    title: Optional[str] = None
    sceneCount: int = Field(default=5, ge=3, le=8)
    voiceId: str = "中文女"
    tone: str = "sharp"
    pace: str = "medium"
    targetPlatform: str = "douyin"


def _numeric_job_id(job_id: str) -> int:
    try:
        return int(str(job_id).replace("job_", ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid job id") from exc


@router.post("/jobs", response_model=AiVideoJobCreated)
def create_stickman_job(
    payload: StickmanWorkflowJobCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    topic = payload.topic.strip()
    title = (payload.title or topic).strip()
    job_payload = {
        "title": title,
        "prompt": topic,
        "requirements": topic,
        "creativeBrief": topic,
        "script": "",
        "videoType": "knowledge_ip_stickman",
        "contentType": "knowledge_ip_stickman",
        "style": "sc1_stickman",
        "visualStyle": "sc1_stickman",
        "aspectRatio": "16:9",
        "voiceProvider": "cosyvoice",
        "voiceId": payload.voiceId,
        "subtitleMode": "keywords",
        "targetPlatform": payload.targetPlatform,
        "tone": payload.tone,
        "pace": payload.pace,
        "sceneCount": payload.sceneCount,
        "goal": "standalone_sc1_stickman_workflow",
        "customPrompt": "Use SC1 standalone stickman workflow, two material-library scene images per scene, no overlap, subtitles synced to voice.",
        "workflowSource": "standalone_stickman_workflow",
        "useMaterialLibrary": True,
        "materialImagesPerScene": 2,
    }
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

