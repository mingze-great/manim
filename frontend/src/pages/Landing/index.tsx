import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { Button, Card, Row, Col, Tag, Modal, Tabs, Spin } from 'antd'
import {
  ThunderboltOutlined,
  ArrowRightOutlined,
  RobotOutlined,
  DownloadOutlined,
  PlaySquareOutlined,
  SafetyCertificateOutlined,
  MessageOutlined,
  PlayCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '@/stores/authStore'
import { resolveBackendUrl } from '@/services/api'
import './Landing.css'

const ICP_NUMBER = '蜀ICP备2026016040号-2'
const BEIAN_URL = 'https://beian.miit.gov.cn/'

interface PublicTemplatePreview {
  id: number
  name: string
  description: string | null
  category: string | null
  thumbnail: string | null
  example_video_url: string | null
  is_system: boolean
}

const features = [
  { icon: <RobotOutlined />, title: '从选题到脚本', desc: '适合知识干货、商业认知、成长观点类账号，把普通想法整理成更有结构的视频表达。' },
  { icon: <PlaySquareOutlined />, title: '可视化动画呈现', desc: '结合思维可视化模板和动态画面，让内容不再只是文字堆叠或普通 PPT。' },
  { icon: <ThunderboltOutlined />, title: '云端渲染成片', desc: '在服务器完成渲染，减少本地配置和剪辑门槛，更适合想快速验证内容方向的创作者。' },
  { icon: <DownloadOutlined />, title: '适配多平台发布', desc: '成片可用于抖音、小红书、视频号等平台，帮助你更快做出同款内容样式。' },
]

const advantages = [
  '不要求懂代码或复杂剪辑软件',
  '重点优化开头吸引力和内容节奏',
  '适合做认知、商业、职场、成长类自媒体内容',
  '先看模板效果，再决定适合自己的视频风格',
]

const steps = [
  { num: '01', title: '主页加联系方式', desc: '从抖音主页添加联系方式，备注“同款视频”。' },
  { num: '02', title: '发选题或文案', desc: '可以发完整文案，也可以只发一个想做的主题。' },
  { num: '03', title: '确认视觉方向', desc: '参考模板样片，选择更适合账号定位的表现方式。' },
  { num: '04', title: '生成视频成片', desc: '云端生成并交付可下载的视频素材。' },
]

const workflowCards = [
  { title: '心理火柴人成片', desc: '输入主题或文案，一键生成心理学火柴人成片。', path: '/stickman-workflow', tag: '推荐', icon: <PlaySquareOutlined /> },
  { title: '工作流中心', desc: '按视频、文章、知识 IP 分类找到全部制作入口。', path: '/creator', tag: '全部入口', icon: <RobotOutlined /> },
  { title: 'AI 视频导演', desc: '管理脚本、镜头、素材和导出流程。', path: '/ai-video/dashboard', tag: '视频', icon: <PlayCircleOutlined />, adminOnly: true },
  { title: '文章内容工作流', desc: '生成公众号、小红书、长文内容并管理历史。', path: '/article', tag: '图文', icon: <MessageOutlined /> },
  { title: '知识 IP 包装', desc: '围绕账号定位整理内容结构和表达方式。', path: '/knowledge-ip', tag: '定位', icon: <SafetyCertificateOutlined />, adminOnly: true },
  { title: '我的作品', desc: '查看生成记录、下载视频和继续编辑。', path: '/history', tag: '管理', icon: <DownloadOutlined /> },
]

function inferTemplateCategory(template: PublicTemplatePreview) {
  const category = String(template.category || '').toLowerCase()
  const text = `${template.name || ''} ${template.description || ''}`
  if (category.includes('math') || text.includes('数学')) return 'math'
  if (category.includes('thinking') || category.includes('mind') || text.includes('思维') || text.includes('认知') || text.includes('闭环')) return 'thinking'
  return 'other'
}

function getVideoUrl(template: PublicTemplatePreview | null) {
  if (!template?.example_video_url) return ''
  return resolveBackendUrl(template.example_video_url)
}

export default function Landing() {
  const navigate = useNavigate()
  const { token, user } = useAuthStore()
  const [templates, setTemplates] = useState<PublicTemplatePreview[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(true)
  const [previewTemplate, setPreviewTemplate] = useState<PublicTemplatePreview | null>(null)

  const scrollToContact = () => {
    document.getElementById('contact-trial')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const scrollToPreview = () => {
    document.getElementById('template-preview')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const handleStart = () => {
    if (token) {
      navigate('/creator')
    } else {
      scrollToContact()
    }
  }

  const openWorkflow = (path: string) => {
    if (!token) {
      navigate('/login')
      return
    }
    navigate(path)
  }

  useEffect(() => {
    let mounted = true
    fetch('/api/templates/public-preview?limit=200')
      .then(response => response.ok ? response.json() : Promise.reject(new Error(String(response.status))))
      .then(data => {
        if (!mounted) return
        const items = Array.isArray(data?.templates) ? data.templates : []
        setTemplates(items.filter((item: PublicTemplatePreview) => item.example_video_url))
      })
      .catch(() => {
        if (mounted) setTemplates([])
      })
      .finally(() => {
        if (mounted) setTemplatesLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  const groupedTemplates = useMemo(() => {
    const groups = {
      all: templates,
      thinking: templates.filter(item => inferTemplateCategory(item) === 'thinking'),
      math: templates.filter(item => inferTemplateCategory(item) === 'math'),
      other: templates.filter(item => inferTemplateCategory(item) === 'other'),
    }
    return groups
  }, [templates])

  const visibleWorkflowCards = useMemo(
    () => workflowCards.filter(item => !item.adminOnly || user?.is_admin),
    [user?.is_admin],
  )

  const tabs = [
    { key: 'all', label: `全部模板 ${groupedTemplates.all.length}`, items: groupedTemplates.all },
    { key: 'thinking', label: `思维可视化 ${groupedTemplates.thinking.length}`, items: groupedTemplates.thinking },
    { key: 'math', label: `数学参考 ${groupedTemplates.math.length}`, items: groupedTemplates.math },
    { key: 'other', label: `其他 ${groupedTemplates.other.length}`, items: groupedTemplates.other },
  ].filter(tab => tab.items.length > 0 || tab.key === 'all')

  const renderPreviewGrid = (items: PublicTemplatePreview[]) => {
    if (templatesLoading) return <div className="preview-loading"><Spin /> <span>模板样片加载中</span></div>
    if (!items.length) return <div className="preview-empty">模板样片正在整理中，稍后会展示更多效果。</div>
    return (
      <div className="showcase-card-row landing-showcase-row">
        {items.map(template => (
          <article className="showcase-card landing-showcase-card" key={template.id}>
            <div className="showcase-card-video">
              <video
                src={getVideoUrl(template)}
                muted
                loop
                playsInline
                preload="metadata"
                className="showcase-video"
                onMouseEnter={event => event.currentTarget.play().catch(() => undefined)}
                onMouseLeave={event => {
                  event.currentTarget.pause()
                  event.currentTarget.currentTime = 0
                }}
              />
              <button className="showcase-card-overlay landing-preview-overlay" type="button" onClick={() => setPreviewTemplate(template)}>
                <PlayCircleOutlined className="showcase-play-icon" />
                <span>查看完整示例</span>
              </button>
              <div className="preview-mask"><EyeOutlined /><span>仅预览</span></div>
            </div>
            <div className="showcase-card-info">
              <div className="showcase-card-name">{template.name}</div>
              {template.description && <div className="showcase-card-desc">{template.description}</div>}
            </div>
          </article>
        ))}
      </div>
    )
  }

  return (
    <div className="landing-page product-landing">
      <header className="landing-header">
        <div className="container">
          <div className="header-content">
            <div className="logo">
              <div className="logo-icon">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" /></svg>
              </div>
              <span>思维可视化</span>
            </div>
            <nav className="header-nav">
              <a href="#features">优势</a>
              <a href="#template-preview">模板预览</a>
              <a href="#contact-trial">试用方式</a>
              <Link to="/docs">帮助</Link>
            </nav>
            <div className="header-actions">
              {token ? (
                <Button type="primary" onClick={() => navigate('/creator')}>进入工作台</Button>
              ) : (
                <>
                  <Button onClick={() => navigate('/login')}>登录</Button>
                  <Button type="primary" onClick={scrollToContact}>申请试用</Button>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      <section className="hero-section product-hero">
        <div className="container">
          <div className="hero-content">
            <div className="hero-kicker">For creators · 知识型短视频生产力</div>
            <h1 className="hero-title">想做同款视频<br /><span className="gradient-text">先从思维可视化开始</span></h1>
            <p className="hero-desc">面向自媒体创作者的思维可视化视频工具。你可以从一个选题、一段文案或一个账号方向开始，逐步生成脚本、动画画面和可发布的视频素材。</p>
            <div className="hero-actions">
              <Button type="primary" size="large" onClick={handleStart}>
                {token ? '进入工作台' : '主页加联系方式试用'}<ArrowRightOutlined />
              </Button>
              {!token && <Button size="large" onClick={() => navigate('/login')}>已有账号，直接登录</Button>}
              <Button size="large" onClick={scrollToPreview}>先看模板效果</Button>
            </div>
            <div className="hero-proof"><span>爆款开头</span><span>脚本结构</span><span>动态画面</span><span>云端渲染</span></div>
          </div>
        </div>
        <div className="hero-bg"><div className="gradient-orb orb-1" /><div className="gradient-orb orb-2" /><div className="grid-pattern" /></div>
      </section>

      <section className="workflow-entry-section">
        <div className="container">
          <div className="section-header">
            <h2>选择一个工作流，直接开始制作</h2>
            <p>把平台能力按制作任务重新组织：先选工作流，再进入对应制作页，原有模块逻辑保持不变。</p>
          </div>
          <div className="workflow-entry-grid">
            {visibleWorkflowCards.map(item => (
              <button className="workflow-entry-card" key={item.path} type="button" onClick={() => openWorkflow(item.path)}>
                <span className="workflow-entry-icon">{item.icon}</span>
                <span className="workflow-entry-copy">
                  <strong>{item.title}</strong>
                  <em>{item.desc}</em>
                </span>
                <Tag color={item.tag === '推荐' ? 'blue' : 'default'}>{item.tag}</Tag>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="features-section" id="features">
        <div className="container">
          <div className="section-header"><h2>不是普通模板站，而是更适合自媒体的成片工作流</h2><p>让不会剪辑、不会代码的人，也能更快做出有记忆点的视频。</p></div>
          <Row gutter={[24, 24]}>
            {features.map((f, i) => (
              <Col xs={24} sm={12} lg={6} key={i}>
                <Card className="feature-card product-card"><div className="feature-icon">{f.icon}</div><h3>{f.title}</h3><p>{f.desc}</p></Card>
              </Col>
            ))}
          </Row>
          <div className="advantage-strip">
            {advantages.map(item => <div className="advantage-item" key={item}><SafetyCertificateOutlined /><span>{item}</span></div>)}
          </div>
        </div>
      </section>

      <section className="template-preview-section" id="template-preview">
        <div className="container">
          <div className="section-header"><h2>先看效果，再决定想做哪种风格</h2><p>这里展示脚本生成部分同款模板样片，仅支持预览，不提供使用入口。</p></div>
          <div className="landing-template-showcase">
            <Tabs
              defaultActiveKey="all"
              items={tabs.map(tab => ({
                key: tab.key,
                label: tab.label,
                children: renderPreviewGrid(tab.items),
              }))}
            />
          </div>
        </div>
      </section>

      <section className="how-it-works" id="how-it-works">
        <div className="container">
          <div className="section-header"><h2>试用流程很简单</h2><p>不用先研究工具，先把你想做的内容发过来。</p></div>
          <div className="steps-wrapper">
            {steps.map((s, i) => (
              <div className="step-item" key={s.num}><div className="step-num">{s.num}</div><h4>{s.title}</h4><p>{s.desc}</p>{i < steps.length - 1 && <div className="step-line" />}</div>
            ))}
          </div>
        </div>
      </section>

      <section className="cta-section contact-section" id="contact-trial">
        <div className="container">
          <div className="cta-content contact-card">
            <div className="contact-icon"><MessageOutlined /></div>
            <h2>想做同款视频，先加主页联系方式试用</h2>
            <p>从抖音主页添加联系方式，备注“同款视频”。你可以发选题、账号定位或一段文案，我会按你的内容方向匹配适合的脚本结构和视觉风格。</p>
            <div className="contact-tags"><Tag>知识干货</Tag><Tag>商业认知</Tag><Tag>人设观点</Tag><Tag>带货讲解</Tag></div>
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="container">
          <div className="footer-content">
            <div className="footer-brand">
              <div className="logo"><div className="logo-icon"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" /></svg></div><span>思维可视化</span></div>
              <p>面向自媒体创作者的思维可视化视频生产工具。</p>
            </div>
            <div className="footer-links">
              <div className="link-group"><h4>产品</h4><a href="#features">产品优势</a><a href="#template-preview">模板预览</a></div>
              <div className="link-group"><h4>支持</h4><Link to="/docs">帮助中心</Link><a href="#contact-trial">申请试用</a></div>
            </div>
          </div>
          <div className="footer-bottom"><p>&copy; 2026 思维可视化. All rights reserved.</p><a href={BEIAN_URL} target="_blank" rel="noreferrer">{ICP_NUMBER}</a></div>
        </div>
      </footer>

      <Modal
        open={!!previewTemplate}
        onCancel={() => setPreviewTemplate(null)}
        footer={null}
        width={860}
        title={previewTemplate?.name}
        className="showcase-preview-modal landing-preview-modal"
      >
        {previewTemplate && getVideoUrl(previewTemplate) && (
          <video src={getVideoUrl(previewTemplate)} controls autoPlay className="showcase-preview-video landing-modal-video" />
        )}
        {previewTemplate?.description && <p className="showcase-preview-desc">{previewTemplate.description}</p>}
      </Modal>
    </div>
  )
}
