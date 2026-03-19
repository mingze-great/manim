import { useState, useEffect } from 'react'
import { Card, Row, Col, Button, Empty, Tabs, Typography, Progress, Space, Modal, message, Popconfirm } from 'antd'
import { 
  VideoCameraOutlined, EditOutlined, DeleteOutlined, 
  CopyOutlined, DownloadOutlined, PlayCircleOutlined,
  ClockCircleOutlined, CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined,
  PlusOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { projectApi, Project, Task } from '@/services/project'
import './History.css'

const { Title, Text } = Typography

const getStatusConfig = (status: string) => {
  switch (status) {
    case 'completed':
      return { color: 'green', icon: <CheckCircleOutlined />, text: '已完成' }
    case 'rendering':
      return { color: 'blue', icon: <ClockCircleOutlined />, text: '渲染中' }
    case 'failed':
      return { color: 'red', icon: <CloseCircleOutlined />, text: '失败' }
    case 'chatting':
      return { color: 'purple', icon: <EditOutlined />, text: '对话中' }
    case 'code_generated':
      return { color: 'cyan', icon: <VideoCameraOutlined />, text: '待渲染' }
    default:
      return { color: 'default', icon: <ClockCircleOutlined />, text: '等待中' }
  }
}

export default function History() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [tasks, setTasks] = useState<Record<number, Task>>({})
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('all')
  const [viewModalVisible, setViewModalVisible] = useState(false)
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)

  useEffect(() => {
    fetchProjects()
  }, [])

  const fetchProjects = async () => {
    setLoading(true)
    try {
      const { data } = await projectApi.list()
      setProjects(data)
      
      const taskMap: Record<number, Task> = {}
      for (const project of data) {
        if (project.id) {
          try {
            const taskRes = await projectApi.getTask(project.id)
            taskMap[project.id] = taskRes.data
          } catch {
            // No task for this project
          }
        }
      }
      setTasks(taskMap)
    } catch (error) {
      message.error('获取项目列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteProject = async (projectId: number) => {
    try {
      await projectApi.delete(projectId)
      message.success('项目已删除')
      fetchProjects()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleContinueProject = (project: Project) => {
    navigate(`/project/${project.id}/chat`)
  }

  const handleViewProject = (project: Project) => {
    setSelectedProject(project)
    setViewModalVisible(true)
  }

  const filteredProjects = projects.filter(p => {
    if (activeTab === 'all') return true
    if (activeTab === 'completed') return p.status === 'completed'
    if (activeTab === 'running') return ['chatting', 'rendering', 'pending'].includes(p.status)
    if (activeTab === 'failed') return p.status === 'failed'
    return true
  })

  const completedCount = projects.filter(p => p.status === 'completed').length
  const runningCount = projects.filter(p => ['chatting', 'rendering', 'pending'].includes(p.status)).length

  return (
    <div className="history-page">
      <div className="history-header">
        <div className="header-left">
          <Title level={4}>我的作品</Title>
          <Text type="secondary">共 {projects.length} 个项目</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchProjects} loading={loading}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/creator')}>
            新建项目
          </Button>
        </Space>
      </div>

      <Card className="stats-card">
        <Row gutter={24}>
          <Col xs={12} sm={8}>
            <div className="stat-item">
              <div className="stat-icon blue">
                <VideoCameraOutlined />
              </div>
              <div className="stat-info">
                <span className="stat-value">{completedCount}</span>
                <span className="stat-label">已完成</span>
              </div>
            </div>
          </Col>
          <Col xs={12} sm={8}>
            <div className="stat-item">
              <div className="stat-icon orange">
                <ClockCircleOutlined />
              </div>
              <div className="stat-info">
                <span className="stat-value">{runningCount}</span>
                <span className="stat-label">进行中</span>
              </div>
            </div>
          </Col>
          <Col xs={24} sm={8}>
            <div className="stat-item">
              <div className="stat-icon green">
                <PlayCircleOutlined />
              </div>
              <div className="stat-info">
                <span className="stat-value">{projects.length}</span>
                <span className="stat-label">总项目数</span>
              </div>
            </div>
          </Col>
        </Row>
      </Card>

      <Tabs 
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          { key: 'all', label: `全部 (${projects.length})`, children: (
            projects.length === 0 ? (
              <Empty description="暂无项目" image={Empty.PRESENTED_IMAGE_SIMPLE}>
                <Button type="primary" onClick={() => navigate('/creator')}>创建第一个项目</Button>
              </Empty>
            ) : (
              <div className="projects-grid">
                {filteredProjects.map((project) => {
                  const statusConfig = getStatusConfig(project.status)
                  const task = tasks[project.id]
                  return (
                    <Card key={project.id} className="project-card hover-lift">
                      <div className="project-thumbnail" onClick={() => handleViewProject(project)}>
                        <VideoCameraOutlined className="thumbnail-icon" />
                        {project.status === 'rendering' && task && (
                          <div className="progress-overlay">
                            <Progress type="circle" percent={task.progress || 0} size={60} strokeColor="#6366f1" />
                          </div>
                        )}
                        <div className={`status-badge ${statusConfig.color}`}>
                          {statusConfig.icon} {statusConfig.text}
                        </div>
                      </div>
                      <div className="project-info">
                        <Title level={5} className="project-name">{project.title}</Title>
                        <div className="project-meta">
                          <Text type="secondary" className="project-date">
                            {new Date(project.created_at).toLocaleDateString('zh-CN')}
                          </Text>
                          {project.theme && (
                            <Text type="secondary" ellipsis style={{ maxWidth: 100 }}>
                              {project.theme}
                            </Text>
                          )}
                        </div>
                        <div className="project-actions">
                          {project.status === 'completed' ? (
                            <>
                              <Button type="text" size="small" icon={<PlayCircleOutlined />} onClick={() => handleViewProject(project)}>播放</Button>
                              <Button type="text" size="small" icon={<CopyOutlined />} onClick={() => navigate(`/project/${project.id}/chat`)}>复用</Button>
                            </>
                          ) : (
                            <Button type="text" size="small" icon={<EditOutlined />} onClick={() => handleContinueProject(project)}>继续编辑</Button>
                          )}
                          <Popconfirm
                            title="确定删除此项目？"
                            description="删除后无法恢复"
                            onConfirm={() => handleDeleteProject(project.id)}
                            okText="确定"
                            cancelText="取消"
                          >
                            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                          </Popconfirm>
                        </div>
                      </div>
                    </Card>
                  )
                })}
              </div>
            )
          )},
          { key: 'completed', label: `已完成 (${completedCount})`, children: (
            filteredProjects.length === 0 ? (
              <Empty description="暂无已完成的项目" />
            ) : (
              <div className="projects-grid">
                {filteredProjects.map((project) => {
                  const task = tasks[project.id]
                  return (
                    <Card key={project.id} className="project-card hover-lift">
                      <div className="project-thumbnail" onClick={() => handleViewProject(project)}>
                        <VideoCameraOutlined className="thumbnail-icon" />
                        <div className="status-badge green">
                          <CheckCircleOutlined /> 已完成
                        </div>
                      </div>
                      <div className="project-info">
                        <Title level={5} className="project-name">{project.title}</Title>
                        <div className="project-meta">
                          <Text type="secondary">{new Date(project.created_at).toLocaleDateString('zh-CN')}</Text>
                        </div>
                        <div className="project-actions">
                          <Button type="text" size="small" icon={<PlayCircleOutlined />} onClick={() => handleViewProject(project)}>播放</Button>
                          {task?.video_url && (
                            <Button type="text" size="small" icon={<DownloadOutlined />}>下载</Button>
                          )}
                        </div>
                      </div>
                    </Card>
                  )
                })}
              </div>
            )
          )},
          { key: 'running', label: `进行中 (${runningCount})`, children: (
            filteredProjects.length === 0 ? (
              <Empty description="暂无进行中的项目" />
            ) : (
              <div className="projects-grid">
                {filteredProjects.map((project) => {
                  const task = tasks[project.id]
                  return (
                    <Card key={project.id} className="project-card hover-lift">
                      <div className="project-thumbnail" onClick={() => handleContinueProject(project)}>
                        <VideoCameraOutlined className="thumbnail-icon" />
                        {task && (
                          <div className="progress-overlay">
                            <Progress type="circle" percent={task.progress || 50} size={60} strokeColor="#6366f1" />
                          </div>
                        )}
                        <div className="status-badge blue">
                          <ClockCircleOutlined /> {getStatusConfig(project.status).text}
                        </div>
                      </div>
                      <div className="project-info">
                        <Title level={5} className="project-name">{project.title}</Title>
                        <div className="project-meta">
                          <Text type="secondary">{new Date(project.created_at).toLocaleDateString('zh-CN')}</Text>
                        </div>
                        <div className="project-actions">
                          <Button type="text" size="small" icon={<EditOutlined />} onClick={() => handleContinueProject(project)}>
                            {project.status === 'rendering' ? '查看进度' : '继续编辑'}
                          </Button>
                        </div>
                      </div>
                    </Card>
                  )
                })}
              </div>
            )
          )},
        ]}
      />

      <Modal
        title={selectedProject?.title}
        open={viewModalVisible}
        onCancel={() => setViewModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setViewModalVisible(false)}>关闭</Button>,
          <Button key="edit" type="primary" onClick={() => {
            setViewModalVisible(false)
            if (selectedProject) handleContinueProject(selectedProject)
          }}>
            {selectedProject?.status === 'completed' ? '复用项目' : '继续编辑'}
          </Button>,
        ]}
        width={700}
      >
        {selectedProject && (
          <div className="project-detail">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Text type="secondary">状态</Text>
                <div className="mt-2">
                  <span className={`status-badge ${getStatusConfig(selectedProject.status).color}`}>
                    {getStatusConfig(selectedProject.status).icon} {getStatusConfig(selectedProject.status).text}
                  </span>
                </div>
              </Col>
              <Col span={12}>
                <Text type="secondary">创建时间</Text>
                <div className="mt-2">
                  <Text>{new Date(selectedProject.created_at).toLocaleString('zh-CN')}</Text>
                </div>
              </Col>
            </Row>
            
            {selectedProject.theme && (
              <div className="mt-4">
                <Text type="secondary">主题</Text>
                <div className="mt-2">
                  <Text>{selectedProject.theme}</Text>
                </div>
              </div>
            )}
            
            {selectedProject.final_script && (
              <div className="mt-4">
                <Text type="secondary">最终脚本</Text>
                <Card size="small" className="mt-2" bodyStyle={{ maxHeight: 200, overflow: 'auto' }}>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{selectedProject.final_script}</pre>
                </Card>
              </div>
            )}
            
            {selectedProject.manim_code && (
              <div className="mt-4">
                <Text type="secondary">代码预览</Text>
                <Card size="small" className="mt-2" bodyStyle={{ maxHeight: 200, overflow: 'auto' }}>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{selectedProject.manim_code.slice(0, 500)}...</pre>
                </Card>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
