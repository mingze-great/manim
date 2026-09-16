/* WebSocket 客户端封装：把二进制音频块和 JSON 事件都路由给上层。 */

export type VoiceServerEvent =
  | { type: 'ready'; wake_word: string; provider: string }
  | { type: 'asr-partial'; text: string }
  | { type: 'asr-final'; text: string }
  | { type: 'llm-token'; text: string }
  | { type: 'tts-start'; text: string }
  | { type: 'tts-end' }
  | { type: 'turn-end'; elapsed_ms?: number }
  | { type: 'error'; detail: string }
  | { type: 'pong' }

export interface VoiceClientHandlers {
  onEvent: (evt: VoiceServerEvent) => void
  onAudio: (chunk: ArrayBuffer) => void
  onClose: () => void
}

export class VoiceClient {
  private ws: WebSocket | null = null

  constructor(private url: string, private handlers: VoiceClientHandlers) {}

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(this.url)
      ws.binaryType = 'arraybuffer'
      this.ws = ws
      ws.onopen = () => resolve()
      ws.onerror = (e) => reject(e)
      ws.onmessage = (ev) => {
        if (typeof ev.data === 'string') {
          try {
            const parsed = JSON.parse(ev.data) as VoiceServerEvent
            this.handlers.onEvent(parsed)
          } catch {
            // ignore
          }
        } else if (ev.data instanceof ArrayBuffer) {
          this.handlers.onAudio(ev.data)
        }
      }
      ws.onclose = () => this.handlers.onClose()
    })
  }

  isOpen(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  sendJSON(payload: object) {
    if (this.isOpen()) this.ws!.send(JSON.stringify(payload))
  }

  sendBinary(buf: ArrayBuffer) {
    if (this.isOpen()) this.ws!.send(buf)
  }

  close() {
    try { this.ws?.close() } catch {}
    this.ws = null
  }
}
