import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { voiceApi, buildWsUrl } from '@/services/voice'
import { startCapture, type AudioCaptureHandle } from './AudioCapture'
import { VoiceClient, type VoiceServerEvent } from './VoiceClient'
import { startWakeWordDetector, type WakeWordHandle } from './WakeWord'

export type VoiceState = 'idle' | 'wake' | 'listening' | 'thinking' | 'speaking' | 'error'

export interface TurnRecord {
  id: string
  user: string
  assistant: string
}

export interface VoiceSessionApi {
  state: VoiceState
  amp: number
  turns: TurnRecord[]
  liveUser: string
  liveAssistant: string
  error: string | null
  wakeWord: string
  provider: string
  startTurn: () => Promise<void>
  endTurn: () => void
  sendText: (text: string) => void
}

export function useVoiceSession(): VoiceSessionApi {
  const [state, setState] = useState<VoiceState>('idle')
  const [amp, setAmp] = useState(0)
  const [turns, setTurns] = useState<TurnRecord[]>([])
  const [liveUser, setLiveUser] = useState('')
  const [liveAssistant, setLiveAssistant] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [wakeWord, setWakeWord] = useState('小曼')
  const [provider, setProvider] = useState('mock')

  const clientRef = useRef<VoiceClient | null>(null)
  const captureRef = useRef<AudioCaptureHandle | null>(null)
  const wakeRef = useRef<WakeWordHandle | null>(null)
  const playbackCtxRef = useRef<AudioContext | null>(null)
  const nextPlayAtRef = useRef<number>(0)

  const ampRef = useRef(0)
  useEffect(() => {
    let raf = 0
    const tick = () => {
      // 平滑衰减
      ampRef.current *= 0.9
      setAmp(ampRef.current)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])

  const ensureConnection = useCallback(async (): Promise<VoiceClient> => {
    if (clientRef.current?.isOpen()) return clientRef.current

    const { data } = await voiceApi.session()
    setWakeWord(data.wake_word || '小曼')
    setProvider(data.provider || 'mock')

    const client = new VoiceClient(buildWsUrl(data.ws_token), {
      onEvent: (evt) => onEvent(evt),
      onAudio: (chunk) => playAudioChunk(chunk),
      onClose: () => {
        clientRef.current = null
      },
    })
    await client.connect()
    clientRef.current = client
    return client
  }, [])

  const onEvent = useCallback((evt: VoiceServerEvent) => {
    switch (evt.type) {
      case 'ready':
        setWakeWord(evt.wake_word)
        setProvider(evt.provider)
        break
      case 'asr-partial':
        setLiveUser(evt.text)
        break
      case 'asr-final':
        setLiveUser(evt.text)
        setState('thinking')
        break
      case 'llm-token':
        setLiveAssistant((prev) => prev + evt.text)
        break
      case 'tts-start':
        setLiveAssistant(evt.text)
        setState('speaking')
        break
      case 'tts-end':
        break
      case 'turn-end':
        setTurns((prev) => [
          ...prev,
          {
            id: `${Date.now()}`,
            user: liveUserRef.current,
            assistant: liveAssistantRef.current,
          },
        ])
        setLiveUser('')
        setLiveAssistant('')
        setState('idle')
        break
      case 'error':
        setError(evt.detail)
        setState('error')
        break
    }
  }, [])

  // 用 ref 追住最新值，避免在 turn-end 里读到旧闭包
  const liveUserRef = useRef('')
  const liveAssistantRef = useRef('')
  useEffect(() => { liveUserRef.current = liveUser }, [liveUser])
  useEffect(() => { liveAssistantRef.current = liveAssistant }, [liveAssistant])

  const startTurn = useCallback(async () => {
    setError(null)
    setLiveUser('')
    setLiveAssistant('')
    try {
      const client = await ensureConnection()
      client.sendJSON({ type: 'start' })
      setState('listening')
      const handle = await startCapture((pcm) => {
        client.sendBinary(pcm)
        // 简易 amp：取块内最大绝对值
        const view = new Int16Array(pcm)
        let peak = 0
        for (let i = 0; i < view.length; i += 32) {
          const v = Math.abs(view[i]) / 32768
          if (v > peak) peak = v
        }
        ampRef.current = Math.min(1, ampRef.current * 0.7 + peak)
      })
      captureRef.current = handle
    } catch (e: any) {
      setError(e?.message || '麦克风或连接失败')
      setState('error')
    }
  }, [ensureConnection])

  const endTurn = useCallback(() => {
    captureRef.current?.stop()
    captureRef.current = null
    if (clientRef.current?.isOpen()) {
      clientRef.current.sendJSON({ type: 'end' })
      setState('thinking')
    } else {
      setState('idle')
    }
  }, [])

  const sendText = useCallback(async (text: string) => {
    if (!text.trim()) return
    try {
      const client = await ensureConnection()
      setLiveUser(text)
      setState('thinking')
      client.sendJSON({ type: 'text', text })
    } catch (e: any) {
      setError(e?.message || '发送失败')
      setState('error')
    }
  }, [ensureConnection])

  useEffect(() => {
    const handle = startWakeWordDetector({
      onWake: () => setState((s) => (s === 'idle' ? 'wake' : s)),
      onPress: () => { void startTurn() },
      onRelease: () => endTurn(),
    })
    wakeRef.current = handle
    return () => {
      wakeRef.current?.stop()
      wakeRef.current = null
      captureRef.current?.stop()
      clientRef.current?.close()
      if (playbackCtxRef.current && playbackCtxRef.current.state !== 'closed') {
        playbackCtxRef.current.close().catch(() => {})
      }
    }
  }, [startTurn, endTurn])

  const playAudioChunk = useCallback((chunk: ArrayBuffer) => {
    // TTS chunk 是 16k mono 16bit PCM
    let ctx = playbackCtxRef.current
    if (!ctx || ctx.state === 'closed') {
      ctx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 })
      playbackCtxRef.current = ctx
      nextPlayAtRef.current = 0
    }
    const view = new Int16Array(chunk)
    const f = new Float32Array(view.length)
    for (let i = 0; i < view.length; i++) f[i] = view[i] / 32768
    const buf = ctx.createBuffer(1, f.length, 16000)
    buf.getChannelData(0).set(f)
    const src = ctx.createBufferSource()
    src.buffer = buf
    src.connect(ctx.destination)
    const startAt = Math.max(ctx.currentTime, nextPlayAtRef.current)
    src.start(startAt)
    nextPlayAtRef.current = startAt + buf.duration
  }, [])

  return useMemo(
    () => ({
      state, amp, turns, liveUser, liveAssistant, error, wakeWord, provider,
      startTurn, endTurn, sendText,
    }),
    [state, amp, turns, liveUser, liveAssistant, error, wakeWord, provider, startTurn, endTurn, sendText],
  )
}
