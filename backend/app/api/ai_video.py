import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.ai_video import AiVideoBrandKit, AiVideoJob, AiVideoProject, AiVideoVersion
from app.models.user import User
from app.schemas.ai_video import (
    AiVideoApplyEditRequest,
    AiVideoBrandKitCreate,
    AiVideoBrandKitResponse,
    AiVideoEditPlanResponse,
    AiVideoEditRequest,
    AiVideoJobCreate,
    AiVideoJobCreated,
    AiVideoJobResponse,
    AiVideoProjectResponse,
)
from app.services.ai_video import AiVideoService, STAGE_MESSAGES

router = APIRouter(prefix="/ai-video", tags=["ai-video"])
service = AiVideoService()


def _job_response(job: AiVideoJob) -> AiVideoJobResponse:
    return AiVideoJobResponse(
        jobId=f"job_{job.id}",
        id=job.id,
        projectId=job.project_id,
        status=job.status,
        progress=job.progress,
        stage=job.stage,
        message=STAGE_MESSAGES.get(job.stage, job.stage),
        outputUrl=job.output_url,
        coverUrl=job.cover_url,
        errorMessage=job.error_message,
        createdAt=job.created_at,
        updatedAt=job.updated_at,
        completedAt=job.completed_at,
    )


def _project_response(db: Session, project: AiVideoProject) -> AiVideoProjectResponse:
    version = None
    if project.current_version_id:
        version = db.query(AiVideoVersion).filter(AiVideoVersion.id == project.current_version_id).first()
    if not version:
        version = (
            db.query(AiVideoVersion)
            .filter(AiVideoVersion.project_id == project.id)
            .order_by(AiVideoVersion.version_no.desc())
            .first()
        )
    return AiVideoProjectResponse(
        id=project.id,
        title=project.title,
        videoType=project.video_type,
        aspectRatio=project.aspect_ratio,
        status=project.status,
        coverUrl=project.cover_url or (version.cover_url if version else None),
        outputUrl=version.output_url if version else None,
        currentVersionId=project.current_version_id,
        createdAt=project.created_at,
        updatedAt=project.updated_at,
        projectJson=service.get_project_json(version),
    )


def _require_project(db: Session, project_id: int, user: User) -> AiVideoProject:
    query = db.query(AiVideoProject).filter(AiVideoProject.id == project_id)
    if not user.is_admin:
        query = query.filter(AiVideoProject.user_id == user.id)
    project = query.first()
    if not project:
        raise HTTPException(status_code=404, detail="AI video project not found")
    return project


