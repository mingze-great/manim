import { Card, Button, Avatar, Space, Tag, Typography, Divider, Descriptions } from 'antd'
import { 
  UserOutlined, LogoutOutlined
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

      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Card loading={loading}>
          <Title level={5}>账号信息</Title>
          <Descriptions column={1} size="small">
            <Descriptions.Item label="用户名">{user?.username || '-'}</Descriptions.Item>
            <Descriptions.Item label="邮箱">{user?.email || '-'}</Descriptions.Item>
            <Descriptions.Item label="用户 ID">{user?.id || '-'}</Descriptions.Item>
            <Descriptions.Item label="套餐">{planLabels[subscription?.plan || 'free'] || subscription?.plan || '付费版'}</Descriptions.Item>
            <Descriptions.Item label="到期时间">{user?.expires_at ? new Date(user.expires_at).toLocaleString('zh-CN') : '未设置'}</Descriptions.Item>
            <Descriptions.Item label="今日使用量">{usageStats?.used_today ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="总使用量">{usageStats?.total_usage?.toLocaleString?.() ?? '-'}</Descriptions.Item>
          </Descriptions>
        </Card>

        <Card>
          <Title level={5}>说明</Title>
          <div className="text-gray-500 text-sm space-y-2">
            <div>个人中心当前仅保留已实际接通的账号信息与订阅信息。</div>
            <div>密码修改、通知设置、下载记录等功能将在后续完整接入后再重新开放。</div>
          </div>
          <Divider />
          <Button type="primary" onClick={() => navigate('/pricing')}>查看套餐</Button>
        </Card>
      </Space>

      <Card className="logout-card">
        <Button danger icon={<LogoutOutlined />} onClick={handleLogout}>
          退出登录
        </Button>
      </Card>
    </div>
  )
}
