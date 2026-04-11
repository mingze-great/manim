import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Descriptions, Progress, Space, Spin, Steps, Tag, message } from 'antd'
import { DownloadOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { Project, Task, projectApi } from '@/services/project'
import { useAuthStore } from '@/stores/authStore'

const taskStatusText: Record<string, string> = {
  pending: '等待中',
  processing: '生成中',
  completed: '已完成',
  failed: '失败',
}

const voiceSourceText: Record<string, string> = {
  ai: 'AI 配音',
  upload: '上传音频',
  record: '浏览器录音',
}

const voiceLabelMap: Record<string, string> = {
  longshuo_v3: '稳重男声',
  longanyang: '阳光男声',
  longanhuan: '元气女声',
  longxiaochun_v2: '知性女声',
  longsanshu: '温暖男声',
  longanlang: '清爽男声',
}

const stageRules = [
  { key: 'script', title: '脚本生成', match: ['脚本生成完成'] },
  { key: 'image', title: '图片生成', match: ['图像生成中'] },
  { key: 'audio', title: '配音处理', match: ['配音生成中', '已使用用户音频', '音轨合成完成'] },
  { key: 'video', title: '视频合成', match: ['视频片段合成中', '视频拼接完成', '火柴人视频生成完成'] },
]

export default function StickmanProjectTask() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [task, setTask] = useState<Task | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [progress, setProgress] = useState(0)
  const [messageText, setMessageText] = useState('等待开始')
  const [downloading, setDownloading] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  const taskLog = task?.log || ''
  const stageItems = stageRules.map((stage, index) => {
    const hit = stage.match.some((text) => taskLog.includes(text))
    const isCurrent = !hit && progress > index * 25 && progress < 100
    return {
      title: stage.title,
      status: task?.status === 'failed' && isCurrent ? 'error' as const : hit ? 'finish' as const : isCurrent ? 'process' as const : 'wait' as const,
    }
  })

  const fetchProject = async () => {
    const { data } = await projectApi.get(Number(id))
    setProject(data)
  }

  const fetchTask = async () => {
    try {
      const { data } = await projectApi.getTask(Number(id))
      if (!data) {
        setTask(null)
        setProgress(0)
        setMessageText('尚未开始生成')
        return
      }
      setTask(data)
      setProgress(data.progress || 0)
      if (data.status === 'completed') {
        setMessageText('视频已生成完成')
      }
    } catch (error: any) {
      if (error.response?.status !== 404) {
        throw error
      }
    }
  }

  useEffect(() => {
    const load = async () => {
      try {
        await fetchProject()
      } catch (error) {
        message.error('加载项目失败')
      }
      try {
        await fetchTask()
      } catch (error) {
        message.error('读取任务状态失败')
      } finally {
        setLoading(false)
      }
    }
    load()
    return () => abortControllerRef.current?.abort()
  }, [id])

  const handleGenerate = async () => {
    setGenerating(true)
    setProgress(3)
    setMessageText('正在连接生成服务...')
    abortControllerRef.current = new AbortController()

    try {
      const token = useAuthStore.getState().token
      const response = await fetch(projectApi.generateStickmanStream(Number(id)), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        signal: abortControllerRef.current.signal,
      })

      if (!response.ok) {
        throw new Error('启动火柴人视频任务失败')
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) {
        throw new Error('无法读取服务端响应')
      }

      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6)
          if (!raw.trim()) continue

          const parsed = JSON.parse(raw)
          if (parsed.type === 'progress') {
            setProgress(parsed.progress || 0)
            setMessageText(parsed.content || '生成中')
          }
          if (parsed.type === 'success') {
            setProgress(100)
            setMessageText(parsed.content || '生成完成')
            message.success('火柴人视频生成完成')
          }
          if (parsed.type === 'error') {
            throw new Error(parsed.content || '生成失败')
          }
        }
      }

      await Promise.all([fetchProject(), fetchTask()])
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        message.error(error.message || '生成失败')
        setMessageText(error.message || '生成失败')
      }
    } finally {
      setGenerating(false)
    }
  }

  const handleDownload = async () => {
    const videoUrl = task?.video_url || project?.video_url
    if (!videoUrl) return

    setDownloading(true)
    try {
      const token = useAuthStore.getState().token
      const fullUrl = videoUrl.startsWith('http') ? videoUrl : `${import.meta.env.VITE_API_BASE_URL || ''}${videoUrl}`
      const response = await fetch(fullUrl, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!response.ok) throw new Error('下载失败')
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `stickman_${id}_${Date.now()}.mp4`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      message.success('下载成功')
    } catch (error) {
      message.error('下载失败')
    } finally {
      setDownloading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto p-6">
      <Card
        title={project?.title || '火柴人视频任务'}
        extra={<Space><Button onClick={() => navigate(`/project/${id}/stickman`)}>分步创作</Button><Button onClick={() => navigate('/creator')}>返回创作首页</Button></Space>}
      >
        <div className="space-y-6">
          <Alert
            type="info"
            message="火柴人模块第一版"
            description="当前流程直接根据主题与分镜数生成脚本、图片、配音并合成视频，不进入聊天打磨。"
          />

          {(() => {
            try {
              const flags = JSON.parse(project?.generation_flags || '{}')
              if (flags.image_fallback_used) {
                return (
                  <Alert
                    type="warning"
                    message="本次图片生成包含降级占位图"
                    description={flags.scene_1_error || '当前开发环境图片模型可能因额度或权限问题未能全部真实出图，建议进入分步创作页检查并单张重生。'}
                  />
                )
              }
            } catch {
              return null
            }
            return null
          })()}

            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="生成模块">火柴人视频</Descriptions.Item>
              <Descriptions.Item label="视频主题">{project?.theme}</Descriptions.Item>
              <Descriptions.Item label="视频比例">{project?.aspect_ratio || '16:9'}</Descriptions.Item>
              <Descriptions.Item label="分镜数量">{project?.storyboard_count || 3}</Descriptions.Item>
              <Descriptions.Item label="配音来源">
                <Tag color={project?.voice_source === 'ai' ? 'blue' : 'orange'}>
                  {voiceSourceText[project?.voice_source || 'ai'] || 'AI 配音'}
                </Tag>
              </Descriptions.Item>
              {project?.voice_source === 'ai' && (
                <Descriptions.Item label="AI 音色">{voiceLabelMap[project?.tts_voice || ''] || project?.tts_voice || '默认'}</Descriptions.Item>
              )}
              <Descriptions.Item label="参考音频时长">
                {project?.voice_duration ? `${(project.voice_duration / 1000).toFixed(1)} 秒` : '自动生成'}
              </Descriptions.Item>
              <Descriptions.Item label="任务状态">{taskStatusText[task?.status || project?.status || 'pending'] || '未开始'}</Descriptions.Item>
            </Descriptions>

          <Card size="small" title="阶段进度">
            <Steps direction="vertical" size="small" items={stageItems} />
          </Card>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium">任务进度</span>
              <span className="text-sm text-gray-500">{progress}%</span>
            </div>
            <Progress
              percent={progress}
              status={task?.status === 'failed' ? 'exception' : progress >= 100 ? 'success' : 'active'}
              strokeColor={{ '0%': '#ef8f41', '100%': '#d15c3d' }}
            />
            <div className="text-sm text-gray-500 mt-2">{messageText}</div>
            {task?.error_message && <div className="text-red-500 mt-2 text-sm">{task.error_message}</div>}
            {!!taskLog && (
              <div className="text-xs text-gray-400 mt-3 whitespace-pre-wrap bg-gray-50 rounded-lg p-3 border border-gray-100">
                {taskLog.trim()}
              </div>
            )}
          </div>

          <div className="flex gap-3 flex-wrap">
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleGenerate}
              loading={generating}
              className="btn-gradient-warm"
              size="large"
            >
              {project?.video_url ? '重新生成火柴人视频' : '开始生成火柴人视频'}
            </Button>

            {project?.video_url && (
              <Button
                icon={<DownloadOutlined />}
                onClick={handleDownload}
                loading={downloading}
                size="large"
              >
                下载视频
              </Button>
            )}
          </div>

          {project?.video_url && (
            <video
              src={project.video_url.startsWith('http') ? project.video_url : `${import.meta.env.VITE_API_BASE_URL || ''}${project.video_url}`}
              controls
              className="w-full rounded-xl shadow-lg"
              style={{ maxHeight: '60vh' }}
            >
              您的浏览器不支持视频播放
            </video>
          )}
        </div>
      </Card>
    </div>
  )
}
