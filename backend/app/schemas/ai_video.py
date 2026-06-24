from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AiVideoJobCreate(BaseModel):
    script: str = Field(..., min_length=2)
    title: Optional[str] = None
    videoType: str = "knowledge_visualization"
    style: str = "futuristic"
    aspectRatio: str = "16:9"
    voiceProvider: str = "cosyvoice"
    voiceId: str = "中文女"
    subtitleMode: str = "keywords"
    brandKitId: Optional[str] = None
    targetPlatform: str = "douyin"


class AiVideoJobCreated(BaseModel):
    jobId: str
    projectId: int
    status: str


class AiVideoJobResponse(BaseModel):
    jobId: str
    id: int
    projectId: int
    status: str
    progress: int
    stage: str
    message: str
    outputUrl: Optional[str]
    coverUrl: Optional[str]
    errorMessage: Optional[str]
    createdAt: datetime
    updatedAt: datetime
    completedAt: Optional[datetime]


class AiVideoProjectResponse(BaseModel):
    id: int
    title: str
    videoType: str
    aspectRatio: str
    status: str
    coverUrl: Optional[str]
    outputUrl: Optional[str]
    currentVersionId: Optional[int]
    createdAt: datetime
    updatedAt: datetime
    projectJson: Optional[dict[str, Any]] = None


class AiVideoEditRequest(BaseModel):
    message: str = Field(..., min_length=2)
    mode: str = "plan_then_apply"


class AiVideoEditPlanResponse(BaseModel):
    editPlan: list[str]
    canApply: bool = True


class AiVideoApplyEditRequest(BaseModel):
    editPlan: list[str] = Field(default_factory=list)
    message: Optional[str] = None


class AiVideoBrandKitCreate(BaseModel):
    name: str
    colors: list[str] = Field(default_factory=lambda: ["#0f766e", "#2563eb", "#f59e0b"])
    voiceConfig: dict[str, Any] = Field(default_factory=dict)
    subtitleStyle: dict[str, Any] = Field(default_factory=dict)


class AiVideoBrandKitResponse(BaseModel):
    id: int
    name: str
    logoUrl: Optional[str]
    colors: list[str]
    voiceConfig: dict[str, Any]
    subtitleStyle: dict[str, Any]
    createdAt: datetime
    updatedAt: datetime
