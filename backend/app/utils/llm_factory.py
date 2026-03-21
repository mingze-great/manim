import os
from abc import ABC, abstractmethod
from typing import Any
import google.generativeai as genai

from app.config import get_settings

settings = get_settings()


class LLMAdapter(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], model: str, **kwargs) -> str:
        pass


class DeepSeekAdapter(LLMAdapter):
    """DeepSeek 适配器 - 兼容 OpenAI 格式"""
    
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
    
    async def chat(self, messages: list[dict], model: str = None, **kwargs) -> str:
        model = model or settings.DEEPSEEK_MODEL
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
    
    async def stream_chat(self, messages: list[dict], model: str = None, **kwargs):
        """流式聊天 - 返回生成器"""
        model = model or settings.DEEPSEEK_MODEL
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            **kwargs
        )
        return response


class GeminiAdapter(LLMAdapter):
    """Gemini 适配器 - 使用 Google 官方 SDK"""
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
    
    async def chat(self, messages: list[dict], model: str = None, **kwargs) -> str:
        model_name = model or settings.GEMINI_MODEL
        
        # 转换消息格式
        gemini_messages = []
        system_content = ""
        
        for msg in messages:
            role = msg.get("role", "")
            if role == "system":
                system_content = msg["content"]
            elif role == "user":
                gemini_messages.append(msg)
            elif role == "assistant":
                gemini_messages.append(msg)
        
        # 使用最新的 gemini 模型
        gemini_model = genai.GenerativeModel(
            model_name,
            system_instruction=system_content
        )
        
        # 转换最后一条用户消息
        if gemini_messages and gemini_messages[-1].get("role") == "user":
            user_content = gemini_messages[-1]["content"]
            response = await gemini_model.generate_content_async(user_content)
            return response.text
        
        return ""
    
    async def stream_chat(self, messages: list[dict], model: str = None, **kwargs):
        """流式聊天 - Gemini 暂不支持流式，回退到普通聊天"""
        content = await self.chat(messages, model, **kwargs)
        
        class FakeStream:
            def __init__(self, content):
                self.content = content
                self._done = False
            
            async def __aiter__(self):
                if not self._done:
                    class FakeChunk:
                        class FakeDelta:
                            content = self.content
                            reasoning_content = None
                        choices = [type('obj', (object,), {'delta': self.FakeDelta()})]
                    yield FakeChunk()
                    self._done = True
        
        return FakeStream(content)


class OpenAIAdapter(LLMAdapter):
    """OpenAI 适配器"""
    
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
    
    async def chat(self, messages: list[dict], model: str = None, **kwargs) -> str:
        model = model or settings.OPENAI_MODEL
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
    
    async def stream_chat(self, messages: list[dict], model: str = None, **kwargs):
        """流式聊天 - 返回生成器"""
        model = model or settings.OPENAI_MODEL
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            **kwargs
        )
        return response


class QwenAdapter(LLMAdapter):
    """阿里云通义千问适配器 - 使用专门的文本模型"""
    
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
    
    async def chat(self, messages: list[dict], model: str = None, **kwargs) -> str:
        # 强制使用 qwen-plus 纯文本模型，避免多模态问题
        model = "qwen-plus"
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
    
    async def stream_chat(self, messages: list[dict], model: str = None, **kwargs):
        """流式聊天 - 返回生成器"""
        model = model or "qwen-plus"
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            **kwargs
        )
        return response


class LLMFactory:
    """LLM 工厂类 - 自动选择可用的 LLM 提供商"""
    
    _client_cache = None
    
    @classmethod
    def get_client(cls) -> LLMAdapter:
        """获取 LLM 客户端，按优先级自动选择"""
        
        # 如果已缓存，直接返回
        if cls._client_cache is not None:
            return cls._client_cache
        
        # 每次都重新检查配置
        provider = settings.LLM_PROVIDER.lower()
        
        # 自动选择模式
        if provider == "auto":
            if settings.DEEPSEEK_API_KEY:
                cls._client_cache = DeepSeekAdapter()
            elif settings.GEMINI_API_KEY:
                cls._client_cache = GeminiAdapter()
            elif settings.OPENAI_API_KEY:
                cls._client_cache = OpenAIAdapter()
            else:
                raise ValueError(
                    "未配置任何 LLM API Key。\n"
                    "请在 .env 中配置以下任一API Key:\n"
                    "  - DEEPSEEK_API_KEY (推荐)\n"
                    "  - GEMINI_API_KEY\n"
                    "  - OPENAI_API_KEY"
                )
        # 指定提供商
        elif provider == "deepseek":
            if not settings.DEEPSEEK_API_KEY:
                raise ValueError("未配置 DEEPSEEK_API_KEY")
            cls._client_cache = DeepSeekAdapter()
        elif provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise ValueError("未配置 GEMINI_API_KEY")
            cls._client_cache = GeminiAdapter()
        elif provider in ["openai", "qwen", "aliyun"]:
            if not settings.OPENAI_API_KEY:
                raise ValueError("未配置 OPENAI_API_KEY")
            # 如果是阿里云，检测是否使用通义千问
            if settings.OPENAI_BASE_URL and "aliyuncs" in settings.OPENAI_BASE_URL:
                cls._client_cache = QwenAdapter()
            else:
                cls._client_cache = OpenAIAdapter()
        else:
            raise ValueError(f"不支持的 LLM 提供商: {provider}")
        
        return cls._client_cache
    
    @classmethod
    def get_model_name(cls) -> str:
        """获取当前使用的模型名称"""
        provider = settings.LLM_PROVIDER.lower()
        
        if provider == "auto":
            if settings.DEEPSEEK_API_KEY:
                return settings.DEEPSEEK_MODEL
            elif settings.GEMINI_API_KEY:
                return settings.GEMINI_MODEL
            elif settings.OPENAI_API_KEY:
                return settings.OPENAI_MODEL
        elif provider == "deepseek":
            return settings.DEEPSEEK_MODEL
        elif provider == "gemini":
            return settings.GEMINI_MODEL
        elif provider == "openai":
            return settings.OPENAI_MODEL
        
        return "unknown"
