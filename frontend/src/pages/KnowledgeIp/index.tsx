
import { useEffect, useMemo, useRef, useState } from 'react'
import { Alert, Button, Card, Progress, Space, Steps, Tag, Upload, message } from 'antd'
import type { UploadFile, UploadProps } from 'antd'
import {
  CloudDownloadOutlined,
  DeleteOutlined,
  FileDoneOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  UploadOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons'
import api, { resolveBackendUrl } from '@/services/api'
import './KnowledgeIp.css'

const version = `v=${Date.now()}`
const previewVideoUrl = `/renders/knowledge-ip-preview-bilingual-sync.mp4?${version}`
const sampleVideoUrl = `/renders/knowledge-ip-final-full-bilingual-sync.mp4?${version}`

type JobStatus = 'idle' | 'uploading' | 'uploaded' | 'running' | 'completed' | 'failed'

type StageTiming = {
  started_at?: string
  ended_at?: string
  duration_seconds?: number
  duration_text?: string
}

type KnowledgeJob = {
  id: string
  status: JobStatus
  stage: string
  progress: number
  message: string
  filename?: string
  size?: number
  result_url?: string
  duration_ms?: number
  caption_count?: number
  segment_count?: number
  render_progress?: number
  timing?: {
    elapsed_seconds?: number
    elapsed_text?: string
    stages?: Record<string, StageTiming>
  }
  error?: string
}

const introStages = [
  { title: '生成动态包装', desc: '根据本次字幕分段生成章节、双语字幕和动态图形包装。' },
  { title: '识别讲解内容', desc: '开始生成后提取音频，调用 Paraformer 识别字幕和时间轴。' },
  { title: '生成动态包装', desc: '根据本次字幕分段生成章节、双语字幕和动态图形包装。' },
  { title: '合成发布成片', desc: '使用本次上传的视频渲染输出，不复用固定样片。' },
]

const generateStages = [
  { key: 'extract_audio', title: '提取音频' },
  { key: 'asr', title: '识别字幕' },
  { key: 'analyze', title: '分析结构' },
  { key: 'materials', title: '生成素材' },
  { key: 'render', title: '渲染成片' },
  { key: 'save', title: '保存成片' },
  { key: 'completed', title: '完成' },
]

const formatFileSize = (size?: number) => {
  if (!size) return '等待上传'
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}

const statusLabel = (status: JobStatus) => {
  if (status === 'uploading') return '上传中'
  if (status === 'uploaded') return '已上传'
  if (status === 'running') return '生成中'
  if (status === 'completed') return '已完成'
  if (status === 'failed') return '等待上传'
  return '等待上传'
}

const timingRows = (job?: KnowledgeJob | null) => {
  const stages = job?.timing?.stages || {}
  return generateStages
    .filter(stage => stage.key !== 'completed')
    .map(stage => ({ ...stage, timing: stages[stage.key] }))
    .filter(stage => stage.timing?.duration_text || stage.key === job?.stage)
}

export default function KnowledgeIp() {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [fileUrl, setFileUrl] = useState('')
  const [job, setJob] = useState<KnowledgeJob | null>(null)
  const [status, setStatus] = useState<JobStatus>('idle')
  const pollRef = useRef<number | null>(null)

  const currentFile = fileList[0]
  const progress = job?.progress || 0
  const resultUrl = job?.result_url ? resolveBackendUrl(job.result_url) : ''
  const canStart = Boolean(job?.id) && status !== 'uploading' && status !== 'running' && status !== 'completed'

  const currentStageIndex = useMemo(() => {
    const index = generateStages.findIndex(stage => stage.key === job?.stage)
    return index >= 0 ? index : 0
  }, [job?.stage])

  const stopPolling = () => {
    if (pollRef.current) window.clearInterval(pollRef.current)
    pollRef.current = null
  }

  useEffect(() => () => {
    stopPolling()
    if (fileUrl) URL.revokeObjectURL(fileUrl)
  }, [fileUrl])

  const pollJob = (jobId: string) => {
    stopPolling()
    const fetchJob = async () => {
      try {
        const { data } = await api.get<KnowledgeJob>(`/knowledge-ip/jobs/${jobId}`)
        setJob(data)
        setStatus(data.status)
        if (data.status === 'completed') {
          stopPolling()
          message.success('包装视频已生成，可以预览或下载。')
          window.setTimeout(() => document.getElementById('knowledge-ip-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 150)
        }
        if (data.status === 'failed') {
          stopPolling()
          message.error(data.message || data.error || '生成失败')
        }
      } catch (error: any) {
        stopPolling()
        setStatus('failed')
        setJob(prev => prev ? { ...prev, status: 'failed', message: error?.response?.data?.detail || '获取任务进度失败' } : prev)
      }
    }
    fetchJob()
    pollRef.current = window.setInterval(fetchJob, 2500)
  }

  const uploadToServer = async (file: File) => {
    stopPolling()
    setStatus('uploading')
    setJob(null)
    const form = new FormData()
    form.append('file', file)
    try {
      const { data } = await api.post<KnowledgeJob>('/knowledge-ip/uploads', form, {
        timeout: 10 * 60 * 1000,
      })
      setJob(data)
      setStatus(data.status)
      message.success('视频已上传到服务器，可以开始生成包装视频。')
    } catch (error: any) {
      setStatus('failed')
      const statusCode = error?.response?.status
      const detail =
        statusCode === 413
          ? '视频文件过大，请压缩后重试，或联系管理员开通更大的上传额度。'
          : statusCode === 401
            ? '登录状态已失效，请重新登录后再上传。'
            : error?.response?.data?.detail || '上传失败，请检查视频格式或网络后重试。'
      setJob({ id: '', status: 'failed', stage: 'uploaded', progress: 0, message: detail })
      message.error(detail)
    }
  }

  const uploadProps: UploadProps = {
    accept: 'video/mp4,video/quicktime,video/webm,video/*',
    maxCount: 1,
    fileList,
    beforeUpload: file => {
      if (!file.type.startsWith('video/')) {
        message.error('请上传视频文件，支持 mp4 / mov / webm 等格式。')
        return Upload.LIST_IGNORE
      }
      stopPolling()
      if (fileUrl) URL.revokeObjectURL(fileUrl)
      const nextFile: UploadFile = {
        uid: file.uid,
        name: file.name,
        status: 'done',
        size: file.size,
        type: file.type,
        originFileObj: file,
      }
      setFileList([nextFile])
      setFileUrl(URL.createObjectURL(file))
      uploadToServer(file)
      return false
    },
    onRemove: () => {
      stopPolling()
      if (fileUrl) URL.revokeObjectURL(fileUrl)
      setFileList([])
      setFileUrl('')
      setJob(null)
      setStatus('idle')
      return true
    },
  }

  const startGenerate = async () => {
    if (!job?.id) {
      message.warning('请先上传真人讲解视频')
      return
    }
    try {
      setStatus('running')
      const { data } = await api.post<KnowledgeJob>(`/knowledge-ip/jobs/${job.id}/start`, {}, { timeout: 60000 })
      setJob(data)
      pollJob(job.id)
      message.info('已开始生成，当前进入视频包装流程。')
    } catch (error: any) {
      const detail = error?.response?.data?.detail || '请重新上传视频或稍后重试。'
      setStatus('failed')
      setJob(prev => prev ? { ...prev, status: 'failed', message: detail } : prev)
      message.error(detail)
    }
  }

  const resetJob = () => {
    stopPolling()
    setStatus(job?.id ? 'uploaded' : 'idle')
    if (job?.id) setJob({ ...job, status: 'uploaded', stage: 'uploaded', progress: 0, message: '请重新上传视频或稍后重试。' })
  }

  return (
    <div className="knowledge-ip-page">
      <section className="knowledge-hero">
        <div>
          <Tag className="hero-tag">Knowledge IP Workflow</Tag>
          <h1>知识IP自动包装</h1>
          <p>上传真人讲解视频，系统按本次视频识别字幕、分析结构、生成动态包装并渲染成片。不会复用固定样片。</p>
          <Space wrap>
            <Upload {...uploadProps}>
              <Button type="primary" size="large" icon={<UploadOutlined />} loading={status === 'uploading'}>上传真人视频</Button>
            </Upload>
            <Button size="large" type="primary" ghost icon={<ThunderboltOutlined />} disabled={!canStart} loading={status === 'running'} onClick={startGenerate}>开始生成包装视频</Button>
            {resultUrl && <Button size="large" icon={<PlayCircleOutlined />} onClick={() => window.open(resultUrl, '_blank')}>查看本次成片</Button>}
          </Space>
          {job?.filename && (
            <div className="upload-note success"><FileDoneOutlined /> 上传完成：{job.filename} · {formatFileSize(job.size)}</div>
          )}
        </div>
        <div className="hero-panel">
          <video src={previewVideoUrl} controls poster="/renders/knowledge-ip-final-checks/full_4s.png" />
          <div className="panel-caption"><strong>案例预览</strong><span>只用于展示效果，生成结果以本次上传任务为准</span></div>
        </div>
      </section>

      <section className="workflow-grid">
        {introStages.map((stage, index) => (
          <Card key={stage.title} className="workflow-step"><span className="step-index">0{index + 1}</span><h3>{stage.title}</h3><p>{stage.desc}</p></Card>
        ))}
      </section>

      <section className="upload-section">
        <Card className="upload-card">
          <div className="upload-card-main">
            <div>
              <Tag color={status === 'uploading' ? 'blue' : job?.id ? 'green' : 'default'}>{statusLabel(status)}</Tag>
              <h2>真人视频</h2>
              <p>点击上传后会直接保存到服务器。上传完成以后，再点击“开始生成包装视频”。</p>
              {currentFile && <div className="file-meta"><span>{currentFile.name}</span><span>{formatFileSize(currentFile.size)}</span><Button size="small" icon={<DeleteOutlined />} onClick={() => uploadProps.onRemove?.(currentFile)}>重新上传</Button></div>}
            </div>
            <Upload {...uploadProps}><Button icon={<UploadOutlined />} loading={status === 'uploading'}>{currentFile ? '更换视频' : '选择视频'}</Button></Upload>
          </div>
          {fileUrl && <video className="local-preview" src={fileUrl} controls />}
        </Card>
      </section>

      <section className="generate-section">
        <Card className={`generate-card status-${status}`}>
          <div className="generate-header">
            <div>
              <Tag color={status === 'failed' ? 'red' : status === 'completed' ? 'green' : job?.id ? 'blue' : 'default'}>{statusLabel(status)}</Tag>
              <h2>生成流程</h2>
              <p>{job?.message || '请先上传真人讲解视频'}</p>
            </div>
            <Progress type="circle" percent={progress} size={86} status={status === 'failed' ? 'exception' : status === 'completed' ? 'success' : 'active'} />
          </div>
          <Progress percent={progress} status={status === 'failed' ? 'exception' : status === 'completed' ? 'success' : 'active'} />
          <Steps className="generate-steps" current={currentStageIndex} status={status === 'failed' ? 'error' : status === 'completed' ? 'finish' : 'process'} items={generateStages.map(stage => ({ title: stage.title }))} />
          {status === 'failed' && <Alert className="generate-alert" type="error" showIcon message="生成遇到问题" description={job?.message || job?.error || '请重新上传视频或稍后重试。'} />}
          {status === 'running' && <Alert className="generate-alert" type="info" showIcon message="正在生成中" description={`长视频会更慢，请不要重复点击。当前任务已用时：${job?.timing?.elapsed_text || '统计中'}。`} />}
          {(job?.timing?.elapsed_text || timingRows(job).length > 0) && (
            <div className="timing-panel">
              <div className="timing-total"><span>当前任务用时</span><strong>{job?.timing?.elapsed_text || '统计中'}</strong></div>
              <div className="timing-grid">
                {timingRows(job).map(stage => (
                  <div className="timing-item" key={stage.key}>
                    <span>{stage.title}</span>
                    <strong>{stage.timing?.duration_text || (stage.key === job?.stage ? '进行中' : '-')}</strong>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="generate-actions">
            <Button type="primary" size="large" icon={<ThunderboltOutlined />} disabled={!canStart} loading={status === 'running'} onClick={startGenerate}>{status === 'failed' ? '重新生成包装视频' : '开始生成包装视频'}</Button>
            <Button size="large" icon={<ReloadOutlined />} disabled={!job?.id || status === 'running'} onClick={resetJob}>重置流程</Button>
            {resultUrl && <><Button size="large" icon={<PlayCircleOutlined />} onClick={() => window.open(resultUrl, '_blank')}>预览成片</Button><Button size="large" icon={<CloudDownloadOutlined />} href={resultUrl} target="_blank">下载成片</Button></>}
          </div>
        </Card>
      </section>

      <section className="result-section" id="knowledge-ip-result">
        <Card className="result-card">
          <div className="result-heading">
            <div>
              <Tag color={resultUrl ? 'green' : 'default'}>{resultUrl ? '本次任务结果' : '等待生成'}</Tag>
              <h2>{resultUrl ? '本次成片已生成' : '生成完成后这里会出现成片'}</h2>
              <p>{resultUrl ? `已根据本次上传视频生成：${job?.caption_count || 0} 条字幕，${job?.segment_count || 0} 个内容分段。总耗时：${job?.timing?.elapsed_text || '已完成'}。` : '示例视频只用于展示版式，真实下载入口只会在本次任务完成后出现。'}</p>
            </div>
            <Progress type="circle" percent={resultUrl ? 100 : progress} size={86} />
          </div>
          {resultUrl && (
            <div className="result-preview">
              <video key={resultUrl} src={resultUrl} controls playsInline preload="metadata" />
            </div>
          )}
          <div className="result-actions">
            {resultUrl ? <><Button type="primary" icon={<VideoCameraOutlined />} onClick={() => document.querySelector<HTMLVideoElement>('.result-preview video')?.play()}>播放预览</Button><Button icon={<PlayCircleOutlined />} onClick={() => window.open(resultUrl, '_blank')}>新窗口打开</Button><Button icon={<CloudDownloadOutlined />} href={resultUrl} target="_blank">下载本次视频</Button></> : <Button icon={<PlayCircleOutlined />} onClick={() => window.open(sampleVideoUrl, '_blank')}>查看效果案例</Button>}
          </div>
        </Card>
      </section>
    </div>
  )
}
