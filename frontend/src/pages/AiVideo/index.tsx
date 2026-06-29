import { useEffect, useMemo, useState } from 'react'
import { Button, Form, Input, Progress, Select, Space, Tag, message } from 'antd'
import {
  CheckCircleOutlined,
  CloudDownloadOutlined,
  DashboardOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  RocketOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons'
import { motion } from 'framer-motion'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  aiVideoApi,
  AiVideoCapability,
  AiVideoExport,
  AiVideoJob,
  AiVideoJobCreate,
  AiVideoOverview,
  AiVideoProject,
} from '@/services/aiVideo'
import { resolveBackendUrl } from '@/services/api'
import './AiVideo.css'

type CreatorMode = 'prompt' | 'style'
type Option = {
  key: string
  label: string
  english: string
  desc: string
  prompt: string
  icon: string
  defaultStyle?: string
}

const videoTypes: Option[] = [
  {
    key: 'product_seed',
    label: '种草带货',
    english: 'Product Hook',
    icon: '01',
    defaultStyle: 'commerce_boost',
    desc: '痛点、卖点、场景和行动引导，适合商品、课程、工具服务。',
    prompt: '帮我做一条小红书种草视频，高级感，开头要抓人，突出真实痛点、产品卖点和购买理由。',
  },
  {
    key: 'teaching',
    label: '教学讲解',
    english: 'Clean Explainer',
    icon: '02',
    defaultStyle: 'clean_explainer',
    desc: '把复杂内容讲清楚，适合教程、知识科普、方法论。',
    prompt: '帮我做一条教学讲解视频，用新手也能听懂的方式，先抛问题，再拆成三步讲清楚。',
  },
  {
    key: 'lifestyle',
    label: '生活分享',
    english: 'Lifestyle',
    icon: '03',
    defaultStyle: 'lifestyle_magazine',
    desc: '自然、有画面感，适合 vlog、日常记录、生活方式内容。',
    prompt: '帮我做一条生活分享视频，语气自然，有画面感，开头让人想继续看，结尾有一点温柔共鸣。',
  },
  {
    key: 'briefing',
    label: '热点快评',
    english: 'News Flash',
    icon: '04',
    defaultStyle: 'news_flash',
    desc: '快节奏讲清事件、矛盾和判断，适合热点、财经、行业观察。',
    prompt: '帮我做一条热点快评视频，先一句话讲清事件，再指出核心矛盾，最后给出明确观点。',
  },
  {
    key: 'creator_talk',
    label: '个人口播',
    english: 'Creator Talk',
    icon: '05',
    defaultStyle: 'viral_pop',
    desc: '像真人创作者表达观点，适合个人 IP、经验分享、观点输出。',
    prompt: '帮我做一条个人 IP 口播视频，像一个有经验的创作者在分享真实判断，开头要强。',
  },
  {
    key: 'case_study',
    label: '案例复盘',
    english: 'Case Study',
    icon: '06',
    defaultStyle: 'data_report',
    desc: '背景、决策、结果和可复用方法，适合商业案例、运营复盘。',
    prompt: '帮我做一条案例复盘视频，讲清背景、关键决策、结果和可复用方法，画面要有数据感。',
  },
]

const visualStyles: Option[] = [
  { key: 'premium_black_gold', label: '高级黑金', english: 'Black Gold', icon: 'BG', desc: '黑金质感、慢推镜头、强品牌感。', prompt: '视觉风格要高级黑金，克制、有质感，字幕不要太满。' },
  { key: 'commerce_boost', label: '电商转化', english: 'Commerce', icon: 'CB', desc: '卖点卡、对比画面、强行动引导。', prompt: '视觉风格要适合带货转化，突出卖点、对比和 CTA。' },
  { key: 'clean_explainer', label: '极简白板', english: 'Explainer', icon: 'CE', desc: '白板线条、步骤卡片、讲解清楚。', prompt: '视觉风格要极简白板，重点突出步骤、关键词和逻辑。' },
  { key: 'lifestyle_magazine', label: '杂志生活', english: 'Magazine', icon: 'LM', desc: '留白、慢节奏、生活方式质感。', prompt: '视觉风格要像生活杂志，有留白、节奏舒缓、画面感强。' },
  { key: 'news_flash', label: '热点快讯', english: 'Flash', icon: 'NF', desc: '红蓝对比、快切、时间线和信息卡。', prompt: '视觉风格要像新闻快讯，节奏快，信息清晰，有时间线和判断感。' },
  { key: 'tech_blueprint', label: '科技蓝图', english: 'Blueprint', icon: 'TB', desc: '网格、HUD、扫描线、数据结构。', prompt: '视觉风格要科技蓝图，有网格、扫描线、结构图和未来感。' },
]

