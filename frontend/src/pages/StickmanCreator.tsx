import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Divider, Input, InputNumber, Select, Typography, Upload, message } from 'antd'
import { ArrowLeftOutlined, AudioOutlined, BulbOutlined, UploadOutlined, VideoCameraOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { projectApi, StickmanVoiceOption } from '@/services/project'
import TopicCategorySelector from './Creator/components/TopicCategorySelector'
import TopicExamples from './Creator/components/TopicExamples'
import AudioRecorder from './Creator/components/AudioRecorder'
import { VideoTopicCategory } from '@/services/videoTopic'
import './Creator/Creator.css'

const { TextArea } = Input

type VoiceSource = 'ai' | 'record' | 'upload'
type GenerationMode = 'one_click' | 'step_by_step'
type StickmanVariant = 'legacy' | 'v2'
type ScriptMode = 'ai' | 'custom'

const defaultStickmanVoiceOptions: StickmanVoiceOption[] = [
  { label: '稳重男声', value: 'longshuo_v3', provider: 'dashscope_cosyvoice', gender: 'male', style: 'steady' },
  { label: '阳光男声', value: 'longanyang', provider: 'dashscope_cosyvoice', gender: 'male', style: 'bright' },
  { label: '温暖男声', value: 'longsanshu', provider: 'dashscope_cosyvoice', gender: 'male', style: 'warm' },
  { label: '清爽男声', value: 'longanlang', provider: 'dashscope_cosyvoice', gender: 'male', style: 'clean' },
  { label: '元气女声', value: 'longanhuan', provider: 'dashscope_cosyvoice', gender: 'female', style: 'energetic' },
  { label: '知性女声', value: 'longxiaochun_v2', provider: 'dashscope_cosyvoice', gender: 'female', style: 'intellectual' },
  { label: '平和女声', value: 'longanwen', provider: 'dashscope_cosyvoice', gender: 'female', style: 'calm' },
  { label: '理性播报男声', value: 'sambert-zhiming-v1', provider: 'dashscope_sambert', gender: 'male', style: 'rational' },
  { label: '治愈陪伴女声', value: 'sambert-zhiya-v1', provider: 'dashscope_sambert', gender: 'female', style: 'healing' },
  { label: '激励主播男声', value: 'sambert-zhihao-v1', provider: 'dashscope_sambert', gender: 'male', style: 'motivational' },
]

function normalizeVoiceOptions(input: unknown): StickmanVoiceOption[] {
  if (!Array.isArray(input)) return defaultStickmanVoiceOptions
  const normalized = input
    .map((item: any) => ({
      label: typeof item?.label === 'string' && item.label.trim() ? item.label : String(item?.value || ''),
      value: typeof item?.value === 'string' ? item.value : '',
      provider: typeof item?.provider === 'string' && item.provider ? item.provider : 'dashscope_cosyvoice',
      gender: typeof item?.gender === 'string' ? item.gender : undefined,
      style: typeof item?.style === 'string' ? item.style : undefined,
    }))
    .filter((item) => item.value)

  return normalized.length ? normalized : defaultStickmanVoiceOptions
}

export default function StickmanCreator() {
  const navigate = useNavigate()
  const { variant } = useParams<{ variant: string }>()
  const stickmanVariant: StickmanVariant = variant === 'v2' ? 'v2' : 'legacy'
  const user = useAuthStore((state) => state.user)
  const [loading, setLoading] = useState(false)
  const [selectedStickmanCategory, setSelectedStickmanCategory] = useState<VideoTopicCategory | null>(null)
  const [scriptMode, setScriptMode] = useState<ScriptMode>('ai')
  const [stickmanTopic, setStickmanTopic] = useState('')
  const [customScript, setCustomScript] = useState('')
  const [storyboardCount, setStoryboardCount] = useState(3)
  const [voiceSource, setVoiceSource] = useState<VoiceSource>('ai')
  const [ttsVoice, setTtsVoice] = useState('longshuo_v3')
  const [ttsRate, setTtsRate] = useState('+0%')
  const [voiceLibrary, setVoiceLibrary] = useState<StickmanVoiceOption[]>(defaultStickmanVoiceOptions)
  const [customVoiceLabel, setCustomVoiceLabel] = useState('')
  const [generationMode, setGenerationMode] = useState<GenerationMode>('one_click')
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null)
  const [styleImageFile, setStyleImageFile] = useState<File | null>(null)
  const [styleImagePreviewUrl, setStyleImagePreviewUrl] = useState<string | null>(null)
  const [styleNotes, setStyleNotes] = useState('')
  const [backgroundImageFile, setBackgroundImageFile] = useState<File | null>(null)
  const [backgroundImagePreviewUrl, setBackgroundImagePreviewUrl] = useState<string | null>(null)

  const permissions = user?.module_permissions || {}
  const stickmanEnabled = user?.is_admin || permissions.stickman?.enabled !== false
  const stickmanStoryboardMax = user?.is_admin ? 20 : 6
  const safeVoiceOptions = useMemo(() => normalizeVoiceOptions(voiceLibrary), [voiceLibrary])

  useEffect(() => {
    const loadVoices = async () => {
      try {
        const { data } = await projectApi.getStickmanVoiceLibrary()
        setVoiceLibrary(normalizeVoiceOptions(data.voices))
      } catch {
        setVoiceLibrary(defaultStickmanVoiceOptions)
      }
    }
    loadVoices()
  }, [])

  useEffect(() => {
    if (!safeVoiceOptions.length) return
    if (!safeVoiceOptions.some((item) => item.value === ttsVoice)) {
      setTtsVoice(safeVoiceOptions[0].value)
    }
  }, [safeVoiceOptions, ttsVoice])

  useEffect(() => () => {
    if (audioPreviewUrl) URL.revokeObjectURL(audioPreviewUrl)
    if (styleImagePreviewUrl) URL.revokeObjectURL(styleImagePreviewUrl)
    if (backgroundImagePreviewUrl) URL.revokeObjectURL(backgroundImagePreviewUrl)
  }, [audioPreviewUrl, styleImagePreviewUrl, backgroundImagePreviewUrl])

  const updateAudioFile = (file: File | null) => {
    setAudioFile(file)
    setAudioPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return file ? URL.createObjectURL(file) : null
    })
  }

  const updateStyleImageFile = (file: File | null) => {
    setStyleImageFile(file)
    setStyleImagePreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return file ? URL.createObjectURL(file) : null
    })
  }

  const updateBackgroundImageFile = (file: File | null) => {
    setBackgroundImageFile(file)
    setBackgroundImagePreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return file ? URL.createObjectURL(file) : null
    })
  }

  const handleStickmanCategorySelect = (category: VideoTopicCategory) => {
    setSelectedStickmanCategory(category)
    setStickmanTopic(category.example_topics?.[0] || '')
  }

  const handleCreateCustomVoice = async () => {
    if (!audioFile) {
      message.warning('请先录音或上传一段声音样本')
      return
    }
    if (!customVoiceLabel.trim()) {
      message.warning('请输入自定义音色名称')
      return
    }
    setLoading(true)
    try {
      const { data } = await projectApi.createCustomStickmanVoice(audioFile, customVoiceLabel.trim())
      setVoiceLibrary((prev) => [...prev, data.voice])
      setTtsVoice(data.voice.value)
      message.success('自定义音色已创建并加入音色库')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '创建自定义音色失败')
    } finally {
      setLoading(false)
    }
  }

  const handleStickmanCreate = async () => {
    if (!stickmanEnabled) {
      message.warning('当前账号未开通火柴人视频模块，请联系管理员开通')
      return
    }
    if (scriptMode === 'ai' && !stickmanTopic.trim()) {
      message.warning('请输入火柴人视频主题')
      return
    }
    if (scriptMode === 'custom' && !customScript.trim()) {
      message.warning('请输入完整文案')
      return
    }
    if (voiceSource !== 'ai' && !audioFile) {
      message.warning('请先录音或上传音频文件')
      return
    }

    const selectedVoice = safeVoiceOptions.find((item) => item.value === ttsVoice)
    const resolvedTheme = scriptMode === 'custom'
      ? (stickmanTopic.trim() || customScript.trim().split(/\r?\n/)[0]?.slice(0, 24) || '火柴人视频')
      : stickmanTopic.trim()
    setLoading(true)
    try {
      const { data } = await projectApi.create({
        title: `火柴人视频-${resolvedTheme}`,
        theme: resolvedTheme,
        module_type: 'stickman',
        stickman_variant: stickmanVariant,
        storyboard_count: storyboardCount,
        aspect_ratio: '16:9',
        generation_mode: generationMode,
        voice_source: voiceSource,
        tts_provider: selectedVoice?.provider || 'dashscope_cosyvoice',
        tts_voice: ttsVoice,
        tts_rate: ttsRate,
      })

      if (audioFile && voiceSource !== 'ai') {
        await projectApi.uploadVoiceReference(data.id, audioFile, voiceSource)
      }
      if (backgroundImageFile) {
        await projectApi.uploadBackgroundImage(data.id, backgroundImageFile)
      }
      if (styleImageFile) {
        await projectApi.uploadStyleReference(data.id, styleImageFile, styleNotes || undefined)
      }
      if (scriptMode === 'custom') {
        await projectApi.useCustomScript(data.id, customScript, false)
      }

      message.success('创建成功')
      navigate(generationMode === 'step_by_step' ? `/project/${data.id}/stickman` : `/project/${data.id}/task`)
    } catch (error: any) {
      const detail = error.response?.data?.detail || error.message || '创建失败'
      message.error(detail)
    } finally {
      setLoading(false)
    }
  }

  const title = stickmanVariant === 'v2' ? '优化版火柴人' : '经典版火柴人'
  const description = stickmanVariant === 'v2'
    ? '你正在配置优化版火柴人项目。创建完成后会直接进入优化版任务流或分步创作页。'
    : '你正在配置经典版火柴人项目。创建完成后会进入经典版对应流程。'

  return (
    <div className="creator-page">
      <div className="creator-hero creator-hero-sunrise">
        <div className="hero-content">
          <h1 className="hero-title">
            <VideoCameraOutlined className="mr-3" />
            {title}创作台
          </h1>
          <p className="hero-subtitle">{description}</p>
        </div>
      </div>

      <div className="creator-container">
        <div className="max-w-6xl mx-auto w-full space-y-6">
          <div className="flex gap-3 flex-wrap">
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/creator/stickman')}>返回版本选择</Button>
            <Button onClick={() => navigate('/creator')}>返回创作首页</Button>
          </div>

          <Alert
            type={stickmanVariant === 'v2' ? 'success' : 'info'}
            message={stickmanVariant === 'v2' ? '当前为优化版专属创建页' : '当前为经典版专属创建页'}
            description={stickmanVariant === 'v2' ? '不会再跳回通用首页配置，后续所有设置都在这个专属页面完成。' : '经典版也使用独立创建页，避免与其他模块配置混在一起。'}
          />

          {selectedStickmanCategory ? (
            <div className="max-w-2xl mx-auto">
              <Button onClick={() => setSelectedStickmanCategory(null)} className="mb-4">
                返回选择方向
              </Button>
              <TopicExamples category={selectedStickmanCategory} onSelect={(topic) => setStickmanTopic(topic)} titlePrefix="热门主题" />
            </div>
          ) : (
            <Card>
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-4">
                  <BulbOutlined className="text-xl text-indigo-500" />
                  <span className="text-lg font-medium">选择热门方向</span>
                </div>
                <TopicCategorySelector onSelect={handleStickmanCategorySelect} />
              </div>
            </Card>
          )}

          <Divider>或直接输入主题并配置参数</Divider>

          <div className="stickman-panel">
            <div className="stickman-panel-head">
              <h2>{title}项目配置</h2>
              <p>{stickmanVariant === 'v2' ? '当前为优化版火柴人流程，可继续选择热门方向和主题，并直接完成创建。' : '当前为经典版火柴人流程，可继续选择热门方向和主题，并直接完成创建。'}</p>
            </div>

            <div className="stickman-form-grid">
              <div>
                <label className="stickman-label">文案来源</label>
                <Select
                  value={scriptMode}
                  onChange={(value) => setScriptMode(value)}
                  options={[
                    { label: 'AI 主题生成', value: 'ai' },
                    { label: '完整文案输入', value: 'custom' },
                  ]}
                  style={{ width: '100%', marginBottom: 16 }}
                />
                <label className="stickman-label">{scriptMode === 'custom' ? '视频主题（可选）' : '视频主题'}</label>
                <TextArea
                  value={stickmanTopic}
                  onChange={(e) => setStickmanTopic(e.target.value)}
                  rows={scriptMode === 'custom' ? 3 : 5}
                  placeholder={`例如：
• 为什么拖延会越来越严重
• 普通人如何建立复利思维
• 熬夜对身体的真实影响`}
                />
                {scriptMode === 'custom' && (
                  <>
                    <label className="stickman-label mt-4">完整文案</label>
                    <TextArea
                      value={customScript}
                      onChange={(e) => setCustomScript(e.target.value)}
                      rows={10}
                      placeholder={`直接粘贴完整文案，系统会自动拆成大的部分、再拆成小字幕段和小场景图。\n\n例如：\n很多焦虑，不是事情太多，而是大脑一直在预演失败。\n第一步，先停掉脑内预演。\n第二步，一次只做一件事。\n第三步，给每次行动一个收尾动作。`}
                    />
                  </>
                )}
              </div>

              <div className="stickman-side-card">
                <label className="stickman-label">视频比例</label>
                <div className="aspect-pill">16:9 横屏</div>

                <label className="stickman-label">分镜数量</label>
                <InputNumber min={2} max={stickmanStoryboardMax} value={storyboardCount} onChange={(value) => setStoryboardCount(value || 3)} style={{ width: '100%' }} />

                <label className="stickman-label mt-4">配音来源</label>
                <Select
                  value={voiceSource}
                  onChange={(value) => {
                    setVoiceSource(value)
                    updateAudioFile(null)
                  }}
                  options={[
                    { label: 'AI 配音', value: 'ai' },
                    { label: '直接录音', value: 'record' },
                    { label: '上传音频文件', value: 'upload' },
                  ]}
                  style={{ width: '100%' }}
                />

                <label className="stickman-label mt-4">生成方式</label>
                <Select
                  value={generationMode}
                  onChange={(value) => setGenerationMode(value)}
                  options={[
                    { label: '一键生成', value: 'one_click' },
                    { label: '分步创作', value: 'step_by_step' },
                  ]}
                  style={{ width: '100%' }}
                />

                {voiceSource === 'ai' && (
                  <>
                    <label className="stickman-label mt-4">AI 音色</label>
                    <Select value={ttsVoice} onChange={setTtsVoice} options={safeVoiceOptions.map((item) => ({ label: item.label, value: item.value }))} style={{ width: '100%' }} />

                    <label className="stickman-label mt-4">语速</label>
                    <Select
                      value={ttsRate}
                      onChange={setTtsRate}
                      options={[
                        { label: '偏慢', value: '-15%' },
                        { label: '标准', value: '+0%' },
                        { label: '偏快', value: '+15%' },
                      ]}
                      style={{ width: '100%' }}
                    />
                  </>
                )}

                {voiceSource === 'record' && <AudioRecorder value={audioFile} onChange={updateAudioFile} />}

                {voiceSource === 'upload' && (
                  <div className="audio-source-box">
                    <Upload
                      beforeUpload={(file) => {
                        updateAudioFile(file)
                        return false
                      }}
                      onRemove={() => {
                        updateAudioFile(null)
                      }}
                      maxCount={1}
                      accept=".mp3,.wav,.m4a,.aac,.ogg,.webm"
                    >
                      <Button icon={<UploadOutlined />}>选择音频文件</Button>
                    </Upload>
                    {audioFile && (
                      <div className="audio-preview-stack">
                        <Typography.Text type="secondary">已选择: {audioFile.name}</Typography.Text>
                        <Typography.Text type="secondary">大小: {(audioFile.size / 1024 / 1024).toFixed(2)} MB</Typography.Text>
                        {audioPreviewUrl && <audio controls src={audioPreviewUrl} style={{ width: '100%' }} />}
                      </div>
                    )}
                  </div>
                )}

                {voiceSource !== 'ai' && (
                  <>
                    <div className="audio-source-box">
                      <Typography.Text strong>基于你的声音创建专属 AI 音色</Typography.Text>
                      <Typography.Text type="secondary">建议至少提供 8 秒以上、安静环境下录制的人声样本。系统会先清洗优化，再尝试创建你的专属配音音色。</Typography.Text>
                      <Input value={customVoiceLabel} onChange={(e) => setCustomVoiceLabel(e.target.value)} placeholder="例如：我的成长男声 / 温柔陪伴女声" style={{ marginTop: 8 }} />
                      <Button style={{ marginTop: 12 }} onClick={handleCreateCustomVoice} loading={loading} icon={<AudioOutlined />}>优化并创建我的音色</Button>
                    </div>
                    <Alert style={{ marginTop: 12 }} type="info" showIcon message="新上线模块，默认支持试用 2 次；如需长期使用请联系管理员开通。公众号约 0.6-1.5 元/篇，火柴人视频按分镜计费。" />
                  </>
                )}

                <div className="audio-source-box">
                  <Typography.Text strong>背景图</Typography.Text>
                  <Typography.Text type="secondary">默认使用固定背景。你也可以上传新的背景图，替换整条视频的底图。</Typography.Text>
                  <Upload beforeUpload={(file) => { updateBackgroundImageFile(file); return false }} onRemove={() => { updateBackgroundImageFile(null) }} maxCount={1} accept=".png,.jpg,.jpeg,.webp" style={{ marginTop: 8 }}>
                    <Button icon={<UploadOutlined />}>上传背景图</Button>
                  </Upload>
                  {backgroundImagePreviewUrl && <img src={backgroundImagePreviewUrl} alt="background-preview" style={{ width: '100%', marginTop: 12, borderRadius: 12, border: '1px solid #eee' }} />}
                </div>

                <div className="audio-source-box">
                  <Typography.Text strong>参考风格图</Typography.Text>
                  <Typography.Text type="secondary">上传一张参考图，让分镜图片尽量贴近它的整体风格。</Typography.Text>
                  <Upload beforeUpload={(file) => { updateStyleImageFile(file); return false }} onRemove={() => { updateStyleImageFile(null) }} maxCount={1} accept=".png,.jpg,.jpeg,.webp" style={{ marginTop: 8 }}>
                    <Button icon={<UploadOutlined />}>上传风格参考图</Button>
                  </Upload>
                  <Input.TextArea rows={2} value={styleNotes} onChange={(e) => setStyleNotes(e.target.value)} placeholder="补充风格说明，例如：极简线稿、暖色调、治愈感" style={{ marginTop: 8 }} />
                  {styleImagePreviewUrl && <img src={styleImagePreviewUrl} alt="style-preview" style={{ width: '100%', marginTop: 12, borderRadius: 12, border: '1px solid #eee' }} />}
                </div>

                <div className="stickman-tips">
                  <p>{stickmanVariant === 'v2' ? '优化版会进入专属 v2 工作流，不再回到通用首页配置。' : '经典版会保持原有火柴人制作逻辑，但入口与创建页已独立。'}</p>
                  <p>{scriptMode === 'custom' ? '当前会优先使用你输入的完整文案，再自动拆成大的部分和小分镜。' : '当前会根据主题自动生成完整文案、再拆成大的部分和小分镜。'}</p>
                  <p>当前版本默认生成 16:9 横版视频。</p>
                  <p>支持 AI 配音、浏览器录音和音频文件上传。</p>
                  <p>支持一键生成，也支持分步控制脚本、分镜和图片。</p>
                </div>

                <Button
                  type="primary"
                  icon={<VideoCameraOutlined />}
                  onClick={handleStickmanCreate}
                  loading={loading}
                  size="large"
                  block
                  disabled={!stickmanTopic.trim()}
                  className="btn-gradient-warm"
                >
                  创建并进入任务
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
