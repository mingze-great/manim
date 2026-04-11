from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        extra="ignore"
    )
    
    DATABASE_URL: str = "sqlite:///./manim_platform.db"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Environment
    ENVIRONMENT: str = "development"  # development/production
    DEBUG: bool = False
    
    # Admin
    ADMIN_EMAIL: str = ""
    
    # LLM Provider Configuration (auto/deepseek/gemini/openai/dashscope)
    LLM_PROVIDER: str = "auto"
    
    # 阿里云百炼 API（主模型）
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    # 代码生成模型配置
    DASHSCOPE_CODE_MODEL: str = "deepseek-v3.2"  # 主代码模型（推荐首次使用）
    DASHSCOPE_CODE_FALLBACK_MODEL: str = "qwen3-coder-next"  # 代码降级模型
    
    # 文本对话模型配置
    DASHSCOPE_CHAT_MODEL: str = "deepseek-v3.1"  # 主对话模型
    DASHSCOPE_CHAT_FALLBACK_MODEL_1: str = "qwen3.5-plus"  # 第一降级
    DASHSCOPE_CHAT_FALLBACK_MODEL_2: str = "deepseek-v3.2"  # 第二降级
    
    # 用户可选择的模型列表
    DASHSCOPE_AVAILABLE_MODELS: str = "qwen3-coder-next,deepseek-v3.1,deepseek-v3.2,qwen3.5-plus"
    
    # DeepSeek (已废弃，仅保留兼容)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://openrouter.fans/v1"
    DEEPSEEK_MODEL: str = "deepseek/deepseek-v3.2"
    
    # DeepSeek Fallback (已废弃)
    DEEPSEEK_FALLBACK_API_KEY: str = ""
    DEEPSEEK_FALLBACK_BASE_URL: str = "https://ai.1seey.com/v1"
    DEEPSEEK_FALLBACK_MODEL: str = "qwen3.5-plus"
    
    # Gemini (Priority 3)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    
    # OpenAI (Priority 4)
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"
    
    # GLM (智谱AI)
    GLM_API_KEY: str = ""
    GLM_BASE_URL: str = "https://code.coolyeah.net"
    GLM_MODEL: str = "glm-5"
    
    # Legacy support
    LLM_MODEL: str = ""
    
    REDIS_URL: str = "redis://localhost:6379/0"
    
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_BUCKET_NAME: str = "manim-videos"
    OSS_ENDPOINT: str = "oss-cn-hangzhou.aliyuncs.com"
    
    # 腾讯云 COS 配置
    COS_SECRET_ID: str = ""
    COS_SECRET_KEY: str = ""
    COS_BUCKET: str = "manim-1308464924"
    COS_REGION: str = "ap-beijing"
    COS_DOMAIN: str = "https://manim-1308464924.cos.ap-beijing.myqcloud.com"
    COS_ENABLE: bool = True  # 是否启用 COS 存储
    
    # WeChat Pay Configuration
    WX_MCH_ID: str = ""
    WX_APP_ID: str = ""
    WX_API_KEY: str = ""
    WX_NOTIFY_URL: str = "https://your-domain.com/api/payment/wx/notify"
    
    CORS_ORIGINS: str = "*"
    VITE_API_BASE_URL: str = ""
    
    INTERNAL_API_KEY: str = "internal-api-key-change-in-production"
    OLD_SERVER_URL: str = "http://106.52.166.109:8000"
    NEW_SERVER_URL: str = "http://152.136.218.74:8000"

    STICKMAN_ENABLED: bool = True
    STICKMAN_LLM_API_KEY: str = ""
    STICKMAN_LLM_BASE_URL: str = "https://openrouter.fans/v1"
    STICKMAN_LLM_MODEL: str = "deepseek/deepseek-v3.2"
    STICKMAN_IMAGE_API_KEY: str = ""
    STICKMAN_IMAGE_BASE_URL: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    STICKMAN_IMAGE_MODEL: str = "qwen-image-2.0-pro"
    STICKMAN_IMAGE_MODELS: str = "qwen-image-2.0-pro,qwen-image-2.0-pro-2026-03-03,qwen-image-2.0,qwen-image-2.0-2026-03-03"
    STICKMAN_IMAGE_SIZE: str = "1024*1024"
    STICKMAN_IMAGE_NEGATIVE_PROMPT: str = "低分辨率，低画质，肢体畸形，手指畸形，画面过饱和，蜡像感，人脸无细节，过度光滑，画面具有AI感，构图混乱，文字模糊，扭曲"
    STICKMAN_TTS_API_KEY: str = ""
    STICKMAN_TTS_BASE_URL: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    STICKMAN_TTS_MODEL: str = "cosyvoice-v3-flash"
    STICKMAN_TTS_PROVIDER: str = "dashscope_cosyvoice"
    STICKMAN_TTS_VOICE: str = "longshuo_v3"
    STICKMAN_TTS_VOICE_LIBRARY: str = "[{\"label\":\"稳重男声\",\"value\":\"longshuo_v3\",\"provider\":\"dashscope_cosyvoice\",\"gender\":\"male\",\"style\":\"steady\"},{\"label\":\"阳光男声\",\"value\":\"longanyang\",\"provider\":\"dashscope_cosyvoice\",\"gender\":\"male\",\"style\":\"bright\"},{\"label\":\"温暖男声\",\"value\":\"longsanshu\",\"provider\":\"dashscope_cosyvoice\",\"gender\":\"male\",\"style\":\"warm\"},{\"label\":\"清爽男声\",\"value\":\"longanlang\",\"provider\":\"dashscope_cosyvoice\",\"gender\":\"male\",\"style\":\"clean\"},{\"label\":\"元气女声\",\"value\":\"longanhuan\",\"provider\":\"dashscope_cosyvoice\",\"gender\":\"female\",\"style\":\"energetic\"},{\"label\":\"知性女声\",\"value\":\"longxiaochun_v2\",\"provider\":\"dashscope_cosyvoice\",\"gender\":\"female\",\"style\":\"intellectual\"},{\"label\":\"平和女声\",\"value\":\"longanwen\",\"provider\":\"dashscope_cosyvoice\",\"gender\":\"female\",\"style\":\"calm\"},{\"label\":\"理性播报男声\",\"value\":\"sambert-zhiming-v1\",\"provider\":\"dashscope_sambert\",\"gender\":\"male\",\"style\":\"rational\"},{\"label\":\"治愈陪伴女声\",\"value\":\"sambert-zhiya-v1\",\"provider\":\"dashscope_sambert\",\"gender\":\"female\",\"style\":\"healing\"},{\"label\":\"激励主播男声\",\"value\":\"sambert-zhihao-v1\",\"provider\":\"dashscope_sambert\",\"gender\":\"male\",\"style\":\"motivational\"}]"
    STICKMAN_OUTPUT_DIR: str = "stickman"

    ARTICLE_DAILY_LIMIT: int = 20


@lru_cache()
def get_settings():
    return Settings()
