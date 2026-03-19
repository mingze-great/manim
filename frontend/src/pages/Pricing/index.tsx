import { Card, Row, Col, Button, Typography, Divider, List } from 'antd'
import { 
  CheckCircleOutlined, CrownOutlined, RocketOutlined, ThunderboltOutlined,
  VideoCameraOutlined, HddOutlined, ToolOutlined, CustomerServiceOutlined
} from '@ant-design/icons'
import './Pricing.css'

const { Title, Text } = Typography

const plans = [
  {
    name: '免费版',
    price: 0,
    icon: <RocketOutlined />,
    color: '#6b7280',
    description: '适合个人学习和体验',
    features: [
      { text: '每日 100 次额度', included: true },
      { text: '基础模板库', included: true },
      { text: '标清视频导出', included: true },
      { text: '社区支持', included: true },
      { text: '高级模板库', included: false },
      { text: '高清视频导出', included: false },
      { text: '优先渲染队列', included: false },
      { text: 'API 接口', included: false },
    ],
    buttonText: '当前方案',
    buttonType: 'default',
  },
  {
    name: '专业版',
    price: 99,
    icon: <CrownOutlined />,
    color: '#6366f1',
    description: '适合创作者和专业用户',
    popular: true,
    features: [
      { text: '每日 1000 次额度', included: true },
      { text: '高级模板库', included: true },
      { text: '高清视频导出', included: true },
      { text: '优先渲染队列', included: true },
      { text: '技术支持', included: true },
      { text: '私有模板', included: false },
      { text: '4K 视频导出', included: false },
      { text: 'API 接口', included: false },
    ],
    buttonText: '立即开通',
    buttonType: 'primary',
  },
  {
    name: '企业版',
    price: 399,
    icon: <ThunderboltOutlined />,
    color: '#f59e0b',
    description: '适合团队和企业用户',
    features: [
      { text: '无限额度', included: true },
      { text: '私有模板库', included: true },
      { text: '4K 视频导出', included: true },
      { text: '专属渲染节点', included: true },
      { text: 'API 接口', included: true },
      { text: '专属客服', included: true },
      { text: '定制服务', included: true },
      { text: 'SLA 保障', included: true },
    ],
    buttonText: '联系销售',
    buttonType: 'default',
  },
]

const faqs = [
  { q: '额度用完了怎么办？', a: '每日额度会在次日重置，或者您可以升级到更高版本的套餐获得更多额度。' },
  { q: '如何获取更多额度？', a: '您可以通过邀请好友、每日签到等方式获取额外额度，或者升级到专业版/企业版。' },
  { q: '视频可以商用吗？', a: '专业版及以上版本生成的视频支持商用，免费版仅支持个人学习使用。' },
  { q: '如何升级套餐？', a: '在会员中心页面选择您想要的套餐，点击开通即可完成升级。' },
]

const features = [
  { icon: <VideoCameraOutlined />, title: '海量模板', desc: '涵盖各学科的精美动画模板' },
  { icon: <HddOutlined />, title: '云端渲染', desc: '强大算力，快速生成高清视频' },
  { icon: <CustomerServiceOutlined />, title: '技术支持', desc: '7x24 小时专业技术支持' },
  { icon: <ToolOutlined />, title: '持续更新', desc: '每周更新新功能和新模板' },
]

export default function Pricing() {
  return (
    <div className="pricing-page">
      <div className="pricing-hero">
        <Title level={2}>选择适合你的方案</Title>
        <Text type="secondary">
          灵活的套餐设计，满足不同用户的创作需求
        </Text>
      </div>

      <Row gutter={[24, 24]} className="pricing-cards">
        {plans.map((plan, index) => (
          <Col xs={24} sm={12} lg={8} key={index}>
            <Card className={`pricing-card ${plan.popular ? 'popular' : ''}`}>
              {plan.popular && (
                <div className="popular-badge">最受欢迎</div>
              )}
              <div className="plan-header">
                <div className="plan-icon" style={{ background: `${plan.color}15`, color: plan.color }}>
                  {plan.icon}
                </div>
                <Title level={4}>{plan.name}</Title>
                <Text type="secondary">{plan.description}</Text>
              </div>
              <div className="plan-price">
                <span className="currency">¥</span>
                <span className="amount">{plan.price}</span>
                <span className="period">/月</span>
              </div>
              <Divider />
              <ul className="feature-list">
                {plan.features.map((f, i) => (
                  <li key={i} className={f.included ? '' : 'disabled'}>
                    {f.included ? <CheckCircleOutlined /> : <span className="cross">×</span>}
                    {f.text}
                  </li>
                ))}
              </ul>
              <Button 
                type={plan.buttonType as any} 
                block 
                size="large"
                className={plan.popular ? 'popular-btn' : ''}
              >
                {plan.buttonText}
              </Button>
            </Card>
          </Col>
        ))}
      </Row>

      <div className="pricing-features">
        <Title level={3} className="section-title">为什么选择 Manim</Title>
        <Row gutter={[24, 24]}>
          {features.map((f, i) => (
            <Col xs={24} sm={12} lg={6} key={i}>
              <Card className="feature-card">
                <div className="feature-icon">{f.icon}</div>
                <Title level={5}>{f.title}</Title>
                <Text type="secondary">{f.desc}</Text>
              </Card>
            </Col>
          ))}
        </Row>
      </div>

      <div className="pricing-faq">
        <Title level={3} className="section-title">常见问题</Title>
        <List
          dataSource={faqs}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                title={<Text strong>{item.q}</Text>}
                description={<Text type="secondary">{item.a}</Text>}
              />
            </List.Item>
          )}
        />
      </div>

      <div className="pricing-cta">
        <Title level={3}>还有疑问？</Title>
        <Text>联系我们的销售团队，获取专属定制方案</Text>
        <Button type="primary" size="large">联系销售</Button>
      </div>
    </div>
  )
}
