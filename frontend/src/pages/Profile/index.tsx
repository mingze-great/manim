import { Card, Tabs, Form, Input, Button, Avatar, Space, Tag, List, Typography, Divider, Progress, Switch, Select, message, Alert } from 'antd'
import { 
  UserOutlined, SafetyOutlined, BellOutlined, KeyOutlined, 
  DownloadOutlined, ClockCircleOutlined, HistoryOutlined, LogoutOutlined, ApiOutlined, SettingOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { paymentApi, Subscription, UsageStats } from '@/services/payment'
import './Profile.css'

const { Title, Text } = Typography

export default function Profile() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [apiConfigLoading, setApiConfigLoading] = useState(false)
  const [llmApiKey, setLlmApiKey] = useState('')
  const [llmProvider, setLlmProvider] = useState('dashscope')
  const [llmUseCustom, setLlmUseCustom] = useState(false)
  const [imageApiKey, setImageApiKey] = useState('')
  const [imageProvider, setImageProvider] = useState('dashscope')
  const [imageUseCustom, setImageUseCustom] = useState(false)
  const [ttsApiKey, setTtsApiKey] = useState('')
  const [ttsProvider, setTtsProvider] = useState('dashscope')
  const [ttsUseCustom, setTtsUseCustom] = useState(false)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [subRes, usageRes] = await Promise.all([
          paymentApi.getMySubscription(),
          paymentApi.getUsageStats()
        ])
        setSubscription(subRes.data)
        setUsageStats(usageRes.data)
      } catch (err) {
        console.error('Failed to fetch profile data:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const planLabels: Record<string, string> = {
    free: '付费版',
    basic: '基础版',
    pro: '专业版',
    enterprise: '企业版'
  }

  const remainingQuota = usageStats ? usageStats.daily_quota - usageStats.used_today : 0
  const usedPercent = usageStats ? Math.round((usageStats.used_today / usageStats.daily_quota) * 100) : 50

  return (
    <div className="profile-page">
      <div className="profile-header">
        <Avatar size={80} icon={<UserOutlined />} className="profile-avatar" />
        <div className="profile-info">
          <Title level={3}>{user?.username || '用户'}</Title>
          <Space>
            <Tag color={subscription?.plan === 'free' ? 'blue' : 'green'}>
              {planLabels[subscription?.plan || 'free'] || subscription?.plan || '付费版'}
            </Tag>
            <Text type="secondary">ID: {user?.id || 1}</Text>
          </Space>
        </div>
      </div>

      <Tabs
        defaultActiveKey="quota"
        items={[
          {
            key: 'quota',
            label: '额度管理',
            children: (
              <Card loading={loading}>
                <div className="quota-section">
                  <div className="quota-header">
                    <Title level={5}>今日额度</Title>
                    <Text type="secondary">每日 00:00 重置</Text>
                  </div>
                  <div className="quota-display">
                    <Progress 
                      type="dashboard" 
                      percent={usedPercent} 
                      size={160}
                      strokeColor={remainingQuota > 0 ? "#6366f1" : "#ff4d4f"}
                      format={() => (
                        <div className="quota-numbers">
                          <span className="used">{remainingQuota}</span>
                          <span className="total">/ {usageStats?.daily_quota || 100}</span>
                        </div>
                      )}
                    />
                  </div>
                  <div className="quota-actions">
                    <Button type="primary" onClick={() => navigate('/pricing')}>升级套餐</Button>
                    <Button>获取更多额度</Button>
                  </div>
                </div>
                <Divider />
                <div className="usage-stats">
                  <Title level={5}>使用统计</Title>
                  <div className="stats-grid">
                    <div className="stat-item">
                      <span className="stat-value">{usageStats?.used_today || 0}</span>
                      <span className="stat-label">今日使用</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-value">{usageStats?.weekly_usage || 0}</span>
                      <span className="stat-label">本周使用</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-value">{usageStats?.total_usage?.toLocaleString() || 0}</span>
                      <span className="stat-label">总使用量</span>
                    </div>
                  </div>
                </div>
              </Card>
            ),
          },
          {
            key: 'account',
            label: '账户设置',
            children: (
              <Card>
                <Form layout="vertical" initialValues={{ username: user?.username, email: user?.email }}>
                  <Form.Item label="用户名">
                    <Input prefix={<UserOutlined />} />
                  </Form.Item>
                  <Form.Item label="邮箱">
                    <Input prefix="@" disabled />
                  </Form.Item>
                  <Form.Item label="手机号">
                    <Input placeholder="未绑定" />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary">保存修改</Button>
                  </Form.Item>
                </Form>
                <Divider />
                <Title level={5}>安全设置</Title>
                <div className="security-items">
                  <div className="security-item">
                    <div>
                      <Text strong>修改密码</Text>
                      <Text type="secondary" className="block">上次修改于 30 天前</Text>
                    </div>
                    <Button icon={<KeyOutlined />}>修改</Button>
                  </div>
                  <div className="security-item">
                    <div>
                      <Text strong>两步验证</Text>
                      <Text type="secondary" className="block">未启用</Text>
                    </div>
                    <Button icon={<SafetyOutlined />}>启用</Button>
                  </div>
                </div>
              </Card>
            ),
          },
          {
            key: 'notifications',
            label: '通知设置',
            children: (
              <Card>
                <List
                  dataSource={[
                    { icon: <BellOutlined />, title: '任务完成通知', desc: '渲染完成时发送通知', enabled: true },
                    { icon: <DownloadOutlined />, title: '下载通知', desc: '视频下载完成时发送通知', enabled: true },
                    { icon: <ClockCircleOutlined />, title: '渲染队列提醒', desc: '渲染开始前提醒', enabled: false },
                    { icon: <HistoryOutlined />, title: '活动日志', desc: '账户重要操作通知', enabled: true },
                  ]}
                  renderItem={(item) => (
                    <List.Item
                      actions={[
                        <Button type="link">{item.enabled ? '关闭' : '开启'}</Button>
                      ]}
                    >
                      <List.Item.Meta
                        avatar={<div className="notif-icon">{item.icon}</div>}
                        title={item.title}
                        description={item.desc}
                      />
                    </List.Item>
                  )}
                />
              </Card>
            ),
          },
          {
            key: 'api',
            label: 'API 配置',
            children: (
              <Card>
                <Alert type="info" message="默认使用系统 API key。如需使用自己的 API key，请配置后开启对应开关。" showIcon style={{ marginBottom: 24 }} />
                
                <Title level={5}><ApiOutlined /> LLM API（文本生成）</Title>
                <div style={{ marginBottom: 24 }}>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text>使用自定义 API Key</Text>
                      <Switch checked={llmUseCustom} onChange={(checked) => setLlmUseCustom(checked)} />
                    </div>
                    <Select value={llmProvider} onChange={setLlmProvider} style={{ width: '100%' }} disabled={!llmUseCustom}>
                      <Select.Option value="dashscope">阿里云百炼 (DashScope)</Select.Option>
                      <Select.Option value="openai">OpenAI</Select.Option>
                      <Select.Option value="gemini">Google Gemini</Select.Option>
                    </Select>
                    <Input.Password 
                      placeholder="输入 API Key" 
                      value={llmApiKey}
                      onChange={(e) => setLlmApiKey(e.target.value)}
                      disabled={!llmUseCustom}
                    />
                    <Button type="primary" loading={apiConfigLoading} disabled={!llmUseCustom} onClick={() => {
                      setApiConfigLoading(true)
                      // TODO: 调用 API 保存配置
                      setTimeout(() => {
                        message.success('LLM API 配置已保存')
                        setApiConfigLoading(false)
                      }, 1000)
                    }}>保存 LLM 配置</Button>
                  </Space>
                </div>

                <Divider />

                <Title level={5}><ApiOutlined /> 图片生成 API</Title>
                <div style={{ marginBottom: 24 }}>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text>使用自定义 API Key</Text>
                      <Switch checked={imageUseCustom} onChange={(checked) => setImageUseCustom(checked)} />
                    </div>
                    <Select value={imageProvider} onChange={setImageProvider} style={{ width: '100%' }} disabled={!imageUseCustom}>
                      <Select.Option value="dashscope">阿里云百炼 (DashScope)</Select.Option>
                    </Select>
                    <Input.Password 
                      placeholder="输入 API Key" 
                      value={imageApiKey}
                      onChange={(e) => setImageApiKey(e.target.value)}
                      disabled={!imageUseCustom}
                    />
                    <Button type="primary" loading={apiConfigLoading} disabled={!imageUseCustom} onClick={() => {
                      setApiConfigLoading(true)
                      setTimeout(() => {
                        message.success('图片 API 配置已保存')
                        setApiConfigLoading(false)
                      }, 1000)
                    }}>保存图片配置</Button>
                  </Space>
                </div>

                <Divider />

                <Title level={5}><ApiOutlined /> TTS API（配音生成）</Title>
                <div>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text>使用自定义 API Key</Text>
                      <Switch checked={ttsUseCustom} onChange={(checked) => setTtsUseCustom(checked)} />
                    </div>
                    <Select value={ttsProvider} onChange={setTtsProvider} style={{ width: '100%' }} disabled={!ttsUseCustom}>
                      <Select.Option value="dashscope">阿里云百炼 (DashScope)</Select.Option>
                    </Select>
                    <Input.Password 
                      placeholder="输入 API Key" 
                      value={ttsApiKey}
                      onChange={(e) => setTtsApiKey(e.target.value)}
                      disabled={!ttsUseCustom}
                    />
                    <Button type="primary" loading={apiConfigLoading} disabled={!ttsUseCustom} onClick={() => {
                      setApiConfigLoading(true)
                      setTimeout(() => {
                        message.success('TTS API 配置已保存')
                        setApiConfigLoading(false)
                      }, 1000)
                    }}>保存 TTS 配置</Button>
                  </Space>
                </div>
              </Card>
            ),
          },
          {
            key: 'downloads',
            label: '下载记录',
            children: (
              <Card>
                <List
                  dataSource={[
                    { name: '勾股定理动画.mp4', size: '12.5 MB', time: '2024-01-15 14:30' },
                    { name: '三角函数演示.mp4', size: '18.2 MB', time: '2024-01-14 10:20' },
                    { name: '概率论讲解.mp4', size: '25.6 MB', time: '2024-01-12 16:45' },
                  ]}
                  renderItem={(item) => (
                    <List.Item
                      actions={[<Button type="link" icon={<DownloadOutlined />}>重新下载</Button>]}
                    >
                      <List.Item.Meta
                        title={item.name}
                        description={`${item.size} · ${item.time}`}
                      />
                    </List.Item>
                  )}
                />
              </Card>
            ),
          },
        ]}
      />

      <Card className="logout-card">
        <Button danger icon={<LogoutOutlined />} onClick={handleLogout}>
          退出登录
        </Button>
      </Card>
    </div>
  )
}
