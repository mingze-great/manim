import { useEffect, useMemo, useState } from 'react'
import { Button, Input, Progress, Select, Space, Typography, message } from 'antd'
import { DownloadOutlined, FolderOpenOutlined, PlayCircleOutlined, RocketOutlined, SoundOutlined } from '@ant-design/icons'
import { resolveBackendUrl } from '@/services/api'
import { stickmanWorkflowApi } from '@/services/stickmanWorkflow'
import type { AiVideoJob } from '@/services/aiVideo'
import './StickmanWorkflow.css'

const { TextArea } = Input

const statusText: Record<string, string> = {
  pending: '任务已创建',
  scripting: '正在生成爆款文案',
  scene_planning: '正在拆分分镜与场景图',
  tts_generating: '正在生成连续配音',
  audio_processing: '正在同步字幕与音频',
  rendering: '正在匹配素材并渲染',
  uploading: '正在保存成片',
  completed: '生成完成',
  failed: '生成失败',
  cancelled: '已取消',
}

const progressSteps = [
  { key: 'pending', label: '创建任务', at: 0, detail: '提交主题并锁定生成参数' },
  { key: 'scripting', label: '生成文案', at: 12, detail: '生成和参考视频同类的口播文案' },
  { key: 'scene_planning', label: '拆分分镜', at: 28, detail: '按语义拆分场景与关键词' },
  { key: 'tts_generating', label: '配音生成', at: 48, detail: '调用声音模型生成连续音频' },
  { key: 'audio_processing', label: '字幕同步', at: 62, detail: '对齐音频、字幕和关键词' },
  { key: 'rendering', label: '画面渲染', at: 82, detail: '合成素材、场景图和转场' },
  { key: 'uploading', label: '输出成片', at: 92, detail: '保存并暴露播放链接' },
  { key: 'completed', label: '完成', at: 100, detail: '可直接预览和下载' },
]

export default function StickmanWorkflow() {
  const [title, setTitle] = useState('为什么你总是在关系里想太多')
  const [voiceId, setVoiceId] = useState('dayun_manbo')
  const [materialLibrary, setMaterialLibrary] = useState('sc1_outputs')
  const [job, setJob] = useState<AiVideoJob | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const outputUrl = useMemo(() => resolveBackendUrl(job?.outputUrl), [job?.outputUrl])
  const currentStep = useMemo(
    () => progressSteps.slice().reverse().find((step) => job ? job.progress >= step.at || job.status === step.key : false) || progressSteps[0],
    [job],
  )

  useEffect(() => {
    if (!job?.jobId || ['completed', 'failed', 'cancelled'].includes(job.status)) return
    const timer = window.setInterval(async () => {
      try {
        const { data } = await stickmanWorkflowApi.getJob(job.jobId)
        setJob(data)
      } catch {
        message.error('无法读取生成进度')
      }
    }, 3000)
    return () => window.clearInterval(timer)
  }, [job?.jobId, job?.status])

  const createVideo = async () => {
    const cleanTitle = title.trim()
    if (cleanTitle.length < 2) {
      message.warning('请输入一个更具体的主题')
      return
    }
    setSubmitting(true)
    setJob(null)
    try {
      const { data } = await stickmanWorkflowApi.createJob({
        title: cleanTitle,
        voiceId,
        materialLibrary,
        tone: 'sharp',
        pace: 'medium',
        targetPlatform: 'douyin',
      })
      const jobRes = await stickmanWorkflowApi.getJob(data.jobId)
      setJob(jobRes.data)
      message.success('火柴人工作流已开始生成')
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '创建任务失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="stickman-workflow-page">
      <div className="stickman-workflow-header">
        <div>
          <Typography.Title level={2}>火柴人工作流</Typography.Title>
          <Typography.Paragraph>
            输入一个主题，系统会自动生成文案、拆分分镜、调用声音模型、同步字幕并渲染成片。
          </Typography.Paragraph>
        </div>
        <div className="workflow-badge">SC1 独立模块</div>
      </div>

      <div className="stickman-workflow-grid">
        <section className="workflow-panel workflow-form-panel">
          <div className="panel-title">主题输入</div>
          <TextArea
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            rows={5}
            maxLength={120}
            showCount
            placeholder="例如：为什么你总是在关系里想太多"
          />

          <div className="workflow-controls">
            <label>
              <span>声音</span>
              <Select
                value={voiceId}
                onChange={setVoiceId}
                suffixIcon={<SoundOutlined />}
                options={[
                  { label: '曼波参考音色', value: 'dayun_manbo' },
                  { label: '中文女', value: '中文女' },
                  { label: '中文男', value: '中文男' },
                ]}
              />
            </label>
            <label>
              <span>素材库</span>
              <Select
                value={materialLibrary}
                onChange={setMaterialLibrary}
                suffixIcon={<FolderOpenOutlined />}
                options={[
                  { label: 'SC1 火柴人素材库', value: 'sc1_outputs' },
                ]}
              />
            </label>
          </div>

          <Button
            type="primary"
            size="large"
            icon={<RocketOutlined />}
            loading={submitting}
            onClick={createVideo}
            block
          >
            生成火柴人成片
          </Button>
        </section>

        <section className="workflow-panel workflow-status-panel">
          <div className="panel-title">生成进度</div>
          {job ? (
            <>
              <div className="job-status-row">
                <span>{statusText[job.status] || job.message || job.status}</span>
                <strong>{job.progress}%</strong>
              </div>
              <Progress
                percent={job.progress}
                status={job.status === 'failed' ? 'exception' : job.status === 'completed' ? 'success' : 'active'}
              />

              <div className="workflow-current-step">
                <span>当前阶段</span>
                <strong>{currentStep.label}</strong>
                <p>{currentStep.detail}</p>
              </div>

              <div className="workflow-step-list">
                {progressSteps.map((step) => {
                  const done = job.progress >= step.at || job.status === 'completed'
                  const active = job.status === step.key
                  return (
                    <div className={`workflow-step ${done ? 'done' : ''} ${active ? 'active' : ''}`} key={step.key}>
                      <span />
                      <strong>{step.label}</strong>
                      <em>{step.detail}</em>
                    </div>
                  )
                })}
              </div>

              {job.errorMessage ? <div className="workflow-error">{job.errorMessage}</div> : null}

              {outputUrl ? (
                <div className="workflow-preview">
                  <video src={outputUrl} controls />
                  <Space>
                    <Button icon={<PlayCircleOutlined />} onClick={() => window.open(outputUrl, '_blank')}>打开成片</Button>
                    <Button icon={<DownloadOutlined />} href={outputUrl}>下载 MP4</Button>
                  </Space>
                </div>
              ) : (
                <div className="workflow-empty">成片完成后会显示预览和下载入口。</div>
              )}
            </>
          ) : (
            <div className="workflow-empty">还没有任务。输入主题后点击生成。</div>
          )}
        </section>
      </div>
    </div>
  )
}
