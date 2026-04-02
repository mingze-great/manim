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
    """阿里云百炼适配器 - 支持代码生成和文本对话的独立降级"""
    
    def __init__(self):
        from openai import AsyncOpenAI
        import httpx
        
        self.client = AsyncOpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,
            timeout=httpx.Timeout(30.0, connect=10.0)
        )
        
        # 代码生成模型链
        self.code_models = [
            settings.DASHSCOPE_CODE_MODEL,
            settings.DASHSCOPE_CODE_FALLBACK_MODEL
        ]
        
        # 文本对话模型链
        self.chat_models = [
            settings.DASHSCOPE_CHAT_MODEL,
            settings.DASHSCOPE_CHAT_FALLBACK_MODEL_1,
            settings.DASHSCOPE_CHAT_FALLBACK_MODEL_2
        ]
        
        # 可用模型列表（供用户选择）
        self.available_models = [m.strip() for m in settings.DASHSCOPE_AVAILABLE_MODELS.split(",")]
    
    async def chat(self, messages: list[dict], model: str = None, **kwargs) -> str:
        """文本对话 - 使用对话模型链"""
        models_to_try = [model] if model else self.chat_models
        
        for i, current_model in enumerate(models_to_try):
            try:
                print(f"[DashScope] 尝试对话模型: {current_model}")
                response = await self.client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    **kwargs
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"[DashScope] 模型 {current_model} 失败: {e}")
                if i < len(models_to_try) - 1:
                    print(f"[DashScope] 降级到: {models_to_try[i+1]}")
                else:
                    raise e
        
        raise Exception("所有模型均失败")
    
    async def generate_code(self, messages: list[dict], model: str = None, **kwargs):
        """代码生成 - 使用更长的超时时间（120秒）"""
        from openai import AsyncOpenAI
        import httpx
        
        # 创建更长超时的客户端（120秒，代码生成需要更长时间）
        long_timeout_client = AsyncOpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,
            timeout=httpx.Timeout(120.0, connect=10.0)
        )
        
        models_to_try = [model] if model else self.code_models
        
        for i, current_model in enumerate(models_to_try):
            try:
                print(f"[DashScope] 尝试代码生成模型: {current_model}")
                response = await long_timeout_client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    **kwargs
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"[DashScope] 代码模型 {current_model} 失败: {e}")
                if i < len(models_to_try) - 1:
                    print(f"[DashScope] 降级到: {models_to_try[i+1]}")
                else:
                    raise e
        
        raise Exception("所有代码模型均失败")
    
    async def chat_with_response(self, messages: list[dict], model: str = None, **kwargs):
        """返回完整的 response 对象"""
        models_to_try = [model] if model else self.chat_models
        
        for i, current_model in enumerate(models_to_try):
            try:
                print(f"[DashScope] 尝试对话模型: {current_model}")
                response = await self.client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    **kwargs
                )
                return response
            except Exception as e:
                print(f"[DashScope] 模型 {current_model} 失败: {e}")
                if i < len(models_to_try) - 1:
                    print(f"[DashScope] 降级到: {models_to_try[i+1]}")
                else:
                    raise e
        
        raise Exception("所有模型均失败")
    
    async def stream_chat(self, messages: list[dict], model: str = None, **kwargs):
        """流式对话 - 使用对话模型链"""
        models_to_try = [model] if model else self.chat_models
        
        for i, current_model in enumerate(models_to_try):
            try:
                print(f"[DashScope] 尝试流式对话模型: {current_model}")
                response = await self.client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    stream=True,
                    stream_options={"include_usage": True},
                    **kwargs
                )
                return response
            except Exception as e:
                print(f"[DashScope] 模型 {current_model} 失败: {e}")
                if i < len(models_to_try) - 1:
                    print(f"[DashScope] 降级到: {models_to_try[i+1]}")
                else:
                    raise e
        
        raise Exception("所有模型均失败")
    
    async def generate_code_stream(self, messages: list[dict], model: str = None, **kwargs):
        """流式代码生成 - 使用代码模型链"""
        models_to_try = [model] if model else self.code_models
        
        for i, current_model in enumerate(models_to_try):
            try:
                print(f"[DashScope] 尝试流式代码生成模型: {current_model}")
                response = await self.client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    stream=True,
                    stream_options={"include_usage": True},
                    **kwargs
                )
                return response
            except Exception as e:
                print(f"[DashScope] 代码模型 {current_model} 失败: {e}")
                if i < len(models_to_try) - 1:
                    print(f"[DashScope] 降级到: {models_to_try[i+1]}")
                else:
                    raise e
        
        raise Exception("所有代码模型均失败")
    
    def get_available_models(self) -> list:
        """获取用户可选择的模型列表"""
        return self.available_models
    
    def get_current_model(self) -> str:
        """获取当前主对话模型"""
        return self.chat_models[0]
    
    def get_code_model(self) -> str:
        """获取当前主代码模型"""
        return self.code_models[0]