@router.get("/overview")
def overview(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    query = db.query(AiVideoProject)
    job_query = db.query(AiVideoJob)
    if not current_user.is_admin:
        query = query.filter(AiVideoProject.user_id == current_user.id)
        job_query = job_query.filter(AiVideoJob.user_id == current_user.id)
    projects = query.order_by(AiVideoProject.updated_at.desc()).limit(8).all()
    jobs = job_query.order_by(AiVideoJob.created_at.desc()).limit(8).all()
    return {
        "stats": {
            "totalProjects": query.count(),
            "generating": query.filter(AiVideoProject.status.in_(["pending", "rendering", "scripting"])).count(),
            "completed": query.filter(AiVideoProject.status == "completed").count(),
            "monthlyExports": db.query(AiVideoVersion).count(),
        },
        "recentProjects": [_project_response(db, project).model_dump(mode="json") for project in projects],
        "queue": [_job_response(job).model_dump(mode="json") for job in jobs],
    }


@router.post("/jobs", response_model=AiVideoJobCreated)
def create_job(
    payload: AiVideoJobCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    job = service.create_generation_job(db, current_user.id, payload.model_dump())
    return AiVideoJobCreated(jobId=f"job_{job.id}", projectId=job.project_id, status=job.status)


@router.get("/jobs/{job_id}", response_model=AiVideoJobResponse)
def get_job(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    numeric_id = int(job_id.replace("job_", ""))
    query = db.query(AiVideoJob).filter(AiVideoJob.id == numeric_id)
    if not current_user.is_admin:
        query = query.filter(AiVideoJob.user_id == current_user.id)
    job = query.first()
    if not job:
        raise HTTPException(status_code=404, detail="AI video job not found")
    return _job_response(job)


@router.get("/projects", response_model=list[AiVideoProjectResponse])
def list_projects(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    query = db.query(AiVideoProject)
    if not current_user.is_admin:
        query = query.filter(AiVideoProject.user_id == current_user.id)
    return [_project_response(db, project) for project in query.order_by(AiVideoProject.updated_at.desc()).all()]


@router.get("/projects/{project_id}", response_model=AiVideoProjectResponse)
def get_project(
    project_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return _project_response(db, _require_project(db, project_id, current_user))


@router.post("/projects/{project_id}/edit", response_model=AiVideoEditPlanResponse)
def plan_edit(
    project_id: int,
    payload: AiVideoEditRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _require_project(db, project_id, current_user)
    return AiVideoEditPlanResponse(editPlan=service.build_edit_plan(payload.message), canApply=True)


@router.post("/projects/{project_id}/apply-edit")
def apply_edit(
    project_id: int,
    payload: AiVideoApplyEditRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    project = _require_project(db, project_id, current_user)
    version = service.apply_edit_plan(db, project, current_user.id, payload.editPlan, payload.message)
    return {"versionId": version.id, "versionNo": version.version_no, "project": _project_response(db, project)}


@router.get("/projects/{project_id}/versions")
def list_versions(
    project_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _require_project(db, project_id, current_user)
    versions = (
        db.query(AiVideoVersion)
        .filter(AiVideoVersion.project_id == project_id)
        .order_by(AiVideoVersion.version_no.desc())
        .all()
    )
    return [
        {
            "id": version.id,
            "versionNo": version.version_no,
            "outputUrl": version.output_url,
            "coverUrl": version.cover_url,
            "changeSummary": version.change_summary,
            "createdAt": version.created_at,
        }
        for version in versions
    ]


@router.get("/templates")
def templates():
    return [
        {"key": "knowledge_visualization", "name": "知识可视化", "duration": "30-60s", "platforms": ["抖音", "视频号"]},
        {"key": "product_promo", "name": "商品推广", "duration": "20-45s", "platforms": ["小红书", "抖音"]},
        {"key": "math_tutorial", "name": "数学题教学", "duration": "45-90s", "platforms": ["B站", "课堂"]},
        {"key": "data_report", "name": "数据报告", "duration": "45-120s", "platforms": ["企业汇报"]},
        {"key": "saas_demo", "name": "SaaS 演示", "duration": "30-90s", "platforms": ["官网", "销售"]},
    ]


@router.get("/brand-kits", response_model=list[AiVideoBrandKitResponse])
def list_brand_kits(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    kits = db.query(AiVideoBrandKit).filter(AiVideoBrandKit.user_id == current_user.id).all()
    return [_brand_kit_response(kit) for kit in kits]


@router.post("/brand-kits", response_model=AiVideoBrandKitResponse)
def create_brand_kit(
    payload: AiVideoBrandKitCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    kit = AiVideoBrandKit(
        user_id=current_user.id,
        name=payload.name,
        colors=json.dumps(payload.colors, ensure_ascii=False),
        voice_config=json.dumps(payload.voiceConfig, ensure_ascii=False),
        subtitle_style=json.dumps(payload.subtitleStyle, ensure_ascii=False),
    )
    db.add(kit)
    db.commit()
    db.refresh(kit)
    return _brand_kit_response(kit)


@router.get("/files/{job_id}/{file_path:path}")
def get_file(job_id: int, file_path: str):
    root = (Path("storage") / "ai-video" / "tasks" / f"job_{job_id}").resolve()
    target = (root / file_path).resolve()
    if not str(target).startswith(str(root)) or not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target)


def _brand_kit_response(kit: AiVideoBrandKit) -> AiVideoBrandKitResponse:
    def parse_json(raw: str | None, fallback):
        if not raw:
            return fallback
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return fallback

    return AiVideoBrandKitResponse(
        id=kit.id,
        name=kit.name,
        logoUrl=kit.logo_url,
        colors=parse_json(kit.colors, []),
        voiceConfig=parse_json(kit.voice_config, {}),
        subtitleStyle=parse_json(kit.subtitle_style, {}),
        createdAt=kit.created_at,
        updatedAt=kit.updated_at,
    )
