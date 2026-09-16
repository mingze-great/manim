import { useEffect, useState } from 'react'
import { Button } from 'antd'
import HeartOrb from './HeartOrb'
import Timeline from './Timeline'
import { useVoiceSession } from './useVoiceSession'
import { voiceApi, type VoiceHealth } from '@/services/voice'
import './Voice.css'

export default function VoicePage() {
  const s = useVoiceSession()
  const [health, setHealth] = useState<VoiceHealth | null>(null)
  const [draft, setDraft] = useState('')

  useEffect(() => {
    voiceApi.health().then(({ data }) => setHealth(data)).catch(() => setHealth(null))
  }, [])

  return (
    <div className="voice-page">
      <div className="voice-stars" />

      <div className="voice-hero">
        <HeartOrb state={s.state} amp={s.amp} />
      </div>

      <div className="voice-hint">
        小曼 · 语音对话（{s.provider === 'mock' ? '开发模式' : s.provider}）
        <br />
        按住 <kbd>Space</kbd> 说话，松开就送出。也可以在下面直接打字给她。
        <br />
        （唤醒词「{s.wakeWord}」将在接入 Porcupine 后启用）
        {health && !health.enabled && (
          <div style={{ color: '#ffb2b2', marginTop: 8 }}>
            服务端 voice 模块未启用，请检查 VOICE_ENABLED
          </div>
        )}
      </div>

      {s.error && <div className="voice-error">⚠️ {s.error}</div>}

      <Timeline turns={s.turns} liveUser={s.liveUser} liveAssistant={s.liveAssistant} />

      <div className="voice-input-bar">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="也可以打字试试…（回车发送）"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && draft.trim()) {
              s.sendText(draft.trim())
              setDraft('')
            }
          }}
        />
        <Button
          type="primary"
          onClick={() => {
            if (draft.trim()) {
              s.sendText(draft.trim())
              setDraft('')
            }
          }}
        >
          发送
        </Button>
      </div>
    </div>
  )
}
