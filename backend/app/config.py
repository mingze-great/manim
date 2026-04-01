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
    
    # Admin
    ADMIN_EMAIL: str = ""
    
    # LLM Provider Configuration (auto/deepseek/gemini/openai/dashscope)
    LLM_PROVIDER: str = "auto"
    
    # 阿里云百炼（优先级1）
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_MODELS: str = "MiniMax-M2.5,deepseek-v3.2,qwen3-coder-next,kimi-k2-thinking"
    DASHSCOPE_CHAT_MODEL: str = "qwen-plus"
    DASHSCOPE_CODE_MODEL: str = "deepseek-v3.2"
    DASHSCOPE_AVAILABLE_MODELS: str = "MiniMax-M2.5,deepseek-v3.2,qwen3-coder-next,kimi-k2-thinking"
    DASHSCOPE_ENABLE_THINKING: bool = False
    
    # DeepSeek (Priority 2)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://openrouter.fans/v1"
    DEEPSEEK_MODEL: str = "deepseek/deepseek-v3.2"
    
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
    
    # WeChat Pay Configuration
    WX_MCH_ID: str = ""
    WX_APP_ID: str = ""
    WX_API_KEY: str = ""
    WX_NOTIFY_URL: str = "https://your-domain.com/api/payment/wx/notify"
    
    CORS_ORIGINS: str = "*"
    VITE_API_BASE_URL: str = ""


@lru_cache()
def get_settings():
    return Settings()
