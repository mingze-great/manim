"""火山引擎 provider —— 工程期骨架，未接入实际实现。

三个方法都抛 NotImplementedError；当用户提供 access token 后再回来填。
接入时的关键：
- ASR：https://www.volcengine.com/docs/6561/80816  一句话 / 流式识别 (WSS)
- TTS：https://www.volcengine.com/docs/6561/79817  流式合成 (WSS)
- 建议直接开双 WS 桥接：本模块的 WS <-> 火山 WS
"""
from __future__ import annotations

from typing import AsyncIterator

from app.voice.config import VoiceSettings


class VolcAsr:
    def __init__(self, s: VoiceSettings):
        self.s = s

    async def stream(self, pcm_chunks):
        raise NotImplementedError("VolcAsr 未接入，等 VOLC_ACCESS_TOKEN 就绪")


class VolcTts:
    def __init__(self, s: VoiceSettings):
        self.s = s

    async def synthesize(self, text: str):
        raise NotImplementedError("VolcTts 未接入，等 VOLC_ACCESS_TOKEN 就绪")
        yield b""  # 让类型检查把它当异步生成器


class VolcLlm:
    def __init__(self, s: VoiceSettings):
        self.s = s

    async def chat_stream(self, user_text: str):
        raise NotImplementedError("VolcLlm 未接入，等 VOLC_ACCESS_TOKEN 就绪")
        yield ""


def build_providers(settings: VoiceSettings):
    return VolcAsr(settings), VolcLlm(settings), VolcTts(settings)
