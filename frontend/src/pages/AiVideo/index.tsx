import { useEffect, useState } from 'react'
import { Button, Form, Input, Progress, Select, Space, Switch, Tag, message } from 'antd'
import {
  AppstoreOutlined,
  BgColorsOutlined,
  CloudDownloadOutlined,
  ControlOutlined,
  DashboardOutlined,
  FolderOpenOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  SettingOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import { aiVideoApi, AiVideoCapability, AiVideoExport, AiVideoJob, AiVideoOverview, AiVideoProject } from '@/services/aiVideo'
import { resolveBackendUrl } from '@/services/api'
import './AiVideo.css'

const videoTypes = [
  { key: 'knowledge_visualization', label: '知识可视化', desc: '认知模型、商业思维、AI 科普' },
  { key: 'product_promo', label: '商品推广', desc: '卖点提炼、痛点对比、CTA' },
  { key: 'math_tutorial', label: '数学教学', desc: '公式推导、步骤高亮、易错点' },
  { key: 'data_report', label: '数据报告', desc: '图表动画、趋势总结、KPI' },
  { key: 'saas_demo', label: 'SaaS 演示', desc: '功能标注、流程拆解、发布会风' },
]

const tabs = [
  { path: '/ai-video/dashboard', label: '工作台', icon: <DashboardOutlined /> },
  { path: '/ai-video/create', label: '新建视频', icon: <PlusOutlined /> },
  { path: '/ai-video/templates', label: '模板中心', icon: <AppstoreOutlined /> },
  { path: '/ai-video/assets', label: '素材库', icon: <FolderOpenOutlined /> },
  { path: '/ai-video/brand-kit', label: '品牌资产', icon: <BgColorsOutlined /> },
  { path: '/ai-video/exports', label: '导出记录', icon: <CloudDownloadOutlined /> },
  { path: '/ai-video/settings', label: '模块设置', icon: <SettingOutlined /> },
]

function Shell({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const active = location.pathname === '/ai-video' ? '/ai-video/dashboard' : location.pathname
  return (
    <div className="ai-video-shell">
      <div className="ai-video-particles" />
      <div className="ai-video-content">
        <div className="ai-video-topbar">
          <div className="ai-video-title">
            <h2>AI 视频导演工作台</h2>
            <p>独立扩展模块：项目、任务、版本、品牌资产与渲染文件隔离管理。</p>
          </div>
          <Space>
            <Button icon={<ControlOutlined />} onClick={() => navigate('/ai-video/settings')}>动效与队列</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/ai-video/create')}>新建视频</Button>
          </Space>
        </div>
        <div className="ai-video-tabs">
          {tabs.map(tab => (
            <button key={tab.path} className={`ai-video-tab ${active.startsWith(tab.path) ? 'active' : ''}`} onClick={() => navigate(tab.path)}>
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>
        {children}
      </div>
    </div>
  )
}

export function AiVideoDashboard() {
  const navigate = useNavigate()
  const [overview, setOverview] = useState<AiVideoOverview | null>(null)

  useEffect(() => {
    aiVideoApi.overview().then(res => setOverview(res.data)).catch(() => message.error('无法加载 AI 视频概览'))
  }, [])

  const stats = overview?.stats || { totalProjects: 0, generating: 0, completed: 0, monthlyExports: 0 }
  return (
    <Shell>
      <div className="metric-row">
        <div className="metric-card"><strong>{stats.totalProjects}</strong><span>总项目数</span></div>
        <div className="metric-card"><strong>{stats.generating}</strong><span>生成中</span></div>
        <div className="metric-card"><strong>{stats.completed}</strong><span>已完成</span></div>
        <div className="metric-card"><strong>{stats.monthlyExports}</strong><span>版本 / 导出</span></div>
      </div>
      <div className="ai-video-grid" style={{ marginTop: 16 }}>
        <section className="ai-video-panel span-12">
          <h3>快捷新建</h3>
          <div className="quick-types">
            {videoTypes.map(type => (
              <div className="quick-type" key={type.key} onClick={() => navigate(`/ai-video/create?type=${type.key}`)}>
                <strong>{type.label}</strong>
                <p>{type.desc}</p>
              </div>
            ))}
          </div>
        </section>
        <section className="ai-video-panel span-7">
          <h3>最近项目</h3>
          <div className="project-list">
            {(overview?.recentProjects || []).map(project => <ProjectItem key={project.id} project={project} />)}
            {!overview?.recentProjects?.length && <p>暂无项目，先创建一个可编辑的视频工程。</p>}
          </div>
        </section>
        <section className="ai-video-panel span-5">
          <h3>生成队列</h3>
          <div className="stage-list">
            {(overview?.queue || []).map(job => (
              <div className="stage-item" key={job.jobId}>
                <span className="stage-dot">{job.progress}</span>
                <div>
                  <strong>{job.message}</strong>
                  <Progress percent={job.progress} size="small" status={job.status === 'failed' ? 'exception' : 'active'} />
                </div>
              </div>
            ))}
            {!overview?.queue?.length && <p>当前没有渲染任务。</p>}
          </div>
        </section>
      </div>
    </Shell>
  )
}

function ProjectItem({ project }: { project: AiVideoProject }) {
  const navigate = useNavigate()
  return (
    <div className="project-item">
      <div className="project-thumb" />
      <div>
        <strong>{project.title}</strong>
        <div><Tag>{project.videoType}</Tag><Tag color="blue">{project.status}</Tag><Tag>{project.aspectRatio}</Tag></div>
      </div>
      <Button icon={<PlayCircleOutlined />} onClick={() => navigate(`/ai-video/editor/${project.id}`)}>打开</Button>
    </div>
  )
}

export function AiVideoCreate() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [job, setJob] = useState<AiVideoJob | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!job || job.status === 'completed' || job.status === 'failed') return
    const timer = setInterval(async () => {
      const { data } = await aiVideoApi.getJob(job.jobId)
      setJob(data)
      if (data.status === 'completed') {
        message.success('AI 视频生成完成')
        navigate(`/ai-video/editor/${data.projectId}`)
      }
    }, 1000)
    return () => clearInterval(timer)
  }, [job, navigate])

  const submit = async (values: any) => {
    setLoading(true)
    try {
      const { data } = await aiVideoApi.createJob(values)
      const jobRes = await aiVideoApi.getJob(data.jobId)
      setJob(jobRes.data)
    } finally {
      setLoading(false)
    }
  }

  const cancelJob = async () => {
    if (!job) return
    const { data } = await aiVideoApi.cancelJob(job.jobId)
    setJob(data)
    message.info('已取消当前 AI 视频任务')
  }

  const retryJob = async () => {
    if (!job) return
    const { data } = await aiVideoApi.retryJob(job.jobId)
    const next = await aiVideoApi.getJob(data.jobId)
    setJob(next.data)
    message.success('已重新加入生成队列')
  }

  return (
    <Shell>
      <div className="ai-video-grid">
        <section className="ai-video-panel span-3">
          <h3>视频类型</h3>
          <div className="stage-list">
            {videoTypes.map((type, index) => (
              <div className="stage-item" key={type.key} onClick={() => form.setFieldValue('videoType', type.key)}>
                <span className="stage-dot">{index + 1}</span>
                <div><strong>{type.label}</strong><p>{type.desc}</p></div>
              </div>
            ))}
          </div>
        </section>
        <section className="ai-video-panel span-6">
          <h3>输入核心内容</h3>
          <Form form={form} layout="vertical" onFinish={submit} initialValues={{
            videoType: 'knowledge_visualization',
            aspectRatio: '16:9',
            style: 'futuristic',
            voiceProvider: 'cosyvoice',
            voiceId: '中文女',
            subtitleMode: 'keywords',
            targetPlatform: 'douyin',
          }}>
            <Form.Item name="title" label="标题"><Input placeholder="例如：认知飞轮" /></Form.Item>
            <Form.Item name="script" label="文案" rules={[{ required: true, message: '请输入文案' }]}>
              <Input.TextArea rows={8} placeholder="输入一段知识、商品、教学或演示文案" />
            </Form.Item>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Form.Item name="videoType" label="视频类型"><Select options={videoTypes.map(t => ({ value: t.key, label: t.label }))} /></Form.Item>
              <Form.Item name="aspectRatio" label="视频比例"><Select options={['16:9', '9:16', '1:1'].map(v => ({ value: v, label: v }))} /></Form.Item>
              <Form.Item name="style" label="视觉风格"><Select options={[{ value: 'futuristic', label: '企业科技风' }, { value: 'launch', label: '发布会风' }, { value: 'clean', label: '清爽教学风' }]} /></Form.Item>
              <Form.Item name="targetPlatform" label="目标平台"><Select options={['douyin', 'xiaohongshu', 'bilibili', 'wechat', 'website'].map(v => ({ value: v, label: v }))} /></Form.Item>
            </div>
            <Button type="primary" htmlType="submit" loading={loading} icon={<VideoCameraOutlined />}>生成视频任务</Button>
          </Form>
        </section>
        <section className="ai-video-panel span-3">
          <h3>实时结构预估</h3>
          <div className="stage-list">
            {['理解文案', '拆分场景', '生成配音', '渲染视频', '保存版本'].map((label, index) => (
              <div className="stage-item" key={label}><span className="stage-dot">{index + 1}</span><strong>{label}</strong></div>
            ))}
          </div>
          {job && (
            <div className="job-control">
              <Progress percent={job.progress} status={job.status === 'failed' ? 'exception' : job.status === 'cancelled' ? 'normal' : 'active'} />
              <p>{job.message}</p>
              {job.errorMessage && <p className="error-text">{job.errorMessage}</p>}
              <Space wrap>
                {!['completed', 'failed', 'cancelled'].includes(job.status) && <Button onClick={cancelJob}>取消任务</Button>}
                {['failed', 'cancelled'].includes(job.status) && <Button type="primary" onClick={retryJob}>重试任务</Button>}
              </Space>
            </div>
          )}
        </section>
      </div>
    </Shell>
  )
}

export function AiVideoEditor() {
  const { id } = useParams()
  const [project, setProject] = useState<AiVideoProject | null>(null)
  const [editText, setEditText] = useState('')
  const [plan, setPlan] = useState<string[]>([])
  const [versions, setVersions] = useState<any[]>([])

  const load = async () => {
    if (!id) return
    const { data } = await aiVideoApi.getProject(Number(id))
    setProject(data)
    const versionRes = await aiVideoApi.versions(Number(id))
    setVersions(versionRes.data as any[])
  }

  useEffect(() => { load() }, [id])

  const scenes = project?.projectJson?.scenes || []
  const outputUrl = resolveBackendUrl(project?.outputUrl)

  const createPlan = async () => {
    if (!project || !editText.trim()) return
    const { data } = await aiVideoApi.planEdit(project.id, editText)
    setPlan(data.editPlan)
  }

  const applyPlan = async () => {
    if (!project) return
    await aiVideoApi.applyEdit(project.id, plan, editText)
    message.success('已生成新版本')
    setPlan([])
    setEditText('')
    load()
  }

  const rollback = async (versionId: number) => {
    if (!project) return
    await aiVideoApi.rollbackVersion(project.id, versionId)
    message.success('已回退到选中版本')
    load()
  }

  return (
    <Shell>
      <div className="ai-video-grid">
        <section className="ai-video-panel span-3">
          <h3>项目结构</h3>
          <div className="stage-list">
            {scenes.map((scene: any, index: number) => (
              <div className="stage-item" key={scene.id}>
                <span className="stage-dot">{index + 1}</span>
                <div><strong>{scene.visual?.headline || scene.id}</strong><p>{scene.duration}s · 配音完成 · 可重生成</p></div>
              </div>
            ))}
          </div>
        </section>
        <section className="ai-video-panel span-6">
          <Space style={{ marginBottom: 12 }}>
            <Tag color="green">{project?.status}</Tag>
            <Tag>{project?.aspectRatio}</Tag>
            <Tag>Version #{project?.currentVersionId || 1}</Tag>
          </Space>
          <div className="preview-frame">
            {outputUrl ? <video src={outputUrl} controls style={{ width: '100%', height: '100%', position: 'relative', zIndex: 1 }} /> : <span>视频预览画布</span>}
          </div>
          <h3>时间线</h3>
          <div className="timeline">
            {scenes.map((scene: any) => <div className="timeline-card" key={scene.id}><strong>{scene.id}</strong><p>{scene.subtitleText}</p></div>)}
          </div>
        </section>
        <section className="ai-video-panel span-3">
          <h3>AI 导演</h3>
          <div className="director-box">
            <Input.TextArea rows={5} value={editText} onChange={e => setEditText(e.target.value)} placeholder="例如：前 5 秒加一个更有冲击力的开场" />
            <Button onClick={createPlan}>生成修改计划</Button>
            {plan.map((item, index) => <div className="stage-item" key={item}><span className="stage-dot">{index + 1}</span><span>{item}</span></div>)}
            {!!plan.length && <Button type="primary" onClick={applyPlan}>应用计划并保存版本</Button>}
            {outputUrl && <Button icon={<CloudDownloadOutlined />} href={outputUrl}>下载 MP4</Button>}
            <div className="waveform">{Array.from({ length: 24 }, (_, i) => <i key={i} />)}</div>
          </div>
          <h3 style={{ marginTop: 18 }}>版本历史</h3>
          <div className="version-list">
            {versions.map(version => (
              <div className="version-item" key={version.id}>
                <div>
                  <strong>Version {version.versionNo}</strong>
                  <p>{version.changeSummary || '生成版本'}</p>
                </div>
                <Button size="small" onClick={() => rollback(version.id)}>回退</Button>
              </div>
            ))}
          </div>
        </section>
      </div>
    </Shell>
  )
}

export function AiVideoTemplates() {
  return <Shell><SimpleCollection title="模板中心" items={videoTypes.map(v => `${v.label} · 工作流模板 · 多比例导出`)} /></Shell>
}

export function AiVideoAssets() {
  return <Shell><SimpleCollection title="素材库" items={['Logo 与水印', '商品图片', 'PPT / CSV / 网页链接', 'BGM 与音色参考']} /></Shell>
}

export function AiVideoBrandKit() {
  const [name, setName] = useState('默认品牌资产')
  const [kits, setKits] = useState<any[]>([])
  const load = () => aiVideoApi.brandKits().then(res => setKits(res.data as any[]))
  useEffect(() => { load() }, [])
  return (
    <Shell>
      <div className="ai-video-grid">
        <section className="ai-video-panel span-4">
          <h3>新建品牌资产</h3>
          <Input value={name} onChange={e => setName(e.target.value)} />
          <Button style={{ marginTop: 12 }} type="primary" onClick={async () => { await aiVideoApi.createBrandKit({ name, colors: ['#0f766e', '#2563eb', '#f59e0b'] }); load() }}>保存</Button>
        </section>
        <section className="ai-video-panel span-8">
          <h3>品牌资产</h3>
          <div className="project-list">{kits.map(kit => <div className="project-item" key={kit.id}><div className="project-thumb" /><strong>{kit.name}</strong><Tag>品牌语气 / 字幕 / 配音</Tag></div>)}</div>
        </section>
      </div>
    </Shell>
  )
}

export function AiVideoExports() {
  const [exports, setExports] = useState<AiVideoExport[]>([])
  useEffect(() => { aiVideoApi.exports().then(res => setExports(res.data)) }, [])
  return (
    <Shell>
      <div className="ai-video-panel">
        <h3>导出记录</h3>
        <div className="project-list">
          {exports.map(item => (
            <div className="project-item" key={item.id}>
              <div className="project-thumb" />
              <div>
                <strong>{item.title}</strong>
                <div><Tag>Version {item.versionNo}</Tag><Tag color={item.status === 'completed' ? 'green' : 'orange'}>{item.status}</Tag></div>
              </div>
              {item.outputUrl && <Button icon={<CloudDownloadOutlined />} href={resolveBackendUrl(item.outputUrl)}>下载</Button>}
            </div>
          ))}
          {!exports.length && <p>暂无导出记录。</p>}
        </div>
      </div>
    </Shell>
  )
}

export function AiVideoSettings() {
  const [capability, setCapability] = useState<AiVideoCapability | null>(null)
  const [motionEnabled, setMotionEnabled] = useState(true)
  useEffect(() => { aiVideoApi.capabilities().then(res => setCapability(res.data)) }, [])
  return (
    <Shell>
      <div className="ai-video-grid">
        <section className="ai-video-panel span-6">
          <h3>渲染服务</h3>
          <div className="status-grid">
            <div><strong>{capability?.renderService.available ? '可用' : '降级可用'}</strong><span>Remotion / CosyVoice</span></div>
            <div><strong>{capability?.ffmpeg.available ? '可用' : '不可用'}</strong><span>ffmpeg 安全降级</span></div>
            <div><strong>{capability?.limits.renderConcurrency || 1}</strong><span>渲染并发</span></div>
            <div><strong>{capability?.limits.cosyVoiceConcurrency || 1}</strong><span>配音并发</span></div>
          </div>
          {capability?.renderService.message && <p className="error-text">{capability.renderService.message}</p>}
        </section>
        <section className="ai-video-panel span-6">
          <h3>隔离与回滚</h3>
          <div className="stage-list">
            <div className="stage-item"><span className="stage-dot">1</span><strong>{capability?.isolation.apiNamespace || '/api/ai-video/*'}</strong></div>
            <div className="stage-item"><span className="stage-dot">2</span><strong>{capability?.isolation.frontendRoutes || '/ai-video/*'}</strong></div>
            <div className="stage-item"><span className="stage-dot">3</span><strong>{capability?.storageRoot || 'storage/ai-video/tasks'}</strong></div>
            <div className="stage-item"><span className="stage-dot">4</span><strong>关闭菜单入口和 API 路由即可回滚</strong></div>
          </div>
          <div className="setting-row"><span>粒子动效</span><Switch checked={motionEnabled} onChange={setMotionEnabled} /></div>
        </section>
      </div>
    </Shell>
  )
}

function SimpleCollection({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="ai-video-panel">
      <h3>{title}</h3>
      <div className="quick-types">
        {items.map(item => <div className="quick-type" key={item}><strong>{item.split(' · ')[0]}</strong><p>{item}</p></div>)}
      </div>
    </div>
  )
}

export default AiVideoDashboard
