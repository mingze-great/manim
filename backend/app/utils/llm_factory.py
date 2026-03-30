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
    
    async def chat_with_response(self, messages: list[dict], model: str = None, **kwargs):
        """返回完整的 response 对象，子类可以覆盖此方法"""
        content = await self.chat(messages, model, **kwargs)
        return {"content": content, "usage": None}


class DashScopeAdapter(LLMAdapter):
    """阿里云百炼适配器 - 支持模型降级"""
    
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL
        )
        self.models = [m.strip() for m in settings.DASHSCOPE_MODELS.split(",")]
        self.current_model_index = 0
        self.enable_thinking = settings.DASHSCOPE_ENABLE_THINKING
    
    def _get_extra_body(self):
        if self.enable_thinking:
            return {"enable_thinking": True}
        return {}
    
    async def chat(self, messages: list[dict], model: str = None, **kwargs) -> str:
        model = model or self.models[self.current_model_index]
        extra_body = self._get_extra_body()
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                extra_body=extra_body,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            if self.current_model_index < len(self.models) - 1:
                self.current_model_index += 1
                print(f"[DashScope] 模型 {model} 调用失败，降级到 {self.models[self.current_model_index]}")
                return await self.chat(messages, **kwargs)
            raise e
    
    async def chat_with_response(self, messages: list[dict], model: str = None, **kwargs):
        """返回完整的 response 对象，包含 usage 信息"""
        model = model or self.models[self.current_model_index]
        extra_body = self._get_extra_body()
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                extra_body=extra_body,
                **kwargs
            )
            return response
        except Exception as e:
            if self.current_model_index < len(self.models) - 1:
                self.current_model_index += 1
                print(f"[DashScope] 模型 {model} 调用失败，降级到 {self.models[self.current_model_index]}")
                return await self.chat_with_response(messages, **kwargs)
            raise e
    
    async def stream_chat(self, messages: list[dict], model: str = None, **kwargs):
        model = model or self.models[self.current_model_index]
        extra_body = self._get_extra_body()
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
                extra_body=extra_body,
                **kwargs
            )
            return response
        except Exception as e:
            if self.current_model_index < len(self.models) - 1:
                self.current_model_index += 1
                print(f"[DashScope] 模型 {model} 调用失败，降级到 {self.models[self.current_model_index]}")
                return await self.stream_chat(messages, **kwargs)
            raise e
    
    def get_current_model(self) -> str:
        return self.models[self.current_model_index]


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


class GLMAdapter(LLMAdapter):
    """GLM (智谱AI) 适配器 - 兼容 OpenAI 格式"""
    
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=settings.GLM_API_KEY,
            base_url=settings.GLM_BASE_URL
        )
    
    async def chat(self, messages: list[dict], model: str = None, **kwargs) -> str:
        model = model or settings.GLM_MODEL
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
    
    async def stream_chat(self, messages: list[dict], model: str = None, **kwargs):
        model = model or settings.GLM_MODEL
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
            if settings.DASHSCOPE_API_KEY:
                cls._client_cache = DashScopeAdapter()
            elif settings.GLM_API_KEY:
                cls._client_cache = GLMAdapter()
            elif settings.DEEPSEEK_API_KEY:
                cls._client_cache = DeepSeekAdapter()
            elif settings.GEMINI_API_KEY:
                cls._client_cache = GeminiAdapter()
            elif settings.OPENAI_API_KEY:
                cls._client_cache = OpenAIAdapter()
            else:
                raise ValueError(
                    "未配置任何 LLM API Key。\n"
                    "请在 .env 中配置以下任一API Key:\n"
                    "  - DASHSCOPE_API_KEY (推荐)\n"
                    "  - GLM_API_KEY\n"
                    "  - DEEPSEEK_API_KEY\n"
                    "  - GEMINI_API_KEY\n"
                    "  - OPENAI_API_KEY"
                )
        # 指定提供商
        elif provider == "dashscope":
            if not settings.DASHSCOPE_API_KEY:
                raise ValueError("未配置 DASHSCOPE_API_KEY")
            cls._client_cache = DashScopeAdapter()
        elif provider == "glm":
            if not settings.GLM_API_KEY:
                raise ValueError("未配置 GLM_API_KEY")
            cls._client_cache = GLMAdapter()
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
            if settings.DASHSCOPE_API_KEY:
                if isinstance(cls._client_cache, DashScopeAdapter):
                    return cls._client_cache.get_current_model()
                return settings.DASHSCOPE_MODELS.split(",")[0].strip()
            elif settings.GLM_API_KEY:
                return settings.GLM_MODEL
            elif settings.DEEPSEEK_API_KEY:
                return settings.DEEPSEEK_MODEL
            elif settings.GEMINI_API_KEY:
                return settings.GEMINI_MODEL
            elif settings.OPENAI_API_KEY:
                return settings.OPENAI_MODEL
        elif provider == "dashscope":
            if isinstance(cls._client_cache, DashScopeAdapter):
                return cls._client_cache.get_current_model()
            return settings.DASHSCOPE_MODELS.split(",")[0].strip()
        elif provider == "glm":
            return settings.GLM_MODEL
        elif provider == "deepseek":
            return settings.DEEPSEEK_MODEL
        elif provider == "gemini":
            return settings.GEMINI_MODEL
        elif provider == "openai":
            return settings.OPENAI_MODEL
        
        return "unknown"
    
    @classmethod
    def get_chat_model(cls) -> str:
        """获取对话模型名称"""
        if settings.DASHSCOPE_API_KEY and settings.DASHSCOPE_CHAT_MODEL:
            return settings.DASHSCOPE_CHAT_MODEL
        return cls.get_model_name()
    
    @classmethod
    def get_code_model(cls) -> str:
        """获取代码生成模型名称"""
        if settings.DASHSCOPE_API_KEY and settings.DASHSCOPE_CODE_MODEL:
            return settings.DASHSCOPE_CODE_MODEL
        return cls.get_model_name()
