import { useNavigate } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { Button, Card, Row, Col } from 'antd'
import {
  CodeOutlined, ThunderboltOutlined,
  ArrowRightOutlined,
  RobotOutlined, DownloadOutlined
} from '@ant-design/icons'
import { useAuthStore } from '@/stores/authStore'
import './Landing.css'

const features = [
  {
    icon: <RobotOutlined />,
    title: '智能对话',
    desc: '与大模型多轮对话，不断优化视频主题与内容',
  },
  {
    icon: <CodeOutlined />,
    title: '自动代码生成',
    desc: '一键生成专业级 Manim 动画代码，无需编程基础',
  },
  {
    icon: <ThunderboltOutlined />,
    title: '云端渲染',
    desc: '强大算力支持，快速生成高清视频',
  },
  {
    icon: <DownloadOutlined />,
    title: '一键下载',
    desc: '支持多种格式导出，灵活适配不同场景',
  },
]

const steps = [
  {
    num: '01',
    title: '输入主题',
    desc: '输入你想要的视频内容',
  },
  {
    num: '02',
    title: '智能生成',
    desc: '根据主题生成完整内容',
  },
  {
    num: '03',
    title: '确认内容',
    desc: '输入"满意"确认，开始生成视频',
  },
  {
    num: '04',
    title: '渲染下载',
    desc: '云端渲染，生成最终视频',
  },
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
    <div className="landing-page">
      {/* Navbar */}
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
              {token ? (
                <Button type="primary" onClick={() => navigate('/creator')}>
                  进入工作台
                </Button>
              ) : (
                <>
                  <Button onClick={() => navigate('/login')}>登录</Button>
                  <Button type="primary" onClick={() => navigate('/register')}>
                    注册
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="container">
          <div className="hero-content">
            <h1 className="hero-title">
              轻松创作<br />
              <span className="gradient-text">思维可视化动画</span>
            </h1>
            <p className="hero-desc">
              输入视频主题，帮你完成创意策划、代码生成、视频渲染全流程。
              无需编程基础，人人都能制作专业的思维可视化动画。
            </p>
            <div className="hero-actions">
              <Button type="primary" size="large" onClick={handleStart}>
                立即开始
                <ArrowRightOutlined />
              </Button>
            </div>
          </div>
        </div>
        <div className="hero-bg">
          <div className="gradient-orb orb-1" />
          <div className="gradient-orb orb-2" />
          <div className="grid-pattern" />
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section" id="features">
        <div className="container">
          <div className="section-header">
            <h2>强大的功能，让创作更简单</h2>
            <p>一站式思维可视化创作平台</p>
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

      {/* How it Works */}
      <section className="how-it-works" id="how-it-works">
        <div className="container">
          <div className="section-header">
            <h2>简单四步，创作精彩动画</h2>
            <p>从创意到成品，一气呵成</p>
          </div>
          <div className="steps-wrapper">
            {steps.map((s, i) => (
              <div className="step-item" key={i}>
                <div className="step-num">{s.num}</div>
                <h4>{s.title}</h4>
                <p>{s.desc}</p>
                {i < steps.length - 1 && <div className="step-line" />}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta-section">
        <div className="container">
          <div className="cta-content">
            <h2>准备好开始创作了吗？</h2>
            <p>注册账号，立即体验思维可视化创作</p>
            <Button type="primary" size="large" onClick={handleStart}>
              立即开始
              <ArrowRightOutlined />
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
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
              <p>赋能思维可视化动画创作</p>
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
