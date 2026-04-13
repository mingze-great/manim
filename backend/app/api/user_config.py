from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.api.auth import get_current_user
from app.utils.encryption import encrypt_api_key, decrypt_api_key, is_valid_api_key_format

router = APIRouter(prefix="/user", tags=["user"])


class ApiConfigRequest(BaseModel):
    api_type: str  # llm / image / tts
    api_key: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    use_custom: Optional[bool] = None


class ApiConfigResponse(BaseModel):
    llm_use_custom: bool
    llm_provider: Optional[str]
    llm_model: Optional[str]
    llm_has_key: bool
    image_use_custom: bool
    image_provider: Optional[str]
    image_has_key: bool
    tts_use_custom: bool
    tts_provider: Optional[str]
    tts_has_key: bool


@router.get("/api-config", response_model=ApiConfigResponse)
async def get_api_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return ApiConfigResponse(
        llm_use_custom=bool(user.llm_use_custom),
        llm_provider=user.llm_api_key_provider,
        llm_model=user.llm_api_key_model,
        llm_has_key=bool(user.llm_api_key_encrypted),
        image_use_custom=bool(user.image_use_custom),
        image_provider=user.image_api_key_provider,
        image_has_key=bool(user.image_api_key_encrypted),
        tts_use_custom=bool(user.tts_use_custom),
        tts_provider=user.tts_api_key_provider,
        tts_has_key=bool(user.tts_api_key_encrypted),
    )


@router.put("/api-config")
async def update_api_config(
    config: ApiConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if config.api_type not in ["llm", "image", "tts"]:
        raise HTTPException(status_code=400, detail="无效的 API 类型")
    
    if config.api_key and not is_valid_api_key_format(config.api_key):
        raise HTTPException(status_code=400, detail="API key 格式无效")
    
    if config.api_type == "llm":
        if config.api_key:
            user.llm_api_key_encrypted = encrypt_api_key(config.api_key)
        if config.provider:
            user.llm_api_key_provider = config.provider
        if config.model:
            user.llm_api_key_model = config.model
        if config.use_custom is not None:
            user.llm_use_custom = config.use_custom
    
    elif config.api_type == "image":
        if config.api_key:
            user.image_api_key_encrypted = encrypt_api_key(config.api_key)
        if config.provider:
            user.image_api_key_provider = config.provider
        if config.use_custom is not None:
            user.image_use_custom = config.use_custom
    
    elif config.api_type == "tts":
        if config.api_key:
            user.tts_api_key_encrypted = encrypt_api_key(config.api_key)
        if config.provider:
            user.tts_api_key_provider = config.provider
        if config.use_custom is not None:
            user.tts_use_custom = config.use_custom
    
    db.commit()
    return {"message": "API 配置已更新"}


@router.post("/api-config/validate")
async def validate_api_key(
    config: ApiConfigRequest,
    current_user: User = Depends(get_current_user),
):
    """验证 API key 是否有效（简单格式检查）"""
    if config.api_type not in ["llm", "image", "tts"]:
        raise HTTPException(status_code=400, detail="无效的 API 类型")
    
    if not config.api_key:
        raise HTTPException(status_code=400, detail="请提供 API key")
    
    valid = is_valid_api_key_format(config.api_key)
    
    return {
        "valid": valid,
        "message": valid and "格式有效" or "格式无效，请检查 API key"
    }