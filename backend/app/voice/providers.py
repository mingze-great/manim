"""Provider 抽象：ASR / LLM / TTS。

工程期跑 providers_mock；接入火山换 providers_volc。事件流面向 WS 会话，
使用简单的 dict 形状而非严格类型，便于直接 json.dumps 发到前端。
"""
from __future__ import annotations

from typing import AsyncIterator, Protocol


class AsrProvider(Protocol):
    async def stream(self, pcm_chunks: AsyncIterator[bytes]) -> AsyncIterator[dict]:
        """把音频流转成一串事件：
        {"type": "partial", "text": "…"}
        {"type": "final",   "text": "…"}
        最终发出 final 后自然结束。
        """
        ...


class TtsProvider(Protocol):
    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        """把文本转成音频块（16kHz mono 16bit PCM 或 mp3 皆可，
        前端只当二进制转发到 <audio>）。"""
        ...


class LlmProvider(Protocol):
    async def chat_stream(self, user_text: str) -> AsyncIterator[str]:
        """流式吐字符串（一段中文回复）。"""
        ...
