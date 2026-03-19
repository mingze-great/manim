import { Card, Collapse, Typography, Space, Tag, Button, Breadcrumb, Row, Col } from 'antd'
import { 
  BookOutlined, PlayCircleOutlined, CodeOutlined, VideoCameraOutlined,
  ArrowRightOutlined, FileTextOutlined, CustomerServiceOutlined, RobotOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import './Docs.css'

const { Title, Text, Paragraph } = Typography
const { Panel } = Collapse

const quickStart = [
  {
    title: '创建你的第一个动画',
    icon: <PlayCircleOutlined />,
    steps: [
      '点击"开始创作"进入创作工作台',
      '点击"新建项目"创建一个新项目',
      '输入你想要制作的动画主题',
      '与 AI 对话完善你的想法',
      '等待代码生成完成',
      '点击"开始渲染"生成视频',
    ],
  },
]

const tutorials = [
  {
    category: '入门教程',
    icon: <BookOutlined />,
    color: '#6366f1',
    items: [
      {
        title: '快速开始',
        desc: '5分钟创建你的第一个数学动画',
        duration: '5分钟',
        level: '入门',
      },
      {
        title: '界面介绍',
        desc: '了解创作工作台的各个功能区',
        duration: '3分钟',
        level: '入门',
      },
      {
        title: '基本操作',
        desc: '如何与 AI 对话生成脚本',
        duration: '5分钟',
        level: '入门',
      },
    ],
  },
  {
    category: '进阶教程',
    icon: <CodeOutlined />,
    color: '#8b5cf6',
    items: [
      {
        title: '自定义代码',
        desc: '在生成后修改和优化 Manim 代码',
        duration: '10分钟',
        level: '进阶',
      },
      {
        title: '使用模板',
        desc: '利用现有模板快速创建动画',
        duration: '5分钟',
        level: '进阶',
      },
      {
        title: '调试技巧',
        desc: '常见代码错误及解决方法',
        duration: '15分钟',
        level: '进阶',
      },
    ],
  },
  {
    category: '特效教程',
    icon: <VideoCameraOutlined />,
    color: '#f59e0b',
    items: [
      {
        title: '数学公式动画',
        desc: '创建美观的数学公式展示',
        duration: '8分钟',
        level: '进阶',
      },
      {
        title: '几何图形变换',
        desc: '多边形、圆形等图形的动画效果',
        duration: '10分钟',
        level: '进阶',
      },
      {
        title: '函数图像绘制',
        desc: '让函数曲线动态绘制出来',
        duration: '12分钟',
        level: '进阶',
      },
    ],
  },
]

const faqs = [
  {
    question: '什么是 Manim？',
    answer: 'Manim 是一个用于创建数学动画的 Python 库，由 3Blue1Brown 创建。它可以制作高质量的数学教学视频。本平台通过 AI 对话的方式，让用户无需编程基础也能创建 Manim 动画。',
  },
  {
    question: '需要编程基础吗？',
    answer: '不需要。本平台通过自然语言与 AI 对话，自动生成 Manim 代码。你只需要描述你想要的效果，AI 会帮你完成代码编写。',
  },
  {
    question: '视频导出支持哪些格式？',
    answer: '目前支持 MP4 格式导出。可以在设置中选择不同的画质（720p、1080p、4K）。',
  },
  {
    question: '每日额度用完了怎么办？',
    answer: '免费用户每日有 100 次 AI 对话额度。你可以通过升级付费套餐获取更多额度，或者等待次日额度重置。',
  },
  {
    question: '生成的视频可以商用吗？',
    answer: '使用本平台生成的视频版权归用户所有，可以用于个人或商业用途。但请注意，生成的代码基于 MIT 协议的 Manim 库。',
  },
  {
    question: '渲染需要多长时间？',
    answer: '渲染时间取决于视频复杂度和服务器负载。简单的动画通常在 1-3 分钟内完成，复杂的可能需要 10 分钟以上。',
  },
]

const concepts = [
  {
    title: '场景 (Scene)',
    icon: <VideoCameraOutlined />,
    desc: '视频的基本单元，每个场景包含一组动画元素',
  },
  {
    title: '物体 (Mobject)',
    icon: <BookOutlined />,
    desc: '可以被创建和动画化的对象，如文字、图形等',
  },
  {
    title: '动画 (Animation)',
    icon: <PlayCircleOutlined />,
    desc: '物体从一种状态到另一种状态的变化过程',
  },
  {
    title: '脚本 (Script)',
    icon: <FileTextOutlined />,
    desc: '描述视频内容、镜头切换和旁白的文档',
  },
]

export default function Docs() {
  const navigate = useNavigate()

  return (
    <div className="docs-page">
      <div className="docs-header">
        <div className="container">
          <Breadcrumb
            items={[
              { title: '首页' },
              { title: '帮助中心' },
            ]}
          />
          <Title level={2} className="mt-4">帮助中心</Title>
          <Text type="secondary" className="docs-subtitle">
            了解如何使用 Manim 视频平台创建精彩的数学动画
          </Text>
        </div>
      </div>

      <div className="container docs-content">
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={16}>
            <section className="docs-section">
              <Title level={4}><BookOutlined /> 快速开始</Title>
              <Card className="quick-start-card">
                {quickStart.map((item, index) => (
                  <div key={index}>
                    <div className="quick-start-header">
                      <span className="quick-start-icon">{item.icon}</span>
                      <span className="quick-start-title">{item.title}</span>
                    </div>
                    <ol className="quick-start-steps">
                      {item.steps.map((step, i) => (
                        <li key={i}>
                          <span className="step-num">{i + 1}</span>
                          <span className="step-text">{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                ))}
                <Button 
                  type="primary" 
                  size="large" 
                  icon={<PlayCircleOutlined />}
                  onClick={() => navigate('/creator')}
                  className="mt-4"
                >
                  开始创作
                </Button>
              </Card>
            </section>

            <section className="docs-section">
              <Title level={4}>教程分类</Title>
              <Row gutter={[16, 16]}>
                {tutorials.map((category, index) => (
                  <Col xs={24} md={8} key={index}>
                    <Card className="tutorial-category-card hover-lift">
                      <div className="category-header" style={{ background: `${category.color}1a` }}>
                        <span style={{ color: category.color }}>{category.icon}</span>
                        <span className="category-title">{category.category}</span>
                      </div>
                      <div className="tutorial-list">
                        {category.items.map((tutorial, i) => (
                          <div key={i} className="tutorial-item">
                            <div className="tutorial-info">
                              <span className="tutorial-title">{tutorial.title}</span>
                              <Text type="secondary" className="tutorial-desc">{tutorial.desc}</Text>
                            </div>
                            <div className="tutorial-meta">
                              <Tag>{tutorial.level}</Tag>
                              <Text type="secondary" className="tutorial-duration">{tutorial.duration}</Text>
                            </div>
                          </div>
                        ))}
                      </div>
                    </Card>
                  </Col>
                ))}
              </Row>
            </section>

            <section className="docs-section">
              <Title level={4}>常见问题</Title>
              <Card>
                <Collapse defaultActiveKey={['0']} ghost>
                  {faqs.map((faq, index) => (
                    <Panel header={<Text strong>{faq.question}</Text>} key={index}>
                      <Paragraph className="mb-0">{faq.answer}</Paragraph>
                    </Panel>
                  ))}
                </Collapse>
              </Card>
            </section>
          </Col>

          <Col xs={24} lg={8}>
            <section className="docs-section">
              <Title level={4}>核心概念</Title>
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {concepts.map((concept, index) => (
                  <Card key={index} className="concept-card hover-lift">
                    <Space>
                      <div className="concept-icon">{concept.icon}</div>
                      <div>
                        <Text strong>{concept.title}</Text>
                        <br />
                        <Text type="secondary" className="text-sm">{concept.desc}</Text>
                      </div>
                    </Space>
                  </Card>
                ))}
              </Space>
            </section>

            <section className="docs-section">
              <Title level={4}>相关链接</Title>
              <Card>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Button block icon={<BookOutlined />} onClick={() => window.open('https://docs.manim.community/', '_blank')}>
                    Manim 官方文档
                  </Button>
                  <Button block icon={<RobotOutlined />} onClick={() => window.open('https://github.com/3b1b/manim', '_blank')}>
                    Manim GitHub
                  </Button>
                  <Button block icon={<CustomerServiceOutlined />} onClick={() => navigate('/pricing')}>
                    查看定价方案
                  </Button>
                </Space>
              </Card>
            </section>

            <section className="docs-section">
              <Card className="contact-card">
                <div className="contact-header">
                  <RobotOutlined style={{ fontSize: '32px', color: '#6366f1' }} />
                  <Title level={5} className="mt-3 mb-2">需要更多帮助？</Title>
                  <Text type="secondary">联系我们的技术支持团队</Text>
                </div>
                <Button type="primary" block className="mt-3">
                  联系客服 <ArrowRightOutlined />
                </Button>
              </Card>
            </section>
          </Col>
        </Row>
      </div>
    </div>
  )
}
