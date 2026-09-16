/* 麦克风采集：getUserMedia → AudioContext(16k) → ScriptProcessor 抽 16bit PCM
   本轮不引入 AudioWorklet 依赖，用 ScriptProcessorNode 起步。 */

const TARGET_SR = 16000

export interface AudioCaptureHandle {
  stop: () => void
}

/** 把 Float32 buffer 下采样并转 16bit PCM Little-Endian。 */
function encodePCM16(input: Float32Array, srcRate: number): ArrayBuffer {
  const ratio = srcRate / TARGET_SR
  const outLen = Math.floor(input.length / ratio)
  const out = new Int16Array(outLen)
  for (let i = 0; i < outLen; i++) {
    const j = Math.floor(i * ratio)
    let s = input[j]
    if (s > 1) s = 1
    if (s < -1) s = -1
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff
  }
  return out.buffer
}

export async function startCapture(
  onChunk: (pcm: ArrayBuffer) => void,
): Promise<AudioCaptureHandle> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      channelCount: 1,
    },
  })

  const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
  const source = ctx.createMediaStreamSource(stream)
  // 老 API，浏览器普遍支持；deprecated 但足够用。
  const bufSize = 4096
  const proc = (ctx as any).createScriptProcessor(bufSize, 1, 1)

  proc.onaudioprocess = (e: AudioProcessingEvent) => {
    const input = e.inputBuffer.getChannelData(0)
    onChunk(encodePCM16(input, ctx.sampleRate))
  }
  source.connect(proc)
  proc.connect(ctx.destination)

  return {
    stop: () => {
      try { proc.disconnect() } catch {}
      try { source.disconnect() } catch {}
      try { ctx.close() } catch {}
      stream.getTracks().forEach((t) => t.stop())
    },
  }
}