const platformOptions = [
  { value: 'douyin', label: '抖音 / 快节奏' },
  { value: 'xiaohongshu', label: '小红书 / 种草感' },
  { value: 'wechat', label: '视频号 / 稳重表达' },
  { value: 'bilibili', label: 'B站 / 讲解深度' },
]

const stageLabels: Record<string, string> = {
  pending: '任务排队',
  scripting: '理解需求',
  scene_planning: '自动编排节奏',
  tts_generating: 'CosyVoice 配音',
  audio_processing: '音频整理',
  rendering: 'Remotion 渲染',
  uploading: '保存成片',
  completed: '生成完成',
  failed: '生成失败',
  cancelled: '已取消',
}

const stageFlow = [
  { key: 'pending', label: '排队' },
  { key: 'scripting', label: '理解需求' },
  { key: 'scene_planning', label: '编排画面' },
  { key: 'tts_generating', label: 'CosyVoice' },
  { key: 'audio_processing', label: '整理音频' },
  { key: 'rendering', label: '渲染视频' },
  { key: 'uploading', label: '保存成片' },
  { key: 'completed', label: '完成' },
]

const tabs = [
  { path: '/ai-video/dashboard', label: '首页', icon: <DashboardOutlined /> },
  { path: '/ai-video/create', label: '生成', icon: <PlusOutlined /> },
  { path: '/ai-video/exports', label: '成片', icon: <CloudDownloadOutlined /> },
  { path: '/ai-video/settings', label: '状态', icon: <SettingOutlined /> },
]

