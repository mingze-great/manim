from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class ProjectBase(BaseModel):
    title: str
    theme: str


class ProjectCreate(ProjectBase):
    category: Optional[str] = None
    module_type: str = "manim"
    storyboard_count: int = 3
    aspect_ratio: str = "16:9"
    generation_mode: str = "one_click"
    voice_source: str = "ai"
    tts_provider: str = "dashscope_cosyvoice"
    tts_voice: str = "longshuo_v3"
    tts_rate: str = "+0%"


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    theme: Optional[str] = None
    category: Optional[str] = None
    module_type: Optional[str] = None
    storyboard_count: Optional[int] = None
    aspect_ratio: Optional[str] = None
    generation_mode: Optional[str] = None
    voice_source: Optional[str] = None
    voice_file_path: Optional[str] = None
    voice_duration: Optional[int] = None
    tts_provider: Optional[str] = None
    tts_voice: Optional[str] = None
    tts_rate: Optional[str] = None
    style_reference_image_path: Optional[str] = None
    style_reference_notes: Optional[str] = None
    style_reference_profile: Optional[str] = None
    preview_image_asset_json: Optional[str] = None
    preview_regen_count: Optional[int] = None
    storyboard_json: Optional[str] = None
    image_assets_json: Optional[str] = None
    generation_flags: Optional[str] = None
    final_script: Optional[str] = None
    manim_code: Optional[str] = None
    custom_code: Optional[str] = None
    status: Optional[str] = None
    template_id: Optional[int] = None
    video_url: Optional[str] = None
    error_message: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: int
    user_id: int
    category: Optional[str] = None
    module_type: str = "manim"
    storyboard_count: int = 3
    aspect_ratio: str = "16:9"
    generation_mode: str = "one_click"
    voice_source: str = "ai"
    voice_file_path: Optional[str]
    voice_duration: Optional[int]
    tts_provider: str = "dashscope_cosyvoice"
    tts_voice: str = "longshuo_v3"
    tts_rate: str = "+0%"
    style_reference_image_path: Optional[str]
    style_reference_notes: Optional[str]
    style_reference_profile: Optional[str]
    preview_image_asset_json: Optional[str]
    preview_regen_count: int = 0
    storyboard_json: Optional[str]
    image_assets_json: Optional[str]
    generation_flags: Optional[str]
    final_script: Optional[str]
    manim_code: Optional[str]
    custom_code: Optional[str]
    status: str
    template_id: Optional[int]
    video_url: Optional[str]
    error_message: Optional[str]
    render_fail_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    content: str


class ConversationUpdate(BaseModel):
    content: str


class CustomScriptRequest(BaseModel):
    script: str
    auto_format: bool = False  # 是否自动转换为标准格式


class ConversationResponse(BaseModel):
    id: int
    project_id: int
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True
