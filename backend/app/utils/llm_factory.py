from __future__ import annotations

from abc import ABC, abstractmethod
from types import SimpleNamespace
from typing import Iterable

import google.generativeai as genai
import httpx

from app.config import get_settings

settings = get_settings()


class LLMAdapter(ABC):
    provider_name = "unknown"

    @abstractmethod
    async def chat(self, messages: list[dict], model: str | None = None, **kwargs) -> str:
        pass

    @abstractmethod
    async def stream_chat(self, messages: list[dict], model: str | None = None, **kwargs):
        pass

    async def chat_with_response(self, messages: list[dict], model: str | None = None, **kwargs):
        content = await self.chat(messages, model, **kwargs)
        return {"content": content, "usage": None}

    async def chat_stream(self, messages: list[dict], model: str | None = None, **kwargs):
        response = await self.stream_chat(messages, model, **kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta if getattr(chunk, "choices", None) else None
            if delta and getattr(delta, "content", None):
                yield delta.content

    async def generate_code(self, messages: list[dict], model: str | None = None, retry_callback=None, **kwargs) -> str:
        return await self.chat(messages, model, **kwargs)

    async def generate_code_stream(self, messages: list[dict], model: str | None = None, **kwargs):
        return await self.stream_chat(messages, model, **kwargs)

    def get_available_models(self) -> list[str]:
        return []

    def get_current_model(self) -> str:
        return ""

    def get_code_model(self) -> str:
        return self.get_current_model()

    def supports_model(self, model: str | None) -> bool:
        normalized = (model or "").strip()
        if not normalized:
            return False
        return normalized in self.get_available_models()


class OpenAICompatibleAdapter(LLMAdapter):
    def __init__(
        self,
        provider_name: str,
        api_key: str,
        base_url: str,
        chat_models: list[str],
        code_models: list[str] | None = None,
        available_models: list[str] | None = None,
        timeout_seconds: float = 30.0,
        connect_timeout_seconds: float = 10.0,
    ):
        from openai import AsyncOpenAI

        self.provider_name = provider_name
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=httpx.Timeout(timeout_seconds, connect=connect_timeout_seconds),
        )
        self.long_timeout_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=httpx.Timeout(300.0, connect=max(connect_timeout_seconds, 15.0)),
        )
        self.chat_models = [item.strip() for item in chat_models if item and item.strip()]
        raw_code_models = code_models if code_models is not None else self.chat_models
        self.code_models = [item.strip() for item in raw_code_models if item and item.strip()]
        raw_available = available_models if available_models is not None else [*self.chat_models, *self.code_models]
        self.available_models = list(dict.fromkeys(item.strip() for item in raw_available if item and item.strip()))

    def _resolve_models(self, override_model: str | None, model_pool: list[str]) -> list[str]:
        if override_model and override_model.strip():
            return [override_model.strip()]
        return model_pool

    async def _chat_once(self, client, model: str, messages: list[dict], **kwargs):
        return await client.chat.completions.create(model=model, messages=messages, **kwargs)

    async def chat(self, messages: list[dict], model: str | None = None, **kwargs) -> str:
        models_to_try = self._resolve_models(model, self.chat_models)
        last_error = None
        for current_model in models_to_try:
            try:
                print(f"[{self.provider_name}] trying chat model: {current_model}")
                response = await self._chat_once(self.client, current_model, messages, **kwargs)
                return response.choices[0].message.content
            except Exception as exc:
                last_error = exc
                print(f"[{self.provider_name}] chat model failed {current_model}: {exc}")
        raise last_error or RuntimeError(f"{self.provider_name} has no available chat models")

    async def chat_with_response(self, messages: list[dict], model: str | None = None, **kwargs):
        models_to_try = self._resolve_models(model, self.chat_models)
        last_error = None
        for current_model in models_to_try:
            try:
                print(f"[{self.provider_name}] trying chat model: {current_model}")
                return await self._chat_once(self.client, current_model, messages, **kwargs)
            except Exception as exc:
                last_error = exc
                print(f"[{self.provider_name}] chat model failed {current_model}: {exc}")
        raise last_error or RuntimeError(f"{self.provider_name} has no available chat models")

    async def stream_chat(self, messages: list[dict], model: str | None = None, **kwargs):
        models_to_try = self._resolve_models(model, self.chat_models)
        last_error = None
        for current_model in models_to_try:
            try:
                print(f"[{self.provider_name}] trying stream chat model: {current_model}")
                return await self._chat_once(
                    self.client,
                    current_model,
                    messages,
                    stream=True,
                    stream_options={"include_usage": True},
                    **kwargs,
                )
            except Exception as exc:
                last_error = exc
                print(f"[{self.provider_name}] stream chat model failed {current_model}: {exc}")
        raise last_error or RuntimeError(f"{self.provider_name} has no available stream chat models")

    async def generate_code(self, messages: list[dict], model: str | None = None, retry_callback=None, **kwargs) -> str:
        models_to_try = self._resolve_models(model, self.code_models)
        last_error = None
        for current_model in models_to_try:
            try:
                print(f"[{self.provider_name}] trying code model: {current_model}")
                if retry_callback:
                    retry_callback(f"正在使用 {self.provider_name} 的 {current_model} 生成脚本...")
                response = await self._chat_once(self.long_timeout_client, current_model, messages, **kwargs)
                return response.choices[0].message.content
            except Exception as exc:
                last_error = exc
                print(f"[{self.provider_name}] code model failed {current_model}: {exc}")
        raise last_error or RuntimeError(f"{self.provider_name} has no available code models")

    async def generate_code_stream(self, messages: list[dict], model: str | None = None, **kwargs):
        models_to_try = self._resolve_models(model, self.code_models)
        last_error = None
        for current_model in models_to_try:
            try:
                print(f"[{self.provider_name}] trying stream code model: {current_model}")
                return await self._chat_once(
                    self.client,
                    current_model,
                    messages,
                    stream=True,
                    stream_options={"include_usage": True},
                    **kwargs,
                )
            except Exception as exc:
                last_error = exc
                print(f"[{self.provider_name}] stream code model failed {current_model}: {exc}")
        raise last_error or RuntimeError(f"{self.provider_name} has no available stream code models")

    def get_available_models(self) -> list[str]:
        return self.available_models

    def get_current_model(self) -> str:
        return self.chat_models[0] if self.chat_models else ""

    def get_code_model(self) -> str:
        return self.code_models[0] if self.code_models else self.get_current_model()


