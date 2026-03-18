from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./manim_platform.db"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # LLM Provider Configuration (auto/deepseek/gemini/openai)
    LLM_PROVIDER: str = "auto"
    
    # DeepSeek (Priority 1)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    
    # Gemini (Priority 2)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    
    # OpenAI (Priority 3)
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"
    
    # Legacy support for LLM_MODEL
    LLM_MODEL: str = ""
    
    REDIS_URL: str = "redis://localhost:6379/0"
    
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_BUCKET_NAME: str = "manim-videos"
    OSS_ENDPOINT: str = "oss-cn-hangzhou.aliyuncs.com"
    
    CORS_ORIGINS: str = "http://localhost:5173"
    VITE_API_BASE_URL: str = ""
    
    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env")
        extra = "ignore"


@lru_cache()
def get_settings():
    return Settings()
