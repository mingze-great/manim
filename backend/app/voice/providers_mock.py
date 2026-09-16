"""Mock providers —— 工程期走通全链路，LLM 是真的。

- MockAsr：收到多少 PCM chunk 都不真识别，最后返回一段固定假文本；
- OpenClawLlm：复用 openclaw 的 hyhawang 通道，走真 LLM，效果和热点日报一致；
- MockTts：返回一段计算好的静音 PCM，播放时长按文本长度估算，前端可以据此驱动嘴型动效。
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from app.openclaw.config import get_openclaw_settings
from app.openclaw.service import _call_chat_completions
from app.voice.config import VoiceSettings


class MockAsr:
    async def stream(self, pcm_chunks: AsyncIterator[bytes]) -> AsyncIterator[dict]:
        collected = 0
        async for chunk in pcm_chunks:
            collected += len(chunk)
            # 每 6 帧假装吐一次 partial
            if collected and collected % (16000 * 2 * 1) == 0:
                yield {"type": "partial", "text": "（正在识别…）"}
        # 简单按收到的字节数估内容
        if collected == 0:
            yield {"type": "final", "text": ""}
        else:
            yield {"type": "final", "text": "小曼你好，这是一次测试语音输入。"}


class OpenClawLlm:
    """借用 openclaw 已经配好的 hyhawang 通道跑 chat.completions。
    工程期不需要单独申请 key，用户已经在 openclaw 里配好了 OPENCLAW_LLM_*.
    """

    def __init__(self, settings: VoiceSettings):
        self.settings = settings
        self.oc = get_openclaw_settings()

    async def chat_stream(self, user_text: str) -> AsyncIterator[str]:
        model = self.settings.llm_model or self.oc.llm_model
        messages = [
            {"role": "system", "content": self.settings.llm_system_prompt},
            {"role": "user", "content": user_text or "（用户没有说话，请友好地问一声。）"},
        ]
        # openclaw 的 _call_chat_completions 目前是非流式；这里为了保持接口
        # 一致，一次性拿到内容后按标点切成小段吐出，前端就能看到「逐段浮现」的效果。
        text = await _call_chat_completions(self.oc, messages, model)
        text = (text or "").strip() or "（小曼一时没想到怎么回答，你可以再试一次。）"
        buf = ""
        for ch in text:
            buf += ch
            # 按标点或 20 字切一段
            if ch in "，。！？!?、；;\n " or len(buf) >= 20:
                yield buf
                buf = ""
                await asyncio.sleep(0)
        if buf:
            yield buf


class MockTts:
    """静音 PCM。采样率 16k mono 16bit，按字符数估播放时长。
    前端拿到 tts-chunk 会真的播放（静音），同时把 tts-text 里的文本喂给嘴型动效。
    """

    SAMPLE_RATE = 16000
    BYTES_PER_SAMPLE = 2
    CHARS_PER_SECOND = 6  # 每秒 6 字，比较接近 TTS 语速

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        if not text:
            return
        seconds = max(0.4, len(text) / self.CHARS_PER_SECOND)
        total_bytes = int(self.SAMPLE_RATE * self.BYTES_PER_SAMPLE * seconds)
        # 按 200ms 一块吐
        chunk_size = self.SAMPLE_RATE * self.BYTES_PER_SAMPLE // 5
        silence = bytes(chunk_size)
        sent = 0
        while sent < total_bytes:
            remaining = total_bytes - sent
            if remaining < chunk_size:
                yield bytes(remaining)
                sent += remaining
            else:
                yield silence
                sent += chunk_size
            await asyncio.sleep(0.05)  # 让事件循环喘口气


def build_providers(settings: VoiceSettings):
    """按 settings.provider 组装。工程期返回 mock/mock/openclaw-llm。"""
    return MockAsr(), OpenClawLlm(settings), MockTts()