function Shell({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const active = location.pathname === '/ai-video' ? '/ai-video/dashboard' : location.pathname
  return (
    <div className="ai-video-shell">
      <div className="studio-noise" />
      <div className="studio-particles"><span /><span /><span /><span /><span /></div>
      <div className="ai-video-content">
        <header className="studio-nav">
          <button className="studio-brand" onClick={() => navigate('/ai-video/create')}>
            <span className="brand-sigil" />
            <strong>AI Video Studio</strong>
          </button>
          <nav className="studio-tabs">
            {tabs.map(t => (
              <button key={t.path} className={active.startsWith(t.path) ? 'active' : ''} onClick={() => navigate(t.path)}>
                {t.icon}
                <span>{t.label}</span>
              </button>
            ))}
          </nav>
          <Button className="light-action" icon={<VideoCameraOutlined />} onClick={() => navigate('/ai-video/create')}>
            一句话生成
          </Button>
        </header>
        {children}
      </div>
    </div>
  )
}

function OptionCard({ item, active, onClick }: { item: Option; active?: boolean; onClick?: () => void }) {
  return (
    <button className={`option-card style-${item.defaultStyle || item.key} ${active ? 'active' : ''}`} onClick={onClick} type="button">
      <span className="option-index">{item.icon}</span>
      <strong>{item.label}</strong>
      <em>{item.english}</em>
      <p>{item.desc}</p>
    </button>
  )
}

function JobControl({ job }: { job: AiVideoJob }) {
  const currentIndex = Math.max(0, stageFlow.findIndex(item => item.key === job.stage))
  return (
    <div className="job-control">
      <div className="waveform">{Array.from({ length: 22 }, (_, i) => <i key={i} />)}</div>
      <Progress percent={job.progress} status={job.status === 'failed' ? 'exception' : job.status === 'completed' ? 'success' : 'active'} />
      <div className="stage-progress">
        {stageFlow.map((item, index) => (
          <span key={item.key} className={index < currentIndex || job.status === 'completed' ? 'done' : index === currentIndex ? 'current' : ''}>
            {item.label}
          </span>
        ))}
      </div>
      <p><strong>{stageLabels[job.stage] || job.message}</strong>{job.stage === 'tts_generating' ? '，正在生成每一幕配音。' : job.stage === 'rendering' ? '，正在合成画面、转场和音轨。' : ''}</p>
      {job.errorMessage && <p className="error-text">{job.errorMessage}</p>}
    </div>
  )
}

function ProjectItem({ project }: { project: AiVideoProject }) {
  const navigate = useNavigate()
  return (
    <motion.div className="project-item" whileHover={{ y: -4 }}>
      <div className={`project-thumb thumb-${project.videoType}`}>
        <span>{project.videoType}</span>
        <strong>{project.title}</strong>
      </div>
      <div className="project-meta">
        <strong>{project.title}</strong>
        <div><Tag>{project.videoType}</Tag><Tag color="blue">{project.status}</Tag><Tag>{project.aspectRatio}</Tag></div>
      </div>
      <Button className="ghost-action" icon={<PlayCircleOutlined />} onClick={() => navigate(`/ai-video/editor/${project.id}`)}>
        查看
      </Button>
    </motion.div>
  )
}

export function AiVideoDashboard() {
  const navigate = useNavigate()
  const [overview, setOverview] = useState<AiVideoOverview | null>(null)

  useEffect(() => {
    aiVideoApi.overview().then(r => setOverview(r.data)).catch(() => message.error('无法加载 AI 视频概览'))
  }, [])

  const stats = overview?.stats || { totalProjects: 0, generating: 0, completed: 0, monthlyExports: 0 }

  return (
    <Shell>
      <section className="studio-hero compact-hero">
        <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <div className="eyebrow"><ThunderboltOutlined /> Prompt First</div>
          <h1>说清你想要什么，系统直接生成视频</h1>
          <p>不需要懂分镜、不需要懂剪辑。输入主题、风格和文案要求，后台自动完成开头钩子、节奏、画面、转场、字幕和 CosyVoice 配音。</p>
          <div className="hero-compose">
            <span>例如：做一条小红书护肤品种草视频，高级感，前三秒抓人</span>
            <button onClick={() => navigate('/ai-video/create')}>Start Creating</button>
          </div>
        </motion.div>
      </section>

      <div className="metric-row">
        <div className="metric-card"><strong>{stats.totalProjects}</strong><span>项目总数</span></div>
        <div className="metric-card"><strong>{stats.generating}</strong><span>生成中</span></div>
        <div className="metric-card"><strong>{stats.completed}</strong><span>已完成</span></div>
        <div className="metric-card"><strong>{stats.monthlyExports}</strong><span>版本 / 导出</span></div>
      </div>

      <div className="ai-video-grid">
        <section className="ai-video-panel span-8">
          <div className="panel-headline">
            <div><div className="panel-kicker">Creator Flow</div><h2>两种简单开始方式</h2></div>
            <Button className="primary-action" onClick={() => navigate('/ai-video/create')}>立即生成</Button>
          </div>
          <div className="flow-cards">
            <div><strong>一句话生成</strong><p>把风格、文案、目标写在一起，系统自动判断视频类型和节奏。</p></div>
            <div><strong>先选风格</strong><p>选择大方向后再输入要求，不是套模板，后台仍会动态编排画面。</p></div>
          </div>
        </section>
        <section className="ai-video-panel span-4">
          <div className="panel-kicker">Render Queue</div>
          <h2>生成队列</h2>
          <div className="stage-list">
            {(overview?.queue || []).slice(0, 4).map(j => <JobControl key={j.jobId} job={j} />)}
            {!overview?.queue?.length && <p className="muted">当前没有渲染任务。</p>}
          </div>
        </section>
        <section className="ai-video-panel span-12">
          <div className="panel-headline">
            <div><div className="panel-kicker">Recent Works</div><h2>最近成片</h2></div>
            <Button className="ghost-action" onClick={() => navigate('/ai-video/exports')}>全部成片</Button>
          </div>
          <div className="project-list cinematic">
            {(overview?.recentProjects || []).map(p => <ProjectItem key={p.id} project={p} />)}
            {!overview?.recentProjects?.length && <p className="muted">还没有项目，先生成一条样片。</p>}
          </div>
        </section>
      </div>
    </Shell>
  )
}

export function AiVideoCreate() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [form] = Form.useForm()
  const [mode, setMode] = useState<CreatorMode>(params.get('mode') === 'style' ? 'style' : 'prompt')
  const [selectedType, setSelectedType] = useState(params.get('type') || 'product_seed')
  const [selectedStyle, setSelectedStyle] = useState(params.get('style') || 'premium_black_gold')
  const [job, setJob] = useState<AiVideoJob | null>(null)
  const [loading, setLoading] = useState(false)

  const typeMeta = useMemo(() => videoTypes.find(i => i.key === selectedType) || videoTypes[0], [selectedType])
  const styleMeta = useMemo(() => visualStyles.find(i => i.key === selectedStyle) || visualStyles[0], [selectedStyle])

  useEffect(() => {
    if (mode === 'style') {
      form.setFieldsValue({ requirements: `${typeMeta.prompt}\n${styleMeta.prompt}` })
    }
  }, [form, mode, styleMeta.prompt, typeMeta.prompt])

  useEffect(() => {
    if (!job || ['completed', 'failed', 'cancelled'].includes(job.status)) return
    const timer = setInterval(async () => {
      const { data } = await aiVideoApi.getJob(job.jobId)
      setJob(data)
      if (data.status === 'completed') {
        message.success('视频生成完成')
        navigate(`/ai-video/editor/${data.projectId}`)
      }
    }, 2500)
    return () => clearInterval(timer)
  }, [job, navigate])

  const submit = async (values: any) => {
    const requirements = String(values.requirements || '').trim()
    const script = String(values.script || '').trim()
    if (!requirements) {
      message.warning('先写一句你想生成什么视频')
      return
    }
    const payload: AiVideoJobCreate = {
      title: values.title || undefined,
      prompt: requirements,
      requirements,
      creativeBrief: requirements,
      script,
      customPrompt: mode === 'style' ? `${styleMeta.prompt}\n${requirements}` : requirements,
      videoType: mode === 'style' ? selectedType : 'auto',
      contentType: mode === 'style' ? selectedType : undefined,
      style: mode === 'style' ? selectedStyle : 'auto',
      visualStyle: mode === 'style' ? selectedStyle : undefined,
      aspectRatio: values.aspectRatio,
      voiceProvider: 'cosyvoice',
      voiceId: values.voiceId,
      subtitleMode: values.subtitleMode,
      targetPlatform: values.targetPlatform,
      tone: values.tone,
      pace: values.pace,
      goal: values.goal,
    }
    setLoading(true)
    try {
      const { data } = await aiVideoApi.createJob(payload)
      const jobRes = await aiVideoApi.getJob(data.jobId)
      setJob(jobRes.data)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Shell>
      <div className="create-header simple-create">
        <div>
          <div className="eyebrow"><RocketOutlined /> Easy Creator</div>
          <h1>一句话，也能生成完整视频</h1>
          <p>主要入口是直接输入提示词。想更稳一点，就先选一个风格方向，再写自己的要求。</p>
        </div>
        <div className="mode-switch">
          <button className={mode === 'prompt' ? 'active' : ''} onClick={() => setMode('prompt')}>直接输入生成</button>
          <button className={mode === 'style' ? 'active' : ''} onClick={() => setMode('style')}>先选风格</button>
        </div>
      </div>

      <Form
        form={form}
        layout="vertical"
        onFinish={submit}
        initialValues={{
          requirements: '帮我做一条小红书护肤品种草视频，高级感，开头抓人，强调熬夜修护，最后引导购买。',
          script: '',
          aspectRatio: '16:9',
          targetPlatform: 'xiaohongshu',
          voiceId: '中文女',
          subtitleMode: 'keywords',
          pace: 'medium',
          tone: 'confident',
          goal: '提升完播和转化',
        }}
      >
        <div className="ai-video-grid creator-grid">
          {mode === 'style' && (
            <section className="ai-video-panel span-12 style-picker-panel">
              <div className="panel-headline">
                <div><div className="panel-kicker">Style Direction</div><h2>选择一个创作方向</h2></div>
                <Tag color="orange">不是模板，生成时会自动变化</Tag>
              </div>
              <div className="style-columns">
                <div>
                  <h3>视频类型</h3>
                  <div className="option-row">{videoTypes.map(t => <OptionCard key={t.key} item={t} active={selectedType === t.key} onClick={() => { setSelectedType(t.key); setSelectedStyle(t.defaultStyle || selectedStyle) }} />)}</div>
                </div>
                <div>
                  <h3>画面风格</h3>
                  <div className="option-row">{visualStyles.map(s => <OptionCard key={s.key} item={s} active={selectedStyle === s.key} onClick={() => setSelectedStyle(s.key)} />)}</div>
                </div>
              </div>
            </section>
          )}

          <section className="ai-video-panel span-8 prompt-panel">
            <div className="panel-kicker">Creative Brief</div>
            <h2>你想生成什么视频？</h2>
            <Form.Item name="requirements" rules={[{ required: true, message: '请输入生成要求' }]}>
              <Input.TextArea
                rows={6}
                className="big-prompt"
                placeholder="例如：做一条小红书护肤品种草视频，高级感，前三秒抓人，强调熬夜修护，最后引导购买。"
              />
            </Form.Item>
            <Form.Item name="script">
              <Input.TextArea
                rows={5}
                className="big-prompt script-prompt"
                placeholder="Optional script / voiceover. If filled, rendering follows this text strictly. Leave empty to let AI write it from the creative brief."
              />
            </Form.Item>
            <div className="prompt-hints">
              {['开头要抓人', '像小红书种草', '少一点文字', '更快节奏', '更高级感'].map(item => (
                <button key={item} type="button" onClick={() => form.setFieldValue('requirements', `${form.getFieldValue('requirements') || ''} ${item}`.trim())}>{item}</button>
              ))}
            </div>
            <Space wrap className="submit-row">
              <Button className="primary-action generate-btn" htmlType="submit" loading={loading} icon={<VideoCameraOutlined />}>
                生成完整视频
              </Button>
              <span>后台会自动拆解内容、安排分镜、控制节奏和转场。</span>
            </Space>
            <p className="audio-note">生成后播放器如果没有声音，请先确认浏览器视频控件没有静音；系统会使用 CosyVoice 生成并合成音轨。</p>
            {job && <JobControl job={job} />}
          </section>

          <section className="ai-video-panel span-4 settings-panel">
            <div className="panel-kicker">Quick Settings</div>
            <h2>少量必要设置</h2>
            <Form.Item name="title" label="标题，可不填"><Input placeholder="系统会自动生成标题" /></Form.Item>
            <Form.Item name="targetPlatform" label="发布平台"><Select options={platformOptions} /></Form.Item>
            <Form.Item name="aspectRatio" label="画面比例"><Select options={[{ value: '16:9', label: '横屏 16:9' }, { value: '9:16', label: '竖屏 9:16' }, { value: '1:1', label: '方形 1:1' }]} /></Form.Item>
            <Form.Item name="voiceId" label="CosyVoice 音色"><Select options={[{ value: '中文女', label: '中文女' }, { value: '中文男', label: '中文男' }]} /></Form.Item>
            <Form.Item name="pace" label="节奏"><Select options={[{ value: 'fast', label: '快节奏' }, { value: 'medium', label: '中等' }, { value: 'slow', label: '舒缓' }]} /></Form.Item>
            <Form.Item name="subtitleMode" label="字幕"><Select options={[{ value: 'keywords', label: '关键词字幕' }, { value: 'full', label: '完整字幕' }, { value: 'minimal', label: '少量字幕' }]} /></Form.Item>
            <Form.Item name="tone" label="语气"><Select options={[{ value: 'confident', label: '坚定' }, { value: 'warm', label: '温柔' }, { value: 'professional', label: '专业' }, { value: 'energetic', label: '有活力' }]} /></Form.Item>
            <Form.Item name="goal" label="目标"><Input placeholder="例如：提升完播、引导购买、涨粉" /></Form.Item>
          </section>
        </div>
      </Form>
    </Shell>
  )
}

export function AiVideoEditor() {
  const { id } = useParams()
  const [project, setProject] = useState<AiVideoProject | null>(null)
  const [editText, setEditText] = useState('')
  const [plan, setPlan] = useState<string[]>([])
  const [versions, setVersions] = useState<any[]>([])
  const [activeJob, setActiveJob] = useState<AiVideoJob | null>(null)
  const [planning, setPlanning] = useState(false)
  const [applying, setApplying] = useState(false)

  const load = async () => {
    if (!id) return
    const { data } = await aiVideoApi.getProject(Number(id))
    setProject(data)
    const vr = await aiVideoApi.versions(Number(id))
    setVersions(vr.data as any[])
  }

  useEffect(() => { load() }, [id])

  useEffect(() => {
    if (!activeJob || ['completed', 'failed', 'cancelled'].includes(activeJob.status)) return
    const timer = window.setInterval(async () => {
      const { data } = await aiVideoApi.getJob(activeJob.jobId)
      setActiveJob(data)
      if (data.status === 'completed') {
        message.success('已按修改意见重新生成视频')
        setPlan([])
        setEditText('')
        load()
      }
      if (data.status === 'failed') {
        message.error(data.errorMessage || '重新生成失败')
      }
    }, 2500)
    return () => window.clearInterval(timer)
  }, [activeJob?.jobId, activeJob?.status])

  const scenes = project?.projectJson?.scenes || []
  const outputUrl = resolveBackendUrl(project?.outputUrl)

  const createPlan = async () => {
    if (!project || !editText.trim()) return
    setPlanning(true)
    try {
      const { data } = await aiVideoApi.planEdit(project.id, editText)
      setPlan(data.editPlan)
      message.success('已根据你的修改意见生成执行计划')
    } finally {
      setPlanning(false)
    }
  }

  const applyPlan = async () => {
    if (!project || !editText.trim()) return
    const finalPlan = plan.length ? plan : (await aiVideoApi.planEdit(project.id, editText)).data.editPlan
    setPlan(finalPlan)
    setApplying(true)
    try {
      const { data } = await aiVideoApi.applyEdit(project.id, finalPlan, editText)
      setProject(data.project)
      const jobRes = await aiVideoApi.getJob(data.jobId)
      setActiveJob(jobRes.data)
      message.success('已开始按你的修改意见重新生成视频')
    } finally {
      setApplying(false)
    }
  }

  return (
    <Shell>
      <div className="editor-title">
        <div><div className="eyebrow"><CheckCircleOutlined /> Result Studio</div><h1>{project?.title || '视频项目'}</h1></div>
        <Space wrap><Tag>{project?.videoType}</Tag><Tag>{project?.aspectRatio}</Tag><Tag color="green">{project?.status}</Tag></Space>
      </div>
      <div className="ai-video-grid">
        <section className="ai-video-panel span-8">
          <div className="preview-frame">{outputUrl ? <video src={outputUrl} controls autoPlay={false} /> : <span>视频生成后会显示在这里</span>}</div>
          {outputUrl && <p className="audio-note">这条视频包含 CosyVoice 音轨。播放时请确认浏览器播放器右下角没有静音。</p>}
          <div className="timeline compact-timeline">
            {scenes.map((scene: any, index: number) => <div className="timeline-card" key={scene.id || index}><strong>{index + 1}</strong><p>{scene.subtitleText || scene.voiceText}</p></div>)}
          </div>
        </section>
        <section className="ai-video-panel span-4">
          <div className="panel-kicker">Chat Modify</div>
          <h2>继续用对话修改</h2>
          <div className="director-box">
            <Input.TextArea rows={6} value={editText} onChange={e => setEditText(e.target.value)} placeholder="例如：开头再抓人一点，整体更像小红书，字幕少一点，节奏更快。" />
            <Button className="ghost-action" onClick={createPlan} loading={planning} disabled={!editText.trim()}>按修改意见生成计划</Button>
            {!!plan.length && <div className="edit-plan-box">
              <strong>将按这些修改执行</strong>
              {plan.map((item, index) => <div className="stage-item" key={item}><span className="stage-dot">{index + 1}</span><span>{item}</span></div>)}
            </div>}
            <Button className="primary-action" onClick={applyPlan} loading={applying} disabled={!editText.trim() || !!activeJob && !['completed', 'failed', 'cancelled'].includes(activeJob.status)}>
              应用修改并重新生成视频
            </Button>
            {activeJob && !['completed', 'failed', 'cancelled'].includes(activeJob.status) && (
              <div className="edit-render-progress">
                <strong>{stageLabels[activeJob.stage] || activeJob.message || '重新生成中'}</strong>
                <Progress percent={activeJob.progress} status="active" />
              </div>
            )}
            {activeJob?.status === 'failed' && <p className="audio-note">重新生成失败：{activeJob.errorMessage}</p>}
            {outputUrl && <Button className="light-action" icon={<CloudDownloadOutlined />} href={outputUrl}>下载 MP4</Button>}
          </div>
          <h2 className="section-gap">版本历史</h2>
          <div className="version-list">{versions.map(v => <div className="version-item" key={v.id}><strong>Version {v.versionNo}</strong><p>{v.changeSummary || '生成版本'}</p></div>)}</div>
        </section>
      </div>
    </Shell>
  )
}

export function AiVideoTemplates() {
  return <Shell><SimpleCollection title="风格方向" subtitle="这里展示的是创作方向，不是固定模板。真正生成时会根据用户输入自动编排。" items={videoTypes} /></Shell>
}

export function AiVideoAssets() {
  return <Shell><SimpleCollection title="视觉风格" subtitle="这些风格会影响画面语言、转场、字幕密度和节奏。" items={visualStyles} /></Shell>
}

export function AiVideoBrandKit() {
  return <Shell><div className="ai-video-panel"><div className="panel-kicker">Brand Kit</div><h2>品牌资产</h2><p className="muted">后续可接入 Logo、品牌色和固定口播人设。当前创建流程已优先保持简单。</p></div></Shell>
}

export function AiVideoExports() {
  const [exports, setExports] = useState<AiVideoExport[]>([])
  useEffect(() => { aiVideoApi.exports().then(r => setExports(r.data)) }, [])
  return (
    <Shell>
      <div className="ai-video-panel">
        <div className="panel-kicker">Exports</div>
        <h2>成片记录</h2>
        <div className="project-list cinematic">
          {exports.map(item => (
            <div className="project-item" key={item.id}>
              <div className="project-thumb"><strong>{item.title}</strong></div>
              <div><strong>{item.title}</strong><div><Tag>Version {item.versionNo}</Tag><Tag>{item.status}</Tag></div></div>
              {item.outputUrl && <Button className="ghost-action" href={resolveBackendUrl(item.outputUrl)}>下载</Button>}
            </div>
          ))}
        </div>
      </div>
    </Shell>
  )
}

export function AiVideoSettings() {
  const [capability, setCapability] = useState<AiVideoCapability | null>(null)
  useEffect(() => { aiVideoApi.capabilities().then(r => setCapability(r.data)) }, [])
  return (
    <Shell>
      <div className="ai-video-grid">
        <section className="ai-video-panel span-6">
          <div className="panel-kicker">Service</div>
          <h2>渲染服务</h2>
          <div className="status-grid">
            <div><strong>{capability?.renderService.available ? '可用' : '降级'}</strong><span>Remotion</span></div>
            <div><strong>{capability?.cosyVoiceService?.available ? '可用' : '检查中'}</strong><span>CosyVoice</span></div>
            <div><strong>{capability?.limits.renderConcurrency || 1}</strong><span>渲染并发</span></div>
            <div><strong>{capability?.limits.cosyVoiceConcurrency || 1}</strong><span>配音并发</span></div>
          </div>
        </section>
      </div>
    </Shell>
  )
}

function SimpleCollection({ title, subtitle, items }: { title: string; subtitle: string; items: Option[] }) {
  return (
    <div className="ai-video-panel">
      <div className="panel-kicker">Collection</div>
      <h2>{title}</h2>
      <p className="muted">{subtitle}</p>
      <div className="style-showcase">{items.map(i => <OptionCard key={i.key} item={i} />)}</div>
    </div>
  )
}

export default AiVideoDashboard
