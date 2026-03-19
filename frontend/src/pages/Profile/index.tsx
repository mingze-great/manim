import { Card, Tabs, Form, Input, Button, Avatar, Space, Tag, List, Typography, Divider, Progress } from 'antd'
import { 
  UserOutlined, SafetyOutlined, BellOutlined, KeyOutlined, 
  DownloadOutlined, ClockCircleOutlined, HistoryOutlined, LogoutOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import './Profile.css'

const { Title, Text } = Typography

export default function Profile() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="profile-page">
      <div className="profile-header">
        <Avatar size={80} icon={<UserOutlined />} className="profile-avatar" />
        <div className="profile-info">
          <Title level={3}>{user?.username || '用户'}</Title>
          <Space>
            <Tag color="blue">免费版</Tag>
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
              <Card>
                <div className="quota-section">
                  <div className="quota-header">
                    <Title level={5}>今日额度</Title>
                    <Text type="secondary">每日 00:00 重置</Text>
                  </div>
                  <div className="quota-display">
                    <Progress 
                      type="dashboard" 
                      percent={50} 
                      size={160}
                      strokeColor="#6366f1"
                      format={(percent) => (
                        <div className="quota-numbers">
                          <span className="used">{100 - (percent || 0)}</span>
                          <span className="total">/ 100</span>
                        </div>
                      )}
                    />
                  </div>
                  <div className="quota-actions">
                    <Button type="primary">升级套餐</Button>
                    <Button>获取更多额度</Button>
                  </div>
                </div>
                <Divider />
                <div className="usage-stats">
                  <Title level={5}>使用统计</Title>
                  <div className="stats-grid">
                    <div className="stat-item">
                      <span className="stat-value">25</span>
                      <span className="stat-label">今日使用</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-value">156</span>
                      <span className="stat-label">本周使用</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-value">1,234</span>
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
