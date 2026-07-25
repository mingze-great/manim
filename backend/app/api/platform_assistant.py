from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.models.user import User
from app.services.platform_assistant import assistant_service


router = APIRouter(prefix="/platform-assistant", tags=["platform-assistant"])


class PlatformAssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    pagePath: str = ""
    module: str = ""


class PlatformAssistantAction(BaseModel):
    label: str
    route: str


class PlatformAssistantSource(BaseModel):
    title: str
    source: str


class PlatformAssistantChatResponse(BaseModel):
    answer: str
    suggestedActions: list[PlatformAssistantAction] = []
    sources: list[PlatformAssistantSource] = []


@router.post("/chat", response_model=PlatformAssistantChatResponse)
async def chat_platform_assistant(
    payload: PlatformAssistantChatRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return await assistant_service.answer(
        payload.message.strip(),
        page_path=payload.pagePath.strip(),
        module=payload.module.strip(),
    )
