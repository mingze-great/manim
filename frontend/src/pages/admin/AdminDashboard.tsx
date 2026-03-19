import { useState, useEffect } from 'react'
import { Row, Col, Card, Space, Tag, Progress } from 'antd'
import {
  UserOutlined, ProjectOutlined, VideoCameraOutlined,
  TeamOutlined, LockOutlined, EyeOutlined,
  SafetyCertificateOutlined, ThunderboltOutlined, ClockCircleOutlined
} from '@ant-design/icons'
import { adminApi, SystemStats } from '../../services/admin'
import { useNavigate } from 'react-router-dom'

export default function AdminDashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const res = await adminApi.getSystemStats()
      setStats(res.data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    } finally {
      setLoading(false)
    }
  }

  const statCards = [
    { 
      icon: <UserOutlined />, 
      title: '总用户数', 
      value: stats?.total_users || 0, 
      suffix: '人',
      color: '#6366f1',
      bg: 'linear-gradient(135deg, #6366f11a, #8b5cf61a)'
    },
    { 
      icon: <TeamOutlined />, 
      title: '活跃用户', 
      value: stats?.active_users || 0, 
      suffix: '人',
      color: '#10b981',
      bg: 'linear-gradient(135deg, #10b9811a, #0596691a)'
    },
    { 
      icon: <ProjectOutlined />, 
      title: '总项目数', 
      value: stats?.total_projects || 0, 
      suffix: '个',
      color: '#8b5cf6',
      bg: 'linear-gradient(135deg, #8b5cf61a, #a855f71a)'
    },
    { 
      icon: <VideoCameraOutlined />, 
      title: '生成视频', 
      value: stats?.total_videos || 0, 
      suffix: '个',
      color: '#f59e0b',
      bg: 'linear-gradient(135deg, #f59e0b1a, #d977061a)'
    },
  ]

  const quickActions = [
    { icon: <TeamOutlined />, title: '用户管理', desc: '管理平台用户', path: '/admin/users', color: '#6366f1' },
    { icon: <EyeOutlined />, title: '操作日志', desc: '查看系统日志', path: '/admin/logs', color: '#8b5cf6' },
    { icon: <LockOutlined />, title: '安全设置', desc: '系统安全配置', path: '/admin/settings', color: '#f59e0b' },
  ]

  return (
    <div>
      <Row gutter={[16, 16]} className="mb-4">
        {statCards.map((stat, index) => (
          <Col xs={24} sm={12} lg={6} key={index}>
            <Card 
              className="hover-lift" 
              bodyStyle={{ padding: '24px' }}
              style={{ borderRadius: '16px', overflow: 'hidden' }}
              loading={loading}
            >
              <div style={{ 
                width: '56px', 
                height: '56px', 
                borderRadius: '14px', 
                background: stat.bg,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '16px'
              }}>
                <span style={{ fontSize: '24px', color: stat.color }}>{stat.icon}</span>
              </div>
              <div style={{ fontSize: '28px', fontWeight: 700, color: '#1f2937', marginBottom: '4px' }}>
                {stat.value}<span style={{ fontSize: '14px', fontWeight: 400, color: '#6b7280', marginLeft: '4px' }}>{stat.suffix}</span>
              </div>
              <div style={{ fontSize: '14px', color: '#6b7280' }}>{stat.title}</div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card 
            title={
              <Space>
                <ThunderboltOutlined style={{ color: '#6366f1' }} />
                <span>快捷操作</span>
              </Space>
            }
            className="hover-lift"
            bodyStyle={{ padding: '16px' }}
            style={{ borderRadius: '16px' }}
          >
            <Row gutter={[16, 16]}>
              {quickActions.map((action, index) => (
                <Col xs={8} key={index}>
                  <div 
                    onClick={() => navigate(action.path)}
                    style={{ 
                      textAlign: 'center', 
                      padding: '24px 16px',
                      borderRadius: '12px',
                      cursor: 'pointer',
                      transition: 'all 0.3s',
                      background: '#f9fafb'
                    }}
                    className="hover-lift"
                  >
                    <div style={{ 
                      width: '48px', 
                      height: '48px', 
                      borderRadius: '12px', 
                      background: `${action.color}1a`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto 12px'
                    }}>
                      <span style={{ fontSize: '20px', color: action.color }}>{action.icon}</span>
                    </div>
                    <div style={{ fontWeight: 600, color: '#1f2937', marginBottom: '4px' }}>{action.title}</div>
                    <div style={{ fontSize: '12px', color: '#6b7280' }}>{action.desc}</div>
                  </div>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
        
        <Col xs={24} lg={10}>
          <Card 
            title={
              <Space>
                <ClockCircleOutlined style={{ color: '#10b981' }} />
                <span>系统状态</span>
              </Space>
            }
            className="hover-lift"
            style={{ borderRadius: '16px' }}
          >
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <div>
                <div className="flex justify-between mb-2">
                  <span style={{ color: '#6b7280' }}>API 调用 (今日)</span>
                  <span style={{ fontWeight: 600, color: '#1f2937' }}>{stats?.api_calls_today || 0} 次</span>
                </div>
                <Progress 
                  percent={Math.min((stats?.api_calls_today || 0) / 1000 * 100, 100)} 
                  strokeColor="#6366f1"
                  showInfo={false}
                />
              </div>
              
              <div className="flex justify-between items-center">
                <Space>
                  <SafetyCertificateOutlined style={{ color: '#10b981' }} />
                  <span style={{ color: '#6b7280' }}>系统状态</span>
                </Space>
                <Tag color="success" icon={<SafetyCertificateOutlined />}>运行正常</Tag>
              </div>
              
              <div className="flex justify-between items-center">
                <Space>
                  <VideoCameraOutlined style={{ color: '#8b5cf6' }} />
                  <span style={{ color: '#6b7280' }}>CPU 使用率</span>
                </Space>
                <Tag color="processing">45%</Tag>
              </div>
              
              <div className="flex justify-between items-center">
                <Space>
                  <ProjectOutlined style={{ color: '#f59e0b' }} />
                  <span style={{ color: '#6b7280' }}>内存使用率</span>
                </Space>
                <Tag color="warning">62%</Tag>
              </div>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