class DeepSeekAdapter(LLMAdapter):
    """DeepSeek 适配器 - 支持降级到备用模型"""
    
    def __init__(self):
        from openai import AsyncOpenAI
        import httpx
        
        # 主 API
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=httpx.Timeout(180.0, connect=30.0)
        )
        self.model = settings.DEEPSEEK_MODEL
        
        # 降级 API
        self.fallback_client = None
        self.fallback_model = settings.DEEPSEEK_FALLBACK_MODEL
        if settings.DEEPSEEK_FALLBACK_API_KEY:
            self.fallback_client = AsyncOpenAI(
                api_key=settings.DEEPSEEK_FALLBACK_API_KEY,
                base_url=settings.DEEPSEEK_FALLBACK_BASE_URL,
                timeout=httpx.Timeout(180.0, connect=30.0)
            )
    
    async def chat(self, messages: list[dict], model: str = None, **kwargs) -> str:
        model = model or self.model
        
        # 尝试主 API
        try:
            print(f"[DeepSeek] 使用主模型: {model}")
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[DeepSeek] 主模型失败: {e}")
            
            # 降级到备用 API
            if self.fallback_client:
                print(f"[DeepSeek] 降级到备用模型: {self.fallback_model}")
                try:
                    response = await self.fallback_client.chat.completions.create(
                        model=self.fallback_model,
                        messages=messages,
                        **kwargs
                    )
                    return response.choices[0].message.content
                except Exception as fallback_error:
                    print(f"[DeepSeek] 备用模型也失败: {fallback_error}")
                    raise fallback_error
            raise e
    
    async def chat_with_response(self, messages: list[dict], model: str = None, **kwargs):
        model = model or self.model
        
        # 尝试主 API
        try:
            print(f"[DeepSeek] 使用主模型: {model}")
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
            return response
        except Exception as e:
            print(f"[DeepSeek] 主模型失败: {e}")
            
            # 降级到备用 API
            if self.fallback_client:
                print(f"[DeepSeek] 降级到备用模型: {self.fallback_model}")
                try:
                    response = await self.fallback_client.chat.completions.create(
                        model=self.fallback_model,
                        messages=messages,
                        **kwargs
                    )
                    return response
                except Exception as fallback_error:
                    print(f"[DeepSeek] 备用模型也失败: {fallback_error}")
                    raise fallback_error
            raise e
    
    async def stream_chat(self, messages: list[dict], model: str = None, **kwargs):
        model = model or self.model
        
        # 尝试主 API
        try:
            print(f"[DeepSeek] 使用主模型(流式): {model}")
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
                **kwargs
            )
            return response
        except Exception as e:
            print(f"[DeepSeek] 主模型失败: {e}")
            
            # 降级到备用 API
            if self.fallback_client:
                print(f"[DeepSeek] 降级到备用模型(流式): {self.fallback_model}")
                try:
                    response = await self.fallback_client.chat.completions.create(
                        model=self.fallback_model,
                        messages=messages,
                        stream=True,
                        stream_options={"include_usage": True},
                        **kwargs
                    )
                    return response
                except Exception as fallback_error:
                    print(f"[DeepSeek] 备用模型也失败: {fallback_error}")
                    raise fallback_error
            raise e


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
    _client_cache = None
    
    @classmethod
    def get_client(cls) -> LLMAdapter:
        if cls._client_cache is not None:
            return cls._client_cache
        
        if not settings.DASHSCOPE_API_KEY:
            raise ValueError(
                "未配置 DASHSCOPE_API_KEY。\n"
                "请在 .env 中配置 DASHSCOPE_API_KEY"
            )
        
        cls._client_cache = DashScopeAdapter()
        return cls._client_cache
    
    @classmethod
    def get_model_name(cls) -> str:
        return settings.DASHSCOPE_CHAT_MODEL
    
    @classmethod
    def get_chat_model(cls) -> str:
        return settings.DASHSCOPE_CHAT_MODEL
    
    @classmethod
    def get_code_model(cls) -> str:
        return settings.DASHSCOPE_CODE_MODEL
    
    @classmethod
    def get_available_models(cls) -> list:
        return [m.strip() for m in settings.DASHSCOPE_AVAILABLE_MODELS.split(",")]
