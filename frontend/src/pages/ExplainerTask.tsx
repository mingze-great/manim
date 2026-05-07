import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Descriptions, Progress, Spin, Steps, Tag, message } from 'antd'
import { ArrowLeftOutlined, DownloadOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { Project, Task, projectApi } from '@/services/project'
import { resolveBackendUrl } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'
import './Creator/Creator.css'

const taskStatusText: Record<string, string> = {
  pending: '等待中',
  processing: '生成中',
  completed: '已完成',
  failed: '失败',
}

const stageRules = [
  { key: 'hook', title: '开头钩子', match: ['脚本生成完成', '开头'] },
  { key: 'image', title: '分镜出图', match: ['场景图生成中', '图像生成中'] },
  { key: 'audio', title: '配音字幕', match: ['配音生成中', '时间轴计算完成'] },
  { key: 'video', title: '视频合成', match: ['视频片段合成中', '视频拼接完成', '讲解型视频生成完成'] },
]

export default function ExplainerTask() {
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
      setTask(data)
      setProgress(data.progress || 0)
      if (data.status === 'completed') setMessageText('视频已生成完成')
    } catch (error: any) {
      if (error.response?.status !== 404) throw error
      setTask(null)
    }
  }

  useEffect(() => {
    const load = async () => {
      try {
        await Promise.all([fetchProject(), fetchTask()])
      } catch {
        message.error('加载讲解型视频任务页失败')
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
      const response = await fetch(projectApi.generateExplainerStream(Number(id)), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        signal: abortControllerRef.current.signal,
      })
      if (!response.ok) throw new Error('启动讲解型视频任务失败')
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) throw new Error('无法读取服务端响应')
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const parsed = JSON.parse(line.slice(6))
          if (parsed.type === 'progress') {
            setProgress(parsed.progress || 0)
            setMessageText(parsed.content || '生成中')
          }
          if (parsed.type === 'success') {
            setProgress(100)
            setMessageText(parsed.content || '生成完成')
            message.success('讲解型视频生成完成')
          }
          if (parsed.type === 'error') throw new Error(parsed.content || '生成失败')
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
      const response = await fetch(projectApi.getVideoDownloadUrl(Number(id)), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        redirect: 'follow',
      })
      if (!response.ok) throw new Error('下载失败')
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `explainer_${id}_${Date.now()}.mp4`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      message.success('下载成功')
    } catch {
      message.error('下载失败')
    } finally {
      setDownloading(false)
    }
  }

  if (loading) return <div className="flex items-center justify-center h-64"><Spin size="large" /></div>

  return (
    <div className="creator-page">
      <div className="creator-hero creator-hero-sunrise">
        <div className="hero-content">
          <h1 className="hero-title">讲解型视频生成页面</h1>
          <p className="hero-subtitle">这里可以查看当前生成进度、结果视频，并在需要时返回继续编辑。</p>
        </div>
      </div>

      <div className="creator-container space-y-6">
        <div className="flex gap-3 flex-wrap">
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/creator/stickman')}>返回视频讲解</Button>
          <Button onClick={() => navigate(`/project/${id}/explainer`)}>分步创作</Button>
          <Button onClick={() => navigate('/creator/explainer')}>新建讲解视频</Button>
        </div>

        <Alert type="success" message="讲解型视频生成中" description="当前会按已确认内容依次生成分镜、画面和视频。" className="mb-4" />
        <Card className="stickman-panel" bordered={false} title={project?.title || '讲解型视频任务'}>
        <div className="space-y-6">
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="生成模块">讲解型视频</Descriptions.Item>
            <Descriptions.Item label="视频主题">{project?.theme}</Descriptions.Item>
            <Descriptions.Item label="视频比例">{project?.aspect_ratio || '16:9'}</Descriptions.Item>
            <Descriptions.Item label="分镜数量">{project?.storyboard_count || 10}</Descriptions.Item>
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
            <Progress percent={progress} status={task?.status === 'failed' ? 'exception' : progress >= 100 ? 'success' : 'active'} strokeColor={{ '0%': '#2563eb', '100%': '#1d4ed8' }} />
            <div className="text-sm text-gray-500 mt-2">{messageText}</div>
            {task?.error_message && <div className="text-red-500 mt-2 text-sm">{task.error_message}</div>}
            {!!taskLog && <div className="text-xs text-gray-400 mt-3 whitespace-pre-wrap bg-gray-50 rounded-lg p-3 border border-gray-100">{taskLog.trim()}</div>}
          </div>

          <div className="flex gap-3 flex-wrap">
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleGenerate} loading={generating} className="btn-gradient-warm" size="large">
              {project?.video_url ? '重新生成讲解型视频' : '开始生成讲解型视频'}
            </Button>
            {project?.video_url && <Button icon={<DownloadOutlined />} onClick={handleDownload} loading={downloading} size="large">下载视频</Button>}
            <Tag color="red">重点复看前 3 秒钩子是否够强</Tag>
          </div>

          {project?.video_url && (
            <video src={resolveBackendUrl(project.video_url)} controls className="w-full rounded-xl shadow-lg" style={{ maxHeight: '60vh' }}>
              您的浏览器不支持视频播放
            </video>
          )}
        </div>
        </Card>
      </div>
    </div>
  )
}
