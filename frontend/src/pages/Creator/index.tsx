import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Input, message, Divider, Card, InputNumber, Segmented, Select, Upload, Typography } from 'antd'
import { RocketOutlined, BulbOutlined, VideoCameraOutlined, HighlightOutlined, UploadOutlined, FileTextOutlined, AudioOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { projectApi, StickmanVoiceOption } from '@/services/project'
import { articleApi, Category as ArticleCategory } from '@/services/article'
import TopicCategorySelector from './components/TopicCategorySelector'
import TopicExamples from './components/TopicExamples'
import AudioRecorder from './components/AudioRecorder'
import { VideoTopicCategory } from '@/services/videoTopic'
import './Creator.css'

const { TextArea } = Input

type ModuleType = 'manim' | 'stickman' | 'article'
type VoiceSource = 'ai' | 'record' | 'upload'
type GenerationMode = 'one_click' | 'step_by_step'

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

export default function Creator() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const [loading, setLoading] = useState(false)
  const [moduleType, setModuleType] = useState<ModuleType>('manim')
  const [selectedCategory, setSelectedCategory] = useState<VideoTopicCategory | null>(null)
  const [selectedStickmanCategory, setSelectedStickmanCategory] = useState<VideoTopicCategory | null>(null)
  const [customTopic, setCustomTopic] = useState('')
  const [stickmanTopic, setStickmanTopic] = useState('')
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
  const [articleTopic, setArticleTopic] = useState('')
  const [articleCategory, setArticleCategory] = useState('生活')
  const [articleCategories, setArticleCategories] = useState<ArticleCategory[]>([])
  const [selectedArticleCategory, setSelectedArticleCategory] = useState<ArticleCategory | null>(null)
  const safeVoiceOptions = useMemo(() => normalizeVoiceOptions(voiceLibrary), [voiceLibrary])

  const permissions = user?.module_permissions || {}
  const stickmanEnabled = user?.is_admin || permissions.stickman?.enabled !== false
  const articleEnabled = user?.is_admin || permissions.article?.enabled !== false
  const stickmanStoryboardMax = user?.is_admin ? 20 : 6

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

  const handleCategorySelect = (category: VideoTopicCategory) => {
    setSelectedCategory(category)
  }

  const handleStickmanCategorySelect = (category: VideoTopicCategory) => {
    setSelectedStickmanCategory(category)
    setStickmanTopic(category.example_topics?.[0] || '')
  }

  const ensureArticleCategories = async () => {
    if (articleCategories.length) return articleCategories
    const { data } = await articleApi.getCategories()
    setArticleCategories(data)
    return data
  }

  const handleArticleModeEnter = async () => {
    try {
      await ensureArticleCategories()
    } catch {
      message.error('加载公众号主题方向失败')
    }
  }

  const handleCreateProject = async (payload: {
    title: string
    theme: string
    category?: string
    module_type: 'manim' | 'stickman'
    storyboard_count?: number
  }) => {
    setLoading(true)
    try {
      const { data } = await projectApi.create(payload)
      message.success('创建成功')
      if (payload.module_type === 'stickman') {
        navigate(`/project/${data.id}/task`)
        return
      }
      navigate(`/project/${data.id}/chat`)
    } catch (error: any) {
      const detail = error.response?.data?.detail || error.message || '创建失败'
      message.error(detail)
    } finally {
      setLoading(false)
    }
  }

  const handleTopicSelect = async (topic: string) => {
    await handleCreateProject({
      title: `视频创作-${topic}`,
      theme: topic,
      category: selectedCategory?.name,
      module_type: 'manim',
      storyboard_count: 3,
    })
  }

  const handleCustomCreate = async () => {
    if (!customTopic.trim()) {
      message.warning('请输入主题')
      return
    }
    await handleTopicSelect(customTopic)
  }

  const handleStickmanCreate = async () => {
    if (!stickmanEnabled) {
      message.warning('当前账号未开通火柴人视频模块，请联系管理员开通')
      return
    }
    if (!stickmanTopic.trim()) {
      message.warning('请输入火柴人视频主题')
      return
    }
    if (voiceSource !== 'ai' && !audioFile) {
      message.warning('请先录音或上传音频文件')
      return
    }

    const selectedVoice = safeVoiceOptions.find((item) => item.value === ttsVoice)
    setLoading(true)
    try {
      const { data } = await projectApi.create({
        title: `火柴人视频-${stickmanTopic}`,
        theme: stickmanTopic.trim(),
        module_type: 'stickman',
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
      if (styleImageFile) {
        await projectApi.uploadStyleReference(data.id, styleImageFile, styleNotes || undefined)
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

  const handleArticleTopicSelect = (topic: string) => {
    if (!articleEnabled) {
      message.warning('当前账号未开通公众号文章模块，请联系管理员开通')
      return
    }
    setArticleTopic(topic)
    navigate(`/article?topic=${encodeURIComponent(topic)}&category=${encodeURIComponent(articleCategory)}`)
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

  return (
    <div className="creator-page">
      <div className="creator-hero creator-hero-sunrise">
        <div className="hero-content">
          <h1 className="hero-title">
            <RocketOutlined className="mr-3" />
            内容创作助手
          </h1>
          <p className="hero-subtitle">
            在统一入口选择动画视频、火柴人视频或公众号文章模块，再进入各自独立的创作流程
          </p>
        </div>
      </div>

      <div className="creator-container">
        <div className="module-switcher-wrap">
          <div className="module-switcher-head">
            <span className="module-switcher-label">开始创作</span>
            <Segmented
              value={moduleType}
              onChange={(value) => {
                const next = value as ModuleType
                setModuleType(next)
                if (next === 'article') {
                  handleArticleModeEnter()
                }
              }}
              options={[
                { label: '思维可视化', value: 'manim' },
                { label: '火柴人视频', value: 'stickman' },
                { label: '公众号文章', value: 'article' },
              ]}
            />
          </div>

          <div className="module-card-grid">
            <Card className={`module-card ${moduleType === 'manim' ? 'active' : ''}`} onClick={() => setModuleType('manim')}>
              <div className="module-card-icon module-card-icon-blue">
                <HighlightOutlined />
              </div>
              <h3>思维可视化</h3>
              <p>多轮打磨文案，生成动画脚本，再进入渲染流程。</p>
            </Card>

            <Card className={`module-card ${moduleType === 'stickman' ? 'active' : ''} ${!stickmanEnabled ? 'module-card-disabled' : ''}`} onClick={() => setModuleType('stickman')}>
              <div className="module-card-icon module-card-icon-orange">
                <VideoCameraOutlined />
              </div>
              <h3>火柴人视频</h3>
              <p>直接填写主题与分镜数，进入图片、配音与合成任务流。</p>
            </Card>

            <Card className={`module-card ${moduleType === 'article' ? 'active' : ''} ${!articleEnabled ? 'module-card-disabled' : ''}`} onClick={() => { setModuleType('article'); handleArticleModeEnter() }}>
              <div className="module-card-icon module-card-icon-green">
                <FileTextOutlined />
              </div>
              <h3>公众号文章</h3>
              <p>生成大纲、正文、配图与公众号 HTML，支持手机预览和复制。</p>
            </Card>
          </div>
        </div>

        {moduleType === 'manim' ? (
          selectedCategory ? (
            <div className="max-w-2xl mx-auto">
              <Button onClick={() => setSelectedCategory(null)} className="mb-4">
                返回选择方向
              </Button>
              <TopicExamples category={selectedCategory} onSelect={handleTopicSelect} />
            </div>
          ) : (
            <>
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-4">
                  <BulbOutlined className="text-xl text-indigo-500" />
                  <span className="text-lg font-medium">选择热门方向</span>
                </div>
                <TopicCategorySelector onSelect={handleCategorySelect} />
              </div>

              <Divider>或直接输入主题</Divider>

              <div className="visual-theme-wrap mx-auto">
                <TextArea
                  value={customTopic}
                  onChange={(e) => setCustomTopic(e.target.value)}
                  placeholder={`输入你的视频主题...

例如：
• 世界十大顶级思维：刻意练习、复利思维、终身学习...
• 勾股定理的证明过程
• 人生三件事：运动、阅读、赚钱`}
                  rows={4}
                  className="theme-input mb-3"
                />

                <Button
                  type="primary"
                  icon={<RocketOutlined />}
                  onClick={handleCustomCreate}
                  loading={loading}
                  size="large"
                  block
                  disabled={!customTopic.trim()}
                  className="btn-gradient"
                >
                  开始创作
                </Button>
              </div>

              <div className="usage-tips mt-6">
                <h3>
                  <BulbOutlined className="mr-2" />
                  使用提示
                </h3>
                <ul>
                  <li>选择热门方向，直接使用爆款主题示例</li>
                  <li>或输入主题，进入 AI 对话打磨流程</li>
                  <li>确认文案后再生成思维可视化脚本和动画视频</li>
                  <li>适合讲解类、公式类、演示类内容</li>
                </ul>
              </div>
            </>
          )
        ) : moduleType === 'stickman' ? (
          selectedStickmanCategory ? (
            <div className="max-w-2xl mx-auto">
              <Button onClick={() => setSelectedStickmanCategory(null)} className="mb-4">
                返回选择方向
              </Button>
              <TopicExamples category={selectedStickmanCategory} onSelect={(topic) => setStickmanTopic(topic)} titlePrefix="热门主题" />
              <div className="stickman-panel mt-6">
                <div className="stickman-panel-head">
                  <h2>火柴人视频模块</h2>
                  <p>先从热门主题入手，或在下方继续调整主题与生成参数。</p>
                </div>

                <div className="stickman-form-grid">
                  <div>
                    <label className="stickman-label">视频主题</label>
                    <TextArea
                      value={stickmanTopic}
                      onChange={(e) => setStickmanTopic(e.target.value)}
                      rows={5}
                      placeholder={`例如：
• 为什么拖延会越来越严重
• 普通人如何建立复利思维
• 熬夜对身体的真实影响`}
                    />
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
                        <Upload beforeUpload={(file) => { updateAudioFile(file); return false }} onRemove={() => { updateAudioFile(null) }} maxCount={1} accept=".mp3,.wav,.m4a,.aac,.ogg,.webm">
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
                      <Typography.Text strong>参考风格图</Typography.Text>
                      <Typography.Text type="secondary">上传一张参考图，让分镜图片尽量贴近它的整体风格。</Typography.Text>
                      <Upload beforeUpload={(file) => { updateStyleImageFile(file); return false }} onRemove={() => { updateStyleImageFile(null) }} maxCount={1} accept=".png,.jpg,.jpeg,.webp" style={{ marginTop: 8 }}>
                        <Button icon={<UploadOutlined />}>上传风格参考图</Button>
                      </Upload>
                      <Input.TextArea rows={2} value={styleNotes} onChange={(e) => setStyleNotes(e.target.value)} placeholder="补充风格说明，例如：极简线稿、暖色调、治愈感" style={{ marginTop: 8 }} />
                      {styleImagePreviewUrl && <img src={styleImagePreviewUrl} alt="style-preview" style={{ width: '100%', marginTop: 12, borderRadius: 12, border: '1px solid #eee' }} />}
                    </div>

                    <div className="stickman-tips">
                      <p>支持热门主题、AI选题和手动输入主题。</p>
                      <p>当前版本默认生成 16:9 横版视频。</p>
                      <p>支持 AI 配音、浏览器录音和音频文件上传。</p>
                    </div>

                    <Button type="primary" icon={<VideoCameraOutlined />} onClick={handleStickmanCreate} loading={loading} size="large" block disabled={!stickmanTopic.trim()} className="btn-gradient-warm">
                      创建并进入任务
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          ) : (
          <div className="stickman-panel">
            <div className="stickman-panel-head">
              <h2>火柴人视频模块</h2>
              <p>先选热门方向和主题，也可以保留下方参数化创作流程。</p>
            </div>

            <div className="mb-6">
              <div className="flex items-center gap-2 mb-4">
                <BulbOutlined className="text-xl text-indigo-500" />
                <span className="text-lg font-medium">选择热门方向</span>
              </div>
              <TopicCategorySelector onSelect={handleStickmanCategorySelect} />
            </div>

            <Divider>或直接输入主题</Divider>

            <div className="stickman-form-grid">
              <div>
                <label className="stickman-label">视频主题</label>
                <TextArea
                  value={stickmanTopic}
                  onChange={(e) => setStickmanTopic(e.target.value)}
                  rows={5}
                  placeholder={`例如：
• 为什么拖延会越来越严重
• 普通人如何建立复利思维
• 熬夜对身体的真实影响`}
                />
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
                  <Typography.Text strong>参考风格图</Typography.Text>
                  <Typography.Text type="secondary">上传一张参考图，让分镜图片尽量贴近它的整体风格。</Typography.Text>
                  <Upload beforeUpload={(file) => { updateStyleImageFile(file); return false }} onRemove={() => { updateStyleImageFile(null) }} maxCount={1} accept=".png,.jpg,.jpeg,.webp" style={{ marginTop: 8 }}>
                    <Button icon={<UploadOutlined />}>上传风格参考图</Button>
                  </Upload>
                  <Input.TextArea rows={2} value={styleNotes} onChange={(e) => setStyleNotes(e.target.value)} placeholder="补充风格说明，例如：极简线稿、暖色调、治愈感" style={{ marginTop: 8 }} />
                  {styleImagePreviewUrl && <img src={styleImagePreviewUrl} alt="style-preview" style={{ width: '100%', marginTop: 12, borderRadius: 12, border: '1px solid #eee' }} />}
                </div>

                <div className="stickman-tips">
                  <p>推荐 3-4 个分镜，生成速度更快。</p>
                  <p>当前版本默认生成 16:9 横版视频。</p>
                  <p>支持 AI 配音、浏览器录音和音频文件上传。</p>
                  <p>支持一键生成，也支持分步控制脚本、分镜和图片。</p>
                  <p>同样支持热门主题与 AI 选题。</p>
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
          )
        ) : (
          <div className="stickman-panel">
            <div className="stickman-panel-head">
              <h2>公众号文章模块</h2>
              <p>支持热门主题、AI 选题、轻量版和专业版工作台。</p>
            </div>

            {selectedArticleCategory ? (
              <div className="max-w-2xl mx-auto">
                <Button onClick={() => setSelectedArticleCategory(null)} className="mb-4">
                  返回选择方向
                </Button>
                <TopicExamples category={selectedArticleCategory} onSelect={handleArticleTopicSelect} generateTopics={articleApi.generateTopics} titlePrefix="热门主题" />
                <div className="mt-6 stickman-form-grid">
                  <div>
                    <label className="stickman-label">文章主题</label>
                    <TextArea value={articleTopic} onChange={(e) => setArticleTopic(e.target.value)} rows={5} placeholder={`例如：
• 为什么成年人越忙越要阅读
• 一个普通人如何建立长期主义
• 父母如何高质量陪伴孩子成长`} />
                  </div>
                  <div className="stickman-side-card">
                    <label className="stickman-label">创作方向</label>
                    <div className="aspect-pill">{articleCategory}</div>
                    <div className="stickman-tips">
                      <p>适合公众号运营、自媒体图文和知识分享场景。</p>
                      <p>支持热门主题、AI 选题、轻量版和专业版。</p>
                    </div>
                    <Button type="primary" icon={<FileTextOutlined />} onClick={() => {
                      if (!articleEnabled) {
                        message.warning('当前账号未开通公众号文章模块，请联系管理员开通')
                        return
                      }
                      navigate(`/article?topic=${encodeURIComponent(articleTopic.trim())}&category=${encodeURIComponent(articleCategory)}`)
                    }} size="large" block disabled={!articleTopic.trim()} className="btn-gradient">
                      进入公众号创作
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
            <>
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-4">
                  <BulbOutlined className="text-xl text-indigo-500" />
                  <span className="text-lg font-medium">选择热门方向</span>
                </div>
                <Button onClick={handleArticleModeEnter} className="mb-3">加载公众号方向</Button>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {articleCategories.map((cat) => (
                    <div key={cat.name} className="category-card p-4 rounded-lg border-2 border-gray-200 cursor-pointer hover:border-indigo-500 hover:shadow-md transition-all" onClick={() => { setArticleCategory(cat.name); setSelectedArticleCategory(cat) }}>
                      <div className="text-3xl text-center mb-2">{cat.icon}</div>
                      <div className="text-sm font-medium text-center">{cat.name}</div>
                    </div>
                  ))}
                </div>
              </div>

              <Divider>或直接输入主题</Divider>

              <div className="stickman-form-grid">
                <div>
                  <label className="stickman-label">文章主题</label>
                  <TextArea
                    value={articleTopic}
                    onChange={(e) => setArticleTopic(e.target.value)}
                    rows={5}
                    placeholder={`例如：
• 为什么成年人越忙越要阅读
• 一个普通人如何建立长期主义
• 父母如何高质量陪伴孩子成长`}
                  />
                </div>

                <div className="stickman-side-card">
                  <label className="stickman-label">创作方向</label>
                  <Select value={articleCategory} onChange={setArticleCategory} options={articleCategories.map((cat) => ({ label: cat.name, value: cat.name }))} style={{ width: '100%' }} />

                  <div className="stickman-tips">
                    <p>适合公众号运营、自媒体图文和知识分享场景。</p>
                    <p>进入后可选择轻量版或专业版。</p>
                    <p>同样支持热门主题与 AI 选题。</p>
                  </div>

                  <Button type="primary" icon={<FileTextOutlined />} onClick={() => {
                    if (!articleEnabled) {
                      message.warning('当前账号未开通公众号文章模块，请联系管理员开通')
                      return
                    }
                    navigate(`/article?topic=${encodeURIComponent(articleTopic.trim())}&category=${encodeURIComponent(articleCategory)}`)
                  }} size="large" block disabled={!articleTopic.trim()} className="btn-gradient">
                    进入公众号创作
                  </Button>
                </div>
              </div>
            </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
