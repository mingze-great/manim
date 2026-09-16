import api from './api'

export interface VoiceHealth {
  enabled: boolean
  provider: string
  wake_word: string
  volc_configured: boolean
}

export interface VoiceSessionResp {
  ws_token: string
  wake_word: string
  provider: string
}

export const voiceApi = {
  health: () => api.get<VoiceHealth>('/voice/health'),
  session: () => api.post<VoiceSessionResp>('/voice/session'),
}

export function buildWsUrl(token: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.host
  return `${proto}://${host}/api/voice/ws?token=${encodeURIComponent(token)}`
}
