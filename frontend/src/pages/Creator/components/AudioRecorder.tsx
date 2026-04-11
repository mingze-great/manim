import { useEffect, useMemo, useRef, useState } from 'react'
import { Button, Space, Typography, message } from 'antd'
import { AudioOutlined, DeleteOutlined, PauseCircleOutlined } from '@ant-design/icons'

type Props = {
  value: File | null
  onChange: (file: File | null) => void
}

export default function AudioRecorder({ value, onChange }: Props) {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const unsupportedReason = useMemo(() => {
    if (typeof window === 'undefined') return '当前环境无法使用录音功能'
    if (!window.isSecureContext) return '当前页面不是安全环境（需 HTTPS 或可信域名），请改用上传音频文件'
    if (!navigator.mediaDevices) return '当前浏览器不支持媒体设备接口，请改用上传音频文件'
    if (!navigator.mediaDevices.getUserMedia) return '当前浏览器不支持麦克风录音，请改用上传音频文件'
    if (typeof MediaRecorder === 'undefined') return '当前浏览器不支持录音组件，请改用上传音频文件'
    return ''
  }, [])

  useEffect(() => {
    if (!recording) return
    const timer = window.setInterval(() => setSeconds((prev) => prev + 1), 1000)
    return () => window.clearInterval(timer)
  }, [recording])

  useEffect(() => {
    if (!value) {
      setPreviewUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev)
        return null
      })
      return
    }
    const url = URL.createObjectURL(value)
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return url
    })
    return () => URL.revokeObjectURL(url)
  }, [value])

  const stopStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }

  const handleStart = async () => {
    if (unsupportedReason) {
      message.error(unsupportedReason)
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      chunksRef.current = []
      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const file = new File([blob], `record_${Date.now()}.webm`, { type: 'audio/webm' })
        onChange(file)
        stopStream()
      }
      recorder.start()
      setSeconds(0)
      setRecording(true)
    } catch (error) {
      message.error('无法访问麦克风，请检查浏览器权限')
    }
  }

  const handleStop = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  const handleClear = () => {
    onChange(null)
    setSeconds(0)
  }

  return (
    <div className="audio-source-box">
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <div className="audio-source-meta">
          <Typography.Text strong>浏览器录音</Typography.Text>
          <Typography.Text type="secondary">{recording ? `录音中 ${seconds}s` : value ? `已录制: ${value.name}` : '未录制'}</Typography.Text>
          {!!unsupportedReason && <Typography.Text type="warning">{unsupportedReason}</Typography.Text>}
        </div>
        <Space wrap>
          {!recording ? (
            <Button icon={<AudioOutlined />} onClick={handleStart} disabled={!!unsupportedReason}>开始录音</Button>
          ) : (
            <Button danger icon={<PauseCircleOutlined />} onClick={handleStop}>停止录音</Button>
          )}
          {value && (
            <Button icon={<DeleteOutlined />} onClick={handleClear}>清除录音</Button>
          )}
        </Space>
        {previewUrl && (
          <audio controls src={previewUrl} style={{ width: '100%' }} />
        )}
      </Space>
    </div>
  )
}