class GeminiAdapter(LLMAdapter):
    provider_name = "gemini"

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL

    async def chat(self, messages: list[dict], model: str | None = None, **kwargs) -> str:
        model_name = model or self.model
        system_content = ""
        prompt_lines: list[str] = []
        for msg in messages:
            role = msg.get("role", "")
            content = str(msg.get("content") or "")
            if role == "system":
                system_content = content
            else:
                prompt_lines.append(f"{role}: {content}")

        gemini_model = genai.GenerativeModel(model_name, system_instruction=system_content or None)
        response = await gemini_model.generate_content_async("\n\n".join(prompt_lines))
        return response.text or ""

    async def stream_chat(self, messages: list[dict], model: str | None = None, **kwargs):
        content = await self.chat(messages, model, **kwargs)

        class FakeStream:
            def __init__(self, text: str):
                self.text = text
                self.sent = False

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.sent:
                    raise StopAsyncIteration
                self.sent = True
                return SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content=self.text, reasoning_content=None))]
                )

        return FakeStream(content)

    def get_available_models(self) -> list[str]:
        return [self.model] if self.model else []

    def get_current_model(self) -> str:
        return self.model or ""


class CrossProviderAdapter(LLMAdapter):
    provider_name = "cross-provider"

    def __init__(self, providers: list[LLMAdapter]):
        self.providers = providers

    def _should_retry_with_default(self, provider: LLMAdapter, requested_model: str, operation: str) -> bool:
        if not provider.supports_model(requested_model):
            return True

        default_model = (
            provider.get_code_model()
            if operation in {"generate_code", "generate_code_stream"}
            else provider.get_current_model()
        )
        if not default_model or default_model != requested_model:
            return True

        return any(item != requested_model for item in provider.get_available_models())

    def _build_attempts(self, operation: str, model: str | None) -> list[tuple[LLMAdapter, str | None]]:
        normalized = (model or "").strip()
        if not normalized:
            return [(provider, None) for provider in self.providers]

        attempts: list[tuple[LLMAdapter, str | None]] = []
        matching = [provider for provider in self.providers if provider.supports_model(normalized)]

        for provider in matching:
            attempts.append((provider, normalized))

        for provider in self.providers:
            if self._should_retry_with_default(provider, normalized, operation):
                attempts.append((provider, None))

        return attempts

    async def _try_providers(self, operation: str, *args, model: str | None = None, **kwargs):
        last_error = None
        for provider, attempt_model in self._build_attempts(operation, model):
            try:
                method = getattr(provider, operation)
                model_label = attempt_model or "__provider_default__"
                print(f"[CrossProvider] trying {provider.provider_name}.{operation} model={model_label}")
                return await method(*args, model=attempt_model, **kwargs)
            except Exception as exc:
                last_error = exc
                model_label = attempt_model or "__provider_default__"
                print(f"[CrossProvider] {provider.provider_name}.{operation} failed model={model_label}: {exc}")
        raise last_error or RuntimeError(f"All providers failed for {operation}")

    async def chat(self, messages: list[dict], model: str | None = None, **kwargs) -> str:
        return await self._try_providers("chat", messages, model=model, **kwargs)

    async def chat_with_response(self, messages: list[dict], model: str | None = None, **kwargs):
        return await self._try_providers("chat_with_response", messages, model=model, **kwargs)

    async def stream_chat(self, messages: list[dict], model: str | None = None, **kwargs):
        return await self._try_providers("stream_chat", messages, model=model, **kwargs)

    async def generate_code(self, messages: list[dict], model: str | None = None, retry_callback=None, **kwargs) -> str:
        return await self._try_providers("generate_code", messages, model=model, retry_callback=retry_callback, **kwargs)

    async def generate_code_stream(self, messages: list[dict], model: str | None = None, **kwargs):
        return await self._try_providers("generate_code_stream", messages, model=model, **kwargs)

    def get_available_models(self) -> list[str]:
        merged: list[str] = []
        for provider in self.providers:
            merged.extend(provider.get_available_models())
        return list(dict.fromkeys(item for item in merged if item))

    def get_current_model(self) -> str:
        for provider in self.providers:
            model = provider.get_current_model()
            if model:
                return model
        return ""

    def get_code_model(self) -> str:
        for provider in self.providers:
            model = provider.get_code_model()
            if model:
                return model
        return self.get_current_model()


