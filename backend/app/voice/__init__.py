"""语音助手「小曼」后端模块。

设计：
- WS 双工：/api/voice/ws?token=<jwt>
- Provider 抽象：ASR / LLM / TTS 三大接口，工程期 provider_mock 走通全链路，
  接入火山引擎时只换 provider_volc。
- 与 openclaw 并列，是个可选模块；VOICE_ENABLED=false 时完全不挂载路由。
"""
from app.voice.config import get_voice_settings, is_enabled  # noqa: F401
from app.voice.router import router  # noqa: F401
