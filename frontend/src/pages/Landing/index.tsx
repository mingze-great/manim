import { useNavigate } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { Button, Card, Row, Col, Badge, Avatar, Tag } from 'antd'
import {
  PlayCircleOutlined, CodeOutlined, ThunderboltOutlined,
  CheckCircleOutlined, ArrowRightOutlined, StarOutlined,
  RobotOutlined, DownloadOutlined
} from '@ant-design/icons'
import { useAuthStore } from '@/stores/authStore'
import './Landing.css'

const features = [
  {
    icon: <RobotOutlined />,
    title: 'AI 智能对话',
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
    desc: '告诉 AI 你想要的视频内容',
  },
  {
    num: '02',
    title: '对话优化',
    desc: '通过多轮对话完善内容细节',
  },
  {
    num: '03',
    title: '生成代码',
    desc: 'AI 自动生成 Manim 动画代码',
  },
  {
    num: '04',
    title: '渲染视频',
    desc: '云端渲染，生成最终视频',
  },
]

const pricingPlans = [
  {
    name: '免费版',
    price: '0',
    features: ['每日 100 次额度', '基础模板库', '标清导出', '社区支持'],
    current: true,
  },
  {
    name: '专业版',
    price: '99',
    features: ['每日 1000 次额度', '高级模板库', '高清导出', '优先渲染', '技术支持'],
    popular: true,
  },
  {
    name: '企业版',
    price: '399',
    features: ['无限额度', '私有模板库', '4K 导出', '专属客服', 'API 接口', '定制服务'],
  },
]

const testimonials = [
  {
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Felix',
    name: '李老师',
    title: '数学教师',
    content: '用 Manim 制作数学动画太方便了，课堂效果提升明显！',
  },
  {
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Aneka',
    name: '王同学',
    title: '大学生',
    content: '毕业设计需要动画效果，这个工具帮了大忙。',
  },
  {
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Bob',
    name: '张博士',
    title: '科研人员',
    content: '论文配图制作效率大幅提升，学术成果展示更专业。',
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
              <span>Manim</span>
            </div>
            <nav className="header-nav">
              <a href="#features">功能</a>
              <a href="#how-it-works">如何使用</a>
              <a href="#pricing">价格</a>
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
                    免费试用
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
            <Badge count={<Tag color="gold">v2.0 全新发布</Tag>} offset={[50, 0]}>
              <h1 className="hero-title">
                用 AI 轻松创作<br />
                <span className="gradient-text">专业级数学动画</span>
              </h1>
            </Badge>
            <p className="hero-desc">
              输入视频主题，AI 帮你完成创意策划、代码生成、视频渲染全流程。
              无需编程基础，人人都能制作专业的数学动画。
            </p>
            <div className="hero-actions">
              <Button type="primary" size="large" onClick={handleStart}>
                立即开始
                <ArrowRightOutlined />
              </Button>
              <Button size="large" onClick={() => navigate('/login')}>
                <PlayCircleOutlined /> 观看演示
              </Button>
            </div>
            <div className="hero-stats">
              <div className="stat-item">
                <span className="stat-num">50,000+</span>
                <span className="stat-label">用户</span>
              </div>
              <div className="stat-item">
                <span className="stat-num">200,000+</span>
                <span className="stat-label">视频生成</span>
              </div>
              <div className="stat-item">
                <span className="stat-num">99.9%</span>
                <span className="stat-label">服务可用性</span>
              </div>
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
            <p>一站式 AI 动画创作平台</p>
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

      {/* Pricing */}
      <section className="pricing-section" id="pricing">
        <div className="container">
          <div className="section-header">
            <h2>灵活的套餐方案</h2>
            <p>选择适合你的创作方案</p>
          </div>
          <Row gutter={[24, 24]} justify="center">
            {pricingPlans.map((p, i) => (
              <Col xs={24} sm={12} lg={8} key={i}>
                <Card className={`pricing-card ${p.popular ? 'popular' : ''}`}>
                  {p.popular && <div className="popular-tag">最受欢迎</div>}
                  <h3>{p.name}</h3>
                  <div className="price">
                    <span className="currency">¥</span>
                    <span className="amount">{p.price}</span>
                    <span className="period">/月</span>
                  </div>
                  <ul className="feature-list">
                    {p.features.map((f, j) => (
                      <li key={j}>
                        <CheckCircleOutlined /> {f}
                      </li>
                    ))}
                  </ul>
                  <Button
                    type={p.popular ? 'primary' : 'default'}
                    block
                    size="large"
                    onClick={() => navigate('/register')}
                  >
                    {p.current ? '当前方案' : '立即开通'}
                  </Button>
                </Card>
              </Col>
            ))}
          </Row>
        </div>
      </section>

      {/* Testimonials */}
      <section className="testimonials-section">
        <div className="container">
          <div className="section-header">
            <h2>用户评价</h2>
            <p>听听他们怎么说</p>
          </div>
          <Row gutter={[24, 24]}>
            {testimonials.map((t, i) => (
              <Col xs={24} lg={8} key={i}>
                <Card className="testimonial-card">
                  <div className="testimonial-header">
                    <Avatar src={t.avatar} size={48} />
                    <div>
                      <div className="testimonial-name">{t.name}</div>
                      <div className="testimonial-title">{t.title}</div>
                    </div>
                    <div className="testimonial-rating">
                      {[1, 2, 3, 4, 5].map((s) => (
                        <StarOutlined key={s} />
                      ))}
                    </div>
                  </div>
                  <p className="testimonial-content">{t.content}</p>
                </Card>
              </Col>
            ))}
          </Row>
        </div>
      </section>

      {/* CTA */}
      <section className="cta-section">
        <div className="container">
          <div className="cta-content">
            <h2>准备好开始创作了吗？</h2>
            <p>免费注册，立即体验 AI 动画创作</p>
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
                <span>Manim</span>
              </div>
              <p>用 AI 赋能数学动画创作</p>
            </div>
            <div className="footer-links">
              <div className="link-group">
                <h4>产品</h4>
                <a href="#features">功能介绍</a>
                <a href="#pricing">价格方案</a>
                <Link to="/docs">使用文档</Link>
              </div>
              <div className="link-group">
                <h4>支持</h4>
                <Link to="/docs">帮助中心</Link>
                <Link to="/docs">常见问题</Link>
                <a href="#">联系我们</a>
              </div>
              <div className="link-group">
                <h4>法律</h4>
                <a href="#">服务条款</a>
                <a href="#">隐私政策</a>
              </div>
            </div>
          </div>
          <div className="footer-bottom">
            <p>&copy; 2024 Manim Video Platform. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