class LLMFactory:
    @classmethod
    def _build_providers(cls) -> list[LLMAdapter]:
        providers: list[LLMAdapter] = []

        if settings.DASHSCOPE_API_KEY and settings.DASHSCOPE_BASE_URL:
            providers.append(
                OpenAICompatibleAdapter(
                    provider_name="dashscope",
                    api_key=settings.DASHSCOPE_API_KEY,
                    base_url=settings.DASHSCOPE_BASE_URL,
                    chat_models=[
                        settings.DASHSCOPE_CHAT_MODEL,
                        settings.DASHSCOPE_CHAT_FALLBACK_MODEL_1,
                        settings.DASHSCOPE_CHAT_FALLBACK_MODEL_2,
                    ],
                    code_models=[
                        settings.DASHSCOPE_CODE_MODEL,
                        settings.DASHSCOPE_CODE_FALLBACK_MODEL,
                    ],
                    available_models=[item.strip() for item in settings.DASHSCOPE_AVAILABLE_MODELS.split(",") if item.strip()],
                )
            )

        if settings.OPENAI_API_KEY and settings.OPENAI_BASE_URL and settings.OPENAI_MODEL:
            providers.append(
                OpenAICompatibleAdapter(
                    provider_name="openai",
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                    chat_models=[settings.OPENAI_MODEL],
                    code_models=[settings.OPENAI_MODEL],
                    available_models=[settings.OPENAI_MODEL],
                    timeout_seconds=60.0,
                    connect_timeout_seconds=20.0,
                )
            )

        if settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_BASE_URL and settings.DEEPSEEK_MODEL:
            providers.append(
                OpenAICompatibleAdapter(
                    provider_name="deepseek",
                    api_key=settings.DEEPSEEK_API_KEY,
                    base_url=settings.DEEPSEEK_BASE_URL,
                    chat_models=[settings.DEEPSEEK_MODEL],
                    code_models=[settings.DEEPSEEK_MODEL],
                    available_models=[settings.DEEPSEEK_MODEL],
                    timeout_seconds=180.0,
                    connect_timeout_seconds=30.0,
                )
            )

        if settings.DEEPSEEK_FALLBACK_API_KEY and settings.DEEPSEEK_FALLBACK_BASE_URL and settings.DEEPSEEK_FALLBACK_MODEL:
            providers.append(
                OpenAICompatibleAdapter(
                    provider_name="deepseek-fallback",
                    api_key=settings.DEEPSEEK_FALLBACK_API_KEY,
                    base_url=settings.DEEPSEEK_FALLBACK_BASE_URL,
                    chat_models=[settings.DEEPSEEK_FALLBACK_MODEL],
                    code_models=[settings.DEEPSEEK_FALLBACK_MODEL],
                    available_models=[settings.DEEPSEEK_FALLBACK_MODEL],
                    timeout_seconds=180.0,
                    connect_timeout_seconds=30.0,
                )
            )

        if settings.GLM_API_KEY and settings.GLM_BASE_URL and settings.GLM_MODEL:
            providers.append(
                OpenAICompatibleAdapter(
                    provider_name="glm",
                    api_key=settings.GLM_API_KEY,
                    base_url=settings.GLM_BASE_URL,
                    chat_models=[settings.GLM_MODEL],
                    code_models=[settings.GLM_MODEL],
                    available_models=[settings.GLM_MODEL],
                )
            )

        if settings.GEMINI_API_KEY and settings.GEMINI_MODEL:
            providers.append(GeminiAdapter())

        provider_hint = (settings.LLM_PROVIDER or "").strip().lower()
        if provider_hint:
            preferred = [item for item in providers if item.provider_name == provider_hint]
            others = [item for item in providers if item.provider_name != provider_hint]
            providers = preferred + others

        return providers

    @classmethod
    def _visible_providers(cls) -> list[LLMAdapter]:
        providers = cls._build_providers()
        provider_hint = (settings.LLM_PROVIDER or "").strip().lower()
        if provider_hint and provider_hint != "auto":
            preferred = [item for item in providers if item.provider_name == provider_hint]
            if preferred:
                return preferred
        return providers

    @classmethod
    def reset_client_cache(cls) -> None:
        return None

    @classmethod
    def get_client(cls) -> LLMAdapter:
        providers = cls._build_providers()
        if not providers:
            raise ValueError("No LLM providers are configured")

        return providers[0] if len(providers) == 1 else CrossProviderAdapter(providers)

    @classmethod
    def get_model_name(cls) -> str:
        return cls.get_chat_model()

    @classmethod
    def get_chat_model(cls) -> str:
        return cls.get_client().get_current_model()

    @classmethod
    def get_code_model(cls) -> str:
        return cls.get_client().get_code_model()

    @classmethod
    def get_available_models(cls) -> list[str]:
        merged: list[str] = []
        for provider in cls._visible_providers():
            merged.extend(provider.get_available_models())
        return list(dict.fromkeys(item for item in merged if item))
