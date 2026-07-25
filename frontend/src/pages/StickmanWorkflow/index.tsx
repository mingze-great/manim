import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Collapse, Input, InputNumber, Progress, Radio, Select, Space, Typography, Upload, message } from 'antd'
import { DownloadOutlined, FolderOpenOutlined, PlayCircleOutlined, RocketOutlined, SoundOutlined, UploadOutlined } from '@ant-design/icons'
import { resolveBackendUrl } from '@/services/api'
import { stickmanWorkflowApi } from '@/services/stickmanWorkflow'
import type { StickmanWorkflowConfig } from '@/services/stickmanWorkflow'
import type { StickmanWorkflowDurationEstimate } from '@/services/stickmanWorkflow'
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
  const [scriptMode, setScriptMode] = useState<'ai' | 'custom'>('ai')
  const [customScript, setCustomScript] = useState('')
  const [targetSeconds, setTargetSeconds] = useState<number | undefined>(undefined)
  const [imageMode, setImageMode] = useState<'material_only' | 'ai_image' | 'hybrid'>('material_only')
  const [backgroundMode, setBackgroundMode] = useState('default')
  const [backgroundTemplate, setBackgroundTemplate] = useState('default')
  const [uploadedBackgroundUrl, setUploadedBackgroundUrl] = useState('')
  const [config, setConfig] = useState<StickmanWorkflowConfig | null>(null)
  const [job, setJob] = useState<AiVideoJob | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [uploadingBackground, setUploadingBackground] = useState(false)
  const [durationEstimate, setDurationEstimate] = useState<StickmanWorkflowDurationEstimate | null>(null)
  const [estimatingDuration, setEstimatingDuration] = useState(false)

  const outputUrl = useMemo(() => resolveBackendUrl(job?.outputUrl), [job?.outputUrl])
  const currentStep = useMemo(
    () => progressSteps.slice().reverse().find((step) => job ? job.progress >= step.at || job.status === step.key : false) || progressSteps[0],
    [job],
  )

  useEffect(() => {
    stickmanWorkflowApi.getConfig()
      .then(({ data }) => {
        setConfig(data)
        setVoiceId(data.defaults.voiceId || 'dayun_manbo')
        setMaterialLibrary(data.defaults.materialLibrary || 'sc1_outputs')
        setImageMode(data.capabilities.canUseAiImages ? (data.defaults.imageMode || 'material_only') as 'material_only' | 'ai_image' | 'hybrid' : 'material_only')
        setBackgroundTemplate(data.backgroundTemplates?.[0]?.key || 'default')
      })
      .catch(() => message.error('加载火柴人配置失败'))
  }, [])

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

  useEffect(() => {
    const script = customScript.trim()
    if (scriptMode !== 'custom' || !script) {
      setDurationEstimate(null)
      setEstimatingDuration(false)
      return
    }

    let active = true
    setEstimatingDuration(true)
    const timer = window.setTimeout(async () => {
      try {
        const { data } = await stickmanWorkflowApi.estimateDuration(script)
        if (active) setDurationEstimate(data)
      } catch {
        if (active) setDurationEstimate(null)
      } finally {
        if (active) setEstimatingDuration(false)
      }
    }, 450)

    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [customScript, scriptMode])

  const createVideo = async () => {
    const cleanTitle = title.trim()
    const cleanScript = customScript.trim()
    if (cleanTitle.length < 2) {
      message.warning('请输入一个更具体的主题')
      return
    }
    if (scriptMode === 'custom' && cleanScript.length < 10) {
      message.warning('自定义文案至少输入 10 个字')
      return
    }
    setSubmitting(true)
    setJob(null)
    try {
      if (backgroundMode === 'upload' && !uploadedBackgroundUrl) {
        message.warning('请先上传背景图，或切换为默认/模板背景')
        return
      }
      const { data } = await stickmanWorkflowApi.createJob({
        title: cleanTitle,
        voiceId,
        materialLibrary,
        tone: 'sharp',
        pace: 'medium',
        targetPlatform: 'douyin',
        scriptMode,
        customScript: scriptMode === 'custom' ? cleanScript : undefined,
        targetSeconds: scriptMode === 'ai' ? targetSeconds : undefined,
        imageMode,
        backgroundMode,
        backgroundTemplate: backgroundMode === 'template' ? backgroundTemplate : undefined,
        uploadedBackgroundUrl: backgroundMode === 'upload' ? uploadedBackgroundUrl : undefined,
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

  const uploadBackground = async (file: File) => {
    setUploadingBackground(true)
    try {
      const { data } = await stickmanWorkflowApi.uploadBackground(file)
      setUploadedBackgroundUrl(data.url)
      setBackgroundMode('upload')
      message.success('背景图已上传')
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '上传背景图失败')
    } finally {
      setUploadingBackground(false)
    }
    return false
  }

  const maxVideoSeconds = config?.capabilities.maxVideoSeconds || 60
  const materialOptions = (config?.materialLibraries || [{ key: 'sc1_outputs', name: 'SC1 火柴人素材库' }]).map((item) => ({
    label: `${item.name}${item.material_count ? ` · ${item.material_count}条` : ''}`,
    value: item.key,
  }))
  const voiceOptions = (config?.voices || [{ label: '曼波参考音色', value: 'dayun_manbo' }]).map((item) => ({ label: item.label, value: item.value }))
  const backgroundTemplateOptions = (config?.backgroundTemplates || [{ key: 'default', name: '默认白纸' }]).map((item) => ({
    label: item.description ? `${item.name} · ${item.description}` : item.name,
    value: item.key,
  }))
  const imageModeOptions = [
    { label: '素材库匹配', value: 'material_only' },
    ...(config?.capabilities.canUseAiImages ? [
      { label: '实时生图', value: 'ai_image' },
      { label: '混合补图', value: 'hybrid' },
    ] : []),
  ]

  return (
    <div className="stickman-workflow-page">
      <div className="stickman-workflow-header">
        <div>
          <Typography.Title level={2}>火柴人工作流</Typography.Title>
          <Typography.Paragraph>
            默认输入一个主题即可生成成片；高级选项支持自定义文案、时长、背景和素材库控制。
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
            rows={4}
            maxLength={120}
            showCount
            placeholder="例如：为什么你总是在关系里想太多"
          />

          <Collapse
            className="workflow-advanced"
            items={[{
              key: 'advanced',
              label: '高级控制',
              children: (
                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                  <label className="workflow-field">
                    <span>生成方式</span>
                    <Radio.Group
                      value={scriptMode}
                      onChange={(event) => {
                        setScriptMode(event.target.value)
                        if (event.target.value === 'custom') setTargetSeconds(undefined)
                      }}
                      optionType="button"
                      buttonStyle="solid"
                      options={[
                        { label: 'AI 按标题生成', value: 'ai' },
                        { label: '使用自定义文案', value: 'custom' },
                      ]}
                    />
                  </label>

                  {scriptMode === 'custom' ? (
                    <label className="workflow-field">
                      <span>自定义文案</span>
                      <TextArea
                        value={customScript}
                        onChange={(event) => setCustomScript(event.target.value)}
                        rows={6}
                        maxLength={1200}
                        showCount
                        placeholder="粘贴完整口播文案。系统会根据配音实际时长同步字幕、场景图和总结关键词。"
                      />
                      <Alert type="info" showIcon message="自定义文案会自动决定视频时长，因此不能同时选择目标时长。" />
                      {estimatingDuration ? (
                        <Typography.Text type="secondary">正在估算配音时长...</Typography.Text>
                      ) : durationEstimate ? (
                        <Alert
                          type={durationEstimate.allowed ? 'success' : 'error'}
                          showIcon
                          message={`预计 ${durationEstimate.estimatedSeconds} 秒，当前套餐上限 ${durationEstimate.maxVideoSeconds} 秒`}
                          description={durationEstimate.allowed ? '最终时长以实际配音为准。' : '请缩短文案后再生成。'}
                        />
                      ) : null}
                    </label>
                  ) : (
                    <label className="workflow-field">
                      <span>目标时长</span>
                      <InputNumber
                        min={15}
                        max={maxVideoSeconds}
                        step={15}
                        value={targetSeconds}
                        onChange={(value) => setTargetSeconds(value || undefined)}
                        addonAfter="秒"
                        placeholder="不限制"
                        style={{ width: '100%' }}
                      />
                    </label>
                  )}

                  <label className="workflow-field">
                    <span>画面模式</span>
                    <Select value={imageMode} onChange={setImageMode} options={imageModeOptions} />
                  </label>

                  <label className="workflow-field">
                    <span>背景模式</span>
                    <Select
                      value={backgroundMode}
                      onChange={(value) => setBackgroundMode(value)}
                      options={[
                        { label: '默认白纸背景', value: 'default' },
                        { label: '后台背景风格', value: 'template' },
                        { label: '用户上传背景', value: 'upload', disabled: config?.capabilities.canUploadBackground === false },
                      ]}
                    />
                  </label>

                  {backgroundMode === 'template' ? (
                    <label className="workflow-field">
                      <span>背景风格</span>
                      <Select value={backgroundTemplate} onChange={setBackgroundTemplate} options={backgroundTemplateOptions} />
                    </label>
                  ) : null}

                  {backgroundMode === 'upload' ? (
                    <label className="workflow-field">
                      <span>上传背景图</span>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Upload beforeUpload={uploadBackground} showUploadList={false} accept=".png,.jpg,.jpeg,.webp">
                          <Button icon={<UploadOutlined />} loading={uploadingBackground}>选择背景图</Button>
                        </Upload>
                        {uploadedBackgroundUrl ? <Typography.Text type="secondary">已上传：{uploadedBackgroundUrl}</Typography.Text> : null}
                      </Space>
                    </label>
                  ) : null}
                </Space>
              ),
            }]}
          />

          <div className="workflow-controls">
            <label>
              <span>声音</span>
              <Select value={voiceId} onChange={setVoiceId} suffixIcon={<SoundOutlined />} options={voiceOptions} />
            </label>
            <label>
              <span>素材库</span>
              <Select value={materialLibrary} onChange={setMaterialLibrary} suffixIcon={<FolderOpenOutlined />} options={materialOptions} />
            </label>
          </div>

          <Button
            type="primary"
            size="large"
            icon={<RocketOutlined />}
            loading={submitting}
            disabled={scriptMode === 'custom' && durationEstimate?.allowed === false}
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
              <Progress percent={job.progress} status={job.status === 'failed' ? 'exception' : job.status === 'completed' ? 'success' : 'active'} />

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
