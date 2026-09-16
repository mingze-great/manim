"""单个 WS 语音会话的编排逻辑。

一次「用户按话筒 → 松开」= 一个 turn：
    recv audio chunks (client) → asr.stream → llm.chat_stream → tts.synthesize
                                                                       ↓
                                                   send tts-chunk (bin) + llm-token (text)

事件（服务端→客户端）—— 全部 JSON except 音频块（BinaryMessage）：
  {"type": "ready"}
  {"type": "asr-partial", "text": ...}
  {"type": "asr-final",   "text": ...}
  {"type": "llm-token",   "text": ...}
  {"type": "tts-start",   "text": <本段将播的完整文本>}
  <binary>  ← tts 音频块（属于最近一次 tts-start 对应的一段）
  {"type": "tts-end"}
  {"type": "turn-end"}
  {"type": "error", "detail": ...}

事件（客户端→服务端）：
  {"type": "start"}                         用户开始说话
  <binary>                                  16k mono 16bit PCM 一小段
  {"type": "end"}                           用户说完
  {"type": "text", "text": "..."}           不走 ASR，直接跳到 LLM（键盘输入 / debug）
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncIterator

from fastapi import WebSocket, WebSocketDisconnect

from app.voice.config import VoiceSettings


class VoiceSession:
    def __init__(self, ws: WebSocket, settings: VoiceSettings, providers):
        self.ws = ws
        self.settings = settings
        self.asr, self.llm, self.tts = providers
        self._audio_q: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=256)
        self._end_evt = asyncio.Event()
        self._text_shortcut: str | None = None

    async def _pcm_iter(self) -> AsyncIterator[bytes]:
        while True:
            chunk = await self._audio_q.get()
            if chunk is None:
                return
            yield chunk

    async def _send_json(self, payload: dict) -> None:
        await self.ws.send_text(json.dumps(payload, ensure_ascii=False))

    async def _run_turn(self, ) -> None:
        """跑一次 ASR → LLM → TTS。"""
        t0 = time.time()

        # 1) ASR
        if self._text_shortcut is not None:
            user_text = self._text_shortcut
            await self._send_json({"type": "asr-final", "text": user_text})
        else:
            user_text = ""
            try:
                async for evt in self.asr.stream(self._pcm_iter()):
                    if evt["type"] == "final":
                        user_text = evt.get("text") or ""
                    await self._send_json({"type": f"asr-{evt['type']}", "text": evt.get("text", "")})
            except Exception as e:  # noqa: BLE001
                await self._send_json({"type": "error", "detail": f"ASR 失败: {type(e).__name__}: {e}"})
                return

        # 2) LLM
        reply_full = ""
        try:
            async for tok in self.llm.chat_stream(user_text):
                reply_full += tok
                await self._send_json({"type": "llm-token", "text": tok})
        except Exception as e:  # noqa: BLE001
            await self._send_json({"type": "error", "detail": f"LLM 失败: {type(e).__name__}: {e}"})
            return

        # 3) TTS —— 把整段 reply 一次性合成，然后按块吐
        await self._send_json({"type": "tts-start", "text": reply_full})
        try:
            async for chunk in self.tts.synthesize(reply_full):
                if chunk:
                    await self.ws.send_bytes(chunk)
        except Exception as e:  # noqa: BLE001
            await self._send_json({"type": "error", "detail": f"TTS 失败: {type(e).__name__}: {e}"})
            return

        await self._send_json({"type": "tts-end"})
        await self._send_json({"type": "turn-end", "elapsed_ms": int((time.time() - t0) * 1000)})

    async def run(self) -> None:
        await self._send_json({
            "type": "ready",
            "wake_word": self.settings.wake_word,
            "provider": self.settings.provider,
        })

        while True:
            try:
                msg = await self.ws.receive()
            except WebSocketDisconnect:
                return

            if msg.get("type") == "websocket.disconnect":
                return

            # 二进制 => 音频
            if msg.get("bytes") is not None:
                await self._audio_q.put(msg["bytes"])
                continue

            raw = msg.get("text")
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue

            mtype = payload.get("type")
            if mtype == "start":
                # 重置本轮状态
                self._audio_q = asyncio.Queue(maxsize=256)
                self._end_evt = asyncio.Event()
                self._text_shortcut = None
            elif mtype == "end":
                # 关闭音频流，触发一次 turn
                await self._audio_q.put(None)
                await self._run_turn()
            elif mtype == "text":
                # 键盘 / debug 通道：跳过 ASR
                self._text_shortcut = (payload.get("text") or "").strip()
                await self._audio_q.put(None)  # 保证 asr 不阻塞（虽然我们不会用它）
                await self._run_turn()
            elif mtype == "ping":
                await self._send_json({"type": "pong"})
            else:
                # 未知消息忽略
                continue
