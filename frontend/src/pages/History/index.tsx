import { Card, Row, Col, Button, Empty, Tabs, Typography, Progress, Space } from 'antd'
import { 
  VideoCameraOutlined, EditOutlined, DeleteOutlined, 
  CopyOutlined, DownloadOutlined, PlayCircleOutlined, FolderOutlined,
  ClockCircleOutlined, CheckCircleOutlined, CloseCircleOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import './History.css'

const { Title, Text } = Typography

const mockProjects = [
  { id: 1, name: '勾股定理动画', status: 'completed', created: '2024-01-15', duration: '15s', views: 234 },
  { id: 2, name: '三角函数演示', status: 'completed', created: '2024-01-14', duration: '20s', views: 156 },
  { id: 3, name: '微积分入门', status: 'running', created: '2024-01-14', duration: '-', views: 0 },
  { id: 4, name: '线性代数基础', status: 'failed', created: '2024-01-13', duration: '-', views: 0 },
  { id: 5, name: '概率论讲解', status: 'completed', created: '2024-01-12', duration: '25s', views: 89 },
]

const getStatusConfig = (status: string) => {
  switch (status) {
    case 'completed':
      return { color: 'green', icon: <CheckCircleOutlined />, text: '已完成' }
    case 'running':
      return { color: 'blue', icon: <ClockCircleOutlined />, text: '渲染中' }
    case 'failed':
      return { color: 'red', icon: <CloseCircleOutlined />, text: '失败' }
    default:
      return { color: 'default', icon: <ClockCircleOutlined />, text: '等待中' }
  }
}

export default function History() {
  const navigate = useNavigate()

  const completedProjects = mockProjects.filter(p => p.status === 'completed')
  const runningProjects = mockProjects.filter(p => p.status === 'running')

  return (
    <div className="history-page">
      <div className="history-header">
        <div className="header-left">
          <Title level={4}>我的作品</Title>
          <Text type="secondary">共 {mockProjects.length} 个项目</Text>
        </div>
        <Space>
          <Button icon={<FolderOutlined />}>创建文件夹</Button>
          <Button type="primary" icon={<VideoCameraOutlined />} onClick={() => navigate('/creator')}>
            新建项目
          </Button>
        </Space>
      </div>

      <Card className="stats-card">
        <Row gutter={24}>
          <Col span={8}>
            <div className="stat-item">
              <div className="stat-icon blue">
                <VideoCameraOutlined />
              </div>
              <div className="stat-info">
                <span className="stat-value">{completedProjects.length}</span>
                <span className="stat-label">已完成</span>
              </div>
            </div>
          </Col>
          <Col span={8}>
            <div className="stat-item">
              <div className="stat-icon orange">
                <ClockCircleOutlined />
              </div>
              <div className="stat-info">
                <span className="stat-value">{runningProjects.length}</span>
                <span className="stat-label">渲染中</span>
              </div>
            </div>
          </Col>
          <Col span={8}>
            <div className="stat-item">
              <div className="stat-icon green">
                <PlayCircleOutlined />
              </div>
              <div className="stat-info">
                <span className="stat-value">479</span>
                <span className="stat-label">总播放</span>
              </div>
            </div>
          </Col>
        </Row>
      </Card>

      <Tabs 
        defaultActiveKey="all"
        items={[
          { key: 'all', label: '全部', children: (
            <div className="projects-grid">
              {mockProjects.map((project) => {
                const statusConfig = getStatusConfig(project.status)
                return (
                  <Card key={project.id} className="project-card" hoverable>
                    <div className="project-thumbnail">
                      <VideoCameraOutlined className="thumbnail-icon" />
                      {project.status === 'running' && (
                        <div className="progress-overlay">
                          <Progress type="circle" percent={65} size={60} strokeColor="#6366f1" />
                        </div>
                      )}
                      <div className={`status-badge ${statusConfig.color}`}>
                        {statusConfig.icon} {statusConfig.text}
                      </div>
                    </div>
                    <div className="project-info">
                      <Title level={5} className="project-name">{project.name}</Title>
                      <div className="project-meta">
                        <Text type="secondary" className="project-date">
                          {project.created}
                        </Text>
                        {project.duration !== '-' && (
                          <Text type="secondary">{project.duration}</Text>
                        )}
                      </div>
                      <div className="project-actions">
                        {project.status === 'completed' ? (
                          <>
                            <Button type="text" icon={<PlayCircleOutlined />}>播放</Button>
                            <Button type="text" icon={<DownloadOutlined />}>下载</Button>
                            <Button type="text" icon={<CopyOutlined />}>复用</Button>
                          </>
                        ) : project.status === 'failed' ? (
                          <Button type="text" icon={<EditOutlined />}>重新编辑</Button>
                        ) : (
                          <Button type="text" icon={<ClockCircleOutlined />}>查看进度</Button>
                        )}
                        <Button type="text" danger icon={<DeleteOutlined />} />
                      </div>
                    </div>
                  </Card>
                )
              })}
            </div>
          )},
          { key: 'completed', label: '已完成', children: (
            <div className="projects-grid">
              {completedProjects.length > 0 ? completedProjects.map((project) => (
                <Card key={project.id} className="project-card" hoverable>
                  <div className="project-thumbnail">
                    <VideoCameraOutlined className="thumbnail-icon" />
                    <div className="status-badge green">
                      <CheckCircleOutlined /> 已完成
                    </div>
                  </div>
                  <div className="project-info">
                    <Title level={5} className="project-name">{project.name}</Title>
                    <div className="project-meta">
                      <Text type="secondary">{project.created}</Text>
                      <Text type="secondary">{project.duration}</Text>
                    </div>
                    <div className="project-actions">
                      <Button type="text" icon={<PlayCircleOutlined />}>播放</Button>
                      <Button type="text" icon={<DownloadOutlined />}>下载</Button>
                      <Button type="text" icon={<CopyOutlined />}>复用</Button>
                    </div>
                  </div>
                </Card>
              )) : <Empty description="暂无已完成的项目" />}
            </div>
          )},
          { key: 'running', label: '渲染中', children: (
            <div className="projects-grid">
              {runningProjects.length > 0 ? runningProjects.map((project) => (
                <Card key={project.id} className="project-card" hoverable>
                  <div className="project-thumbnail">
                    <VideoCameraOutlined className="thumbnail-icon" />
                    <div className="progress-overlay">
                      <Progress type="circle" percent={65} size={60} strokeColor="#6366f1" />
                    </div>
                    <div className="status-badge blue">
                      <ClockCircleOutlined /> 渲染中
                    </div>
                  </div>
                  <div className="project-info">
                    <Title level={5} className="project-name">{project.name}</Title>
                    <div className="project-meta">
                      <Text type="secondary">{project.created}</Text>
                    </div>
                    <div className="project-actions">
                      <Button type="text" icon={<ClockCircleOutlined />}>查看进度</Button>
                    </div>
                  </div>
                </Card>
              )) : <Empty description="暂无渲染中的项目" />}
            </div>
          )},
        ]}
      />
    </div>
  )
}
