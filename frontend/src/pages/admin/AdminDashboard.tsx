import { useState, useEffect } from 'react'
import { Row, Col, Card, Statistic } from 'antd'
import {
  UserOutlined, ProjectOutlined, VideoCameraOutlined,
  RiseOutlined, TeamOutlined, LockOutlined, EyeOutlined
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

  return (
    <div className="admin-dashboard">
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card className="admin-card stat-card blue" loading={loading}>
            <UserOutlined className="stat-icon" />
            <Statistic
              value={stats?.total_users || 0}
              className="stat-value"
              suffix="人"
            />
            <div className="stat-label">总用户数</div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="admin-card stat-card green" loading={loading}>
            <TeamOutlined className="stat-icon" />
            <Statistic
              value={stats?.active_users || 0}
              className="stat-value"
              suffix="人"
            />
            <div className="stat-label">活跃用户</div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="admin-card stat-card purple" loading={loading}>
            <ProjectOutlined className="stat-icon" />
            <Statistic
              value={stats?.total_projects || 0}
              className="stat-value"
              suffix="个"
            />
            <div className="stat-label">总项目数</div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="admin-card stat-card orange" loading={loading}>
            <VideoCameraOutlined className="stat-icon" />
            <Statistic
              value={stats?.total_videos || 0}
              className="stat-value"
              suffix="个"
            />
            <div className="stat-label">生成视频</div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="mt-4">
        <Col xs={24} lg={16}>
          <Card title="快捷操作" className="admin-card">
            <Row gutter={16}>
              <Col xs={8}>
                <div className="quick-action" onClick={() => navigate('/admin/users')}>
                  <TeamOutlined className="quick-action-icon" style={{ color: '#1890ff' }} />
                  <div className="hidden sm:block">用户管理</div>
                </div>
              </Col>
              <Col xs={8}>
                <div className="quick-action" onClick={() => navigate('/admin/logs')}>
                  <EyeOutlined className="quick-action-icon" style={{ color: '#722ed1' }} />
                  <div className="hidden sm:block">查看日志</div>
                </div>
              </Col>
              <Col xs={8}>
                <div className="quick-action" onClick={() => navigate('/admin/settings')}>
                  <LockOutlined className="quick-action-icon" style={{ color: '#faad14' }} />
                  <div className="hidden sm:block">安全设置</div>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="今日概览" className="admin-card">
            <div className="mb-4">
              <div className="text-gray mb-2">API 调用次数</div>
              <div className="text-2xl font-bold">{stats?.api_calls_today || 0}</div>
              <div className="text-green text-sm mt-1">
                <RiseOutlined /> 较昨日
              </div>
            </div>
            <div>
              <div className="text-gray mb-2">系统状态</div>
              <div className="text-green font-medium">运行正常</div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
