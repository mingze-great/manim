import { Card, Button, Avatar, Space, Tag, Typography, Divider, Descriptions, Modal, Form, Input, message } from 'antd'
import { 
  UserOutlined, LogoutOutlined, LockOutlined, GiftOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { paymentApi, Subscription, UsageStats } from '@/services/payment'
import { authApi } from '@/services/auth'
import './Profile.css'

const { Title, Text } = Typography

export default function Profile() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [passwordModalOpen, setPasswordModalOpen] = useState(false)
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [redeemCode, setRedeemCode] = useState('')
  const [redeeming, setRedeeming] = useState(false)
  const [form] = Form.useForm()

  const loadProfileData = async () => {
    setLoading(true)
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

  useEffect(() => {
    loadProfileData()
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const handleChangePassword = async () => {
    const token = useAuthStore.getState().token
    if (!token) {
      message.error('登录状态已失效，请重新登录')
      return
    }
    try {
      const values = await form.validateFields()
      setPasswordLoading(true)
      await authApi.changePassword({ old_password: values.old_password, new_password: values.new_password }, token)
      message.success('密码修改成功，请牢记新密码')
      setPasswordModalOpen(false)
      form.resetFields()
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(err.response?.data?.detail || '密码修改失败')
    } finally {
      setPasswordLoading(false)
    }
  }

  const handleRedeemCode = async () => {
    const code = redeemCode.trim()
    if (!code) {
      message.warning('请输入兑换码')
      return
    }
    setRedeeming(true)
    try {
      const { data } = await paymentApi.redeemCode(code)
      message.success(`兑换成功，已开通 ${data.plan}`)
      setRedeemCode('')
      await loadProfileData()
      const token = useAuthStore.getState().token
      if (token) {
        const me = await authApi.me(token)
        useAuthStore.getState().setUser(me.data)
      }
    } catch (err: any) {
      message.error(err.response?.data?.detail || '兑换失败')
    } finally {
      setRedeeming(false)
    }
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
            <Descriptions.Item label="手机号">{user?.phone || '-'}</Descriptions.Item>
            <Descriptions.Item label="系统邮箱">{user?.email || '-'}</Descriptions.Item>
            <Descriptions.Item label="用户 ID">{user?.id || '-'}</Descriptions.Item>
            <Descriptions.Item label="套餐">{planLabels[subscription?.plan || 'free'] || subscription?.plan || '付费版'}</Descriptions.Item>
            <Descriptions.Item label="到期时间">{user?.expires_at ? new Date(user.expires_at).toLocaleString('zh-CN') : '未设置'}</Descriptions.Item>
            <Descriptions.Item label="今日使用量">{usageStats?.used_today ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="总使用量">{usageStats?.total_usage?.toLocaleString?.() ?? '-'}</Descriptions.Item>
          </Descriptions>
        </Card>

        <Card>
          <Title level={5}>兑换码开通</Title>
          <Space.Compact style={{ width: '100%' }}>
            <Input
              value={redeemCode}
              onChange={(event) => setRedeemCode(event.target.value)}
              placeholder="输入付款后获得的兑换码"
              allowClear
            />
            <Button type="primary" icon={<GiftOutlined />} loading={redeeming} onClick={handleRedeemCode}>
              立即兑换
            </Button>
          </Space.Compact>
          <Text type="secondary" className="block mt-2">
            兑换成功后会立即刷新套餐、额度和火柴人生成权限。
          </Text>
        </Card>

        <Card>
          <Title level={5}>说明</Title>
          <div className="text-gray-500 text-sm space-y-2">
            <div>个人中心当前保留账号信息、订阅信息和密码修改能力。</div>
            <div>下载记录、通知设置等功能会在后续继续完善。</div>
          </div>
          <Divider />
          <Space wrap>
            <Button type="primary" onClick={() => navigate('/pricing')}>查看套餐</Button>
            <Button icon={<LockOutlined />} onClick={() => setPasswordModalOpen(true)}>修改密码</Button>
          </Space>
        </Card>
      </Space>

      <Card className="logout-card">
        <Button danger icon={<LogoutOutlined />} onClick={handleLogout}>
          退出登录
        </Button>
      </Card>

      <Modal
        title="修改密码"
        open={passwordModalOpen}
        onCancel={() => {
          setPasswordModalOpen(false)
          form.resetFields()
        }}
        onOk={handleChangePassword}
        confirmLoading={passwordLoading}
        okText="确认修改"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item label="旧密码" name="old_password" rules={[{ required: true, message: '请输入旧密码' }]}>
            <Input.Password placeholder="请输入当前密码" />
          </Form.Item>
          <Form.Item label="新密码" name="new_password" rules={[
            { required: true, message: '请输入新密码' },
            { min: 8, message: '密码至少 8 位' },
            { pattern: /[A-Za-z]/, message: '密码必须包含字母' },
            { pattern: /\d/, message: '密码必须包含数字' },
          ]}>
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
          <Form.Item label="确认新密码" name="confirm_password" dependencies={['new_password']} rules={[
            { required: true, message: '请再次输入新密码' },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('new_password') === value) {
                  return Promise.resolve()
                }
                return Promise.reject(new Error('两次输入的新密码不一致'))
              },
            }),
          ]}>
            <Input.Password placeholder="请再次输入新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
