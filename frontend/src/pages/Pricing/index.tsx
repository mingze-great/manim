import { useState, useEffect } from 'react'
import { Card, Row, Col, Button, Tag, Modal, message, Spin, QRCode } from 'antd'
import { 
  CheckCircleOutlined, CrownOutlined, RocketOutlined, ThunderboltOutlined,
  VideoCameraOutlined, HddOutlined, ToolOutlined, CustomerServiceOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { paymentApi, SubscriptionPlan } from '@/services/payment'
import './Pricing.css'

const PLAN_COLORS: Record<string, string> = {
  free: '#6b7280',
  basic: '#6366f1',
  pro: '#8b5cf6',
  enterprise: '#f59e0b',
}

const PLAN_ICONS: Record<string, React.ReactNode> = {
  free: <RocketOutlined />,
  basic: <ThunderboltOutlined />,
  pro: <VideoCameraOutlined />,
  enterprise: <CrownOutlined />,
}

export default function Pricing() {
  const navigate = useNavigate()
  const [plans, setPlans] = useState<Record<string, SubscriptionPlan>>({})
  const [currentPlan, setCurrentPlan] = useState<string>('free')
  const [loading, setLoading] = useState(true)
  const [paying, setPaying] = useState(false)
  const [payModalVisible, setPayModalVisible] = useState(false)
  const [currentOrder, setCurrentOrder] = useState<{ order_id: string; code_url: string; amount: number } | null>(null)
  const [queryingOrder, setQueryingOrder] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [plansRes, subRes] = await Promise.all([
        paymentApi.getPlans(),
        paymentApi.getMySubscription(),
      ])
      setPlans(plansRes.data)
      setCurrentPlan(subRes.data.plan)
    } catch (error) {
      console.error('获取套餐信息失败:', error)
      message.error('获取套餐信息失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSubscribe = async (planKey: string) => {
    const plan = plans[planKey]
    if (!plan || plan.price === 0) return

    setPaying(true)
    try {
      const res = await paymentApi.createOrder(planKey)
      if (res.data.code_url) {
        setCurrentOrder({
          order_id: res.data.order_id,
          code_url: res.data.code_url,
          amount: res.data.amount,
        })
        setPayModalVisible(true)
        startQueryOrder(res.data.order_id)
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '创建订单失败')
    } finally {
      setPaying(false)
    }
  }

  const startQueryOrder = (orderId: string) => {
    const queryInterval = setInterval(async () => {
      setQueryingOrder(true)
      try {
        const res = await paymentApi.queryOrder(orderId)
        if (res.data.status === 'paid') {
          clearInterval(queryInterval)
          message.success('支付成功！')
          setPayModalVisible(false)
          fetchData()
        }
      } catch (error) {
        console.error('查询订单失败:', error)
      } finally {
        setQueryingOrder(false)
      }
    }, 3000)

    setTimeout(() => {
      clearInterval(queryInterval)
      setQueryingOrder(false)
    }, 30 * 60 * 1000)
  }

  if (loading) {
    return (
      <div className="pricing-page">
        <div style={{ textAlign: 'center', padding: '100px 0' }}>
          <Spin size="large" />
        </div>
      </div>
    )
  }

  return (
    <div className="pricing-page">
      <div className="pricing-hero">
        <h2>选择适合你的创作方案</h2>
        <p>灵活的套餐方案，满足不同创作需求</p>
        {currentPlan !== 'free' && (
          <Tag color="success" className="mt-3">当前订阅: {plans[currentPlan]?.name}</Tag>
        )}
      </div>

      <Row gutter={[24, 24]} className="pricing-cards">
        {Object.entries(plans).map(([key, plan]) => (
          <Col xs={24} sm={12} lg={6} key={key}>
            <Card 
              className={`pricing-card ${key === 'pro' ? 'popular' : ''} ${currentPlan === key ? 'current' : ''}`}
              bodyStyle={{ padding: '32px 24px' }}
            >
              {key === 'pro' && <div className="popular-badge">最受欢迎</div>}
              
              <div className="plan-icon" style={{ background: `${PLAN_COLORS[key]}1a`, color: PLAN_COLORS[key] }}>
                {PLAN_ICONS[key]}
              </div>
              
              <h3 className="plan-name">{plan.name}</h3>
              
              <div className="plan-price">
                {plan.price === 0 ? (
                  <span className="amount">免费</span>
                ) : (
                  <>
                    <span className="currency">¥</span>
                    <span className="amount">{(plan.price / 100).toFixed(0)}</span>
                    <span className="period">/月</span>
                  </>
                )}
              </div>

              <ul className="feature-list">
                <li>
                  <CheckCircleOutlined style={{ color: '#10b981' }} />
                  每日 {plan.daily_quota} 次额度
                </li>
                <li>
                  <CheckCircleOutlined style={{ color: '#10b981' }} />
                  {plan.max_projects === -1 ? '无限项目数' : `最多 ${plan.max_projects} 个项目`}
                </li>
                {plan.features.map((feature, i) => (
                  <li key={i}>
                    <CheckCircleOutlined style={{ color: '#10b981' }} />
                    {feature}
                  </li>
                ))}
              </ul>

              <Button
                type={currentPlan === key ? 'default' : 'primary'}
                block
                size="large"
                disabled={currentPlan === key}
                loading={paying}
                className={currentPlan === key ? '' : key === 'pro' ? 'popular-btn' : ''}
                onClick={() => handleSubscribe(key)}
              >
                {currentPlan === key 
                  ? '当前方案' 
                  : plan.price === 0 
                    ? '免费使用' 
                    : '立即开通'
                }
              </Button>
            </Card>
          </Col>
        ))}
      </Row>

      <div className="pricing-features">
        <h3 className="section-title">所有方案都包含</h3>
        <Row gutter={[24, 24]}>
          {[
            { icon: <VideoCameraOutlined />, title: '智能对话生成', desc: '智能脚本策划' },
            { icon: <HddOutlined />, title: '云端渲染', desc: '强大算力支持' },
            { icon: <ToolOutlined />, title: '脚本编辑器', desc: '在线修改内容' },
            { icon: <CustomerServiceOutlined />, title: '技术支持', desc: '专业客服帮助' },
          ].map((item, i) => (
            <Col xs={12} lg={6} key={i}>
              <Card className="feature-card hover-lift" bodyStyle={{ textAlign: 'center', padding: '24px' }}>
                <div className="feature-icon" style={{ margin: '0 auto 16px' }}>{item.icon}</div>
                <div style={{ fontWeight: 600 }}>{item.title}</div>
                <div style={{ color: '#6b7280', fontSize: '13px' }}>{item.desc}</div>
              </Card>
            </Col>
          ))}
        </Row>
      </div>

      <div className="pricing-cta">
        <h3>准备好开始创作了吗？</h3>
        <p>加入 thousands of creators，轻松制作思维可视化动画</p>
        <Button 
          type="primary" 
          size="large" 
          onClick={() => navigate('/creator')}
          style={{ background: '#fff', color: '#6366f1', border: 'none' }}
        >
          立即开始创作
        </Button>
      </div>

      <Modal
        title="微信支付"
        open={payModalVisible}
        onCancel={() => setPayModalVisible(false)}
        footer={null}
        centered
      >
        {currentOrder && (
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <p style={{ marginBottom: '20px' }}>
              请使用微信扫描下方二维码完成支付
            </p>
            <div style={{ background: '#fff', padding: '20px', display: 'inline-block' }}>
              <QRCode value={currentOrder.code_url} size={200} />
            </div>
            <p style={{ marginTop: '20px', color: '#6b7280' }}>
              支付金额: <strong style={{ color: '#ef4444', fontSize: '24px' }}>¥{(currentOrder.amount / 100).toFixed(2)}</strong>
            </p>
            <p style={{ marginTop: '10px', color: '#6b7280', fontSize: '13px' }}>
              订单号: {currentOrder.order_id}
            </p>
            {queryingOrder && (
              <div style={{ marginTop: '20px' }}>
                <Spin />
                <p style={{ color: '#6b7280', marginTop: '10px' }}>等待支付中...</p>
              </div>
            )}
            <p style={{ marginTop: '20px', color: '#6b7280', fontSize: '12px' }}>
              支付成功后页面将自动跳转
            </p>
          </div>
        )}
      </Modal>
    </div>
  )
}
