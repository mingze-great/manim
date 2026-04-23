import { useNavigate, Link } from 'react-router-dom'
import { Button, Card, Row, Col } from 'antd'
import {
  ThunderboltOutlined,
  ArrowRightOutlined,
  RobotOutlined,
  DownloadOutlined,
  PlaySquareOutlined,
  FireOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '@/stores/authStore'
import { ChallengeStrip, GuidedHero, SectionShell, StepRail, TipCard } from '@/components/GuidedExperience'
import './Landing.css'

const features = [
  {
    icon: <RobotOutlined />,
    title: '一步步陪你打磨内容',
    desc: '不是直接丢给你一个空白输入框，而是通过提示把要求慢慢补全。',
  },
  {
    icon: <PlaySquareOutlined />,
    title: '模板与脚本自动衔接',
    desc: '确认内容后自动进入模板和脚本阶段，不需要自己研究代码。',
  },
  {
    icon: <ThunderboltOutlined />,
    title: '云端渲染直接出片',
    desc: '脚本准备好后直接发起渲染，系统会持续告诉你当前状态。',
  },
  {
    icon: <DownloadOutlined />,
    title: '成片可预览可下载',
    desc: '渲染完成即可预览完整视频、下载成片，或继续回去优化。',
  },
]

const steps = [
  { title: '选择模块', desc: '先决定是思维讲解、数学推演还是火柴人视频。' },
  { title: '补全要求', desc: '系统会一步步告诉你还缺什么，不会也能继续。' },
  { title: '生成脚本', desc: '模板、风格、模型选择都在提示下完成。' },
  { title: '渲染成片', desc: '完成渲染后直接预览和下载，不需要技术背景。' },
]

export default function Landing() {
  const navigate = useNavigate()
  const { token } = useAuthStore()

  const handleStart = () => {
    if (token) {
      navigate('/creator')
    } else {
      navigate('/login')
    }
  }

  return (
    <div className="landing-page premium-dark-page">
      <header className="landing-header">
        <div className="container">
          <div className="header-content">
            <div className="logo">
              <div className="logo-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
              </div>
              <span>思维可视化</span>
            </div>
            <nav className="header-nav">
              <a href="#features">功能</a>
              <a href="#how-it-works">如何使用</a>
              <Link to="/docs">帮助</Link>
            </nav>
            <div className="header-actions">
              <Button className="landing-workbench-btn" onClick={handleStart}>
                {token ? '进入工作台' : '立即开始'}
                <ArrowRightOutlined />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <section className="hero-section">
        <div className="container">
          <GuidedHero
            eyebrow="零基础也能完成的思维可视化工作流"
            title="思维可视化动画"
            description="输入视频主题，系统会一步一步带你完成创意策划、对话打磨、脚本生成与视频渲染。就算你从没做过视频，也能按提示做出第一条成片。"
            actions={
              <>
                <Button type="primary" size="large" className="btn-gradient" onClick={handleStart}>
                  立即开始
                  <ArrowRightOutlined />
                </Button>
                <Button size="large" className="challenge-chip" onClick={handleStart}>
                  <FireOutlined /> 挑战：3 分钟出第一版
                </Button>
              </>
            }
          />
        </div>
        <div className="hero-bg">
          <div className="gradient-orb orb-1" />
          <div className="gradient-orb orb-2" />
          <div className="grid-pattern" />
        </div>
      </section>

      <section className="features-section" id="features">
        <div className="container landing-stack">
          <StepRail title="第一次来也能照着做" subtitle="系统会在每一步告诉你当前在做什么、下一步该点哪里。" steps={steps} active={0} />
          <div className="section-header">
            <h2>强大的功能，让创作更简单</h2>
            <p>不只是提供工具，而是把从主题到成片的路径设计清楚。</p>
          </div>
          <Row gutter={[24, 24]}>
            {features.map((f, i) => (
              <Col xs={24} sm={12} lg={6} key={i}>
                <Card className="feature-card">
                  <div className="feature-icon">{f.icon}</div>
                  <h3>{f.title}</h3>
                  <p>{f.desc}</p>
                </Card>
              </Col>
            ))}
          </Row>
        </div>
      </section>

      <section className="how-it-works" id="how-it-works">
        <div className="container landing-stack">
          <div className="landing-grid-three">
            <TipCard title="新手推荐路径" tone="gold">
              先从思维可视化开始，使用热门方向选题，再按照页面提示补全要求，通常最容易做出第一版视频。
            </TipCard>
            <TipCard title="你会得到什么" tone="soft">
              每个关键页面都会明确告诉你：当前步骤、下一步动作，以及不会做时的推荐按钮。
            </TipCard>
            <TipCard title="适合哪些用户" tone="soft">
              既适合完全没基础的新手，也适合已经有脚本思路、想更快出片的内容创作者。
            </TipCard>
          </div>
          <ChallengeStrip
            title="不想从空白开始？直接用推荐动作启动"
            actions={
              <>
                <Button className="challenge-chip" onClick={handleStart}>挑战：先做思维讲解</Button>
                <Button className="challenge-chip" onClick={handleStart}>挑战：直接试数学动画</Button>
                <Button className="challenge-chip" onClick={handleStart}>挑战：快速体验成片流程</Button>
              </>
            }
          />
        </div>
      </section>

      <section className="cta-section">
        <div className="container">
          <SectionShell>
            <div className="cta-content">
              <h2>准备好进入工作流了吗？</h2>
              <p>从选择模块到渲染成片，系统会始终给你明确提示，让第一次使用也能顺利完成。</p>
              <div className="hero-actions">
                <Button type="primary" size="large" className="btn-gradient" onClick={handleStart}>
                  进入工作台
                  <ArrowRightOutlined />
                </Button>
                <Button size="large" className="challenge-chip" onClick={() => navigate('/docs')}>
                  查看新手说明
                </Button>
              </div>
            </div>
          </SectionShell>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="container">
          <div className="footer-content">
            <div className="footer-brand">
              <div className="logo">
                <div className="logo-icon">
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                  </svg>
                </div>
                <span>思维可视化</span>
              </div>
              <p>赋能零基础用户完成从主题到视频的完整创作流程。</p>
            </div>
            <div className="footer-links">
              <div className="link-group">
                <h4>产品</h4>
                <a href="#features">功能介绍</a>
                <Link to="/docs">使用文档</Link>
              </div>
              <div className="link-group">
                <h4>支持</h4>
                <Link to="/docs">帮助中心</Link>
                <Link to="/docs">常见问题</Link>
              </div>
            </div>
          </div>
          <div className="footer-bottom">
            <p>&copy; 2024 思维可视化平台. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
