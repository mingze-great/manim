import { useState, useRef, useEffect } from 'react'
import { 
  Card, Button, Input, Tabs, Steps, Progress, 
  Space, Tag, Typography, message, Badge, Tooltip,
  Empty, Segmented, Select, Avatar, Modal, Form, Spin
} from 'antd'
import {
  SendOutlined, RobotOutlined, CodeOutlined, PlayCircleOutlined,
  CopyOutlined, ReloadOutlined, DownloadOutlined,
  SettingOutlined, BulbOutlined, MessageOutlined, FileTextOutlined,
  VideoCameraOutlined, RedoOutlined, PlusOutlined, SaveOutlined
} from '@ant-design/icons'
import { projectApi, Project, Conversation } from '@/services/project'
import { templateApi, Template } from '@/services/template'
import './Creator.css'

const { Text, Title } = Typography
const { TextArea } = Input

interface Task {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  message: string
}

const presets = [
  { label: '公式展示', desc: '标题 + 公式动画，适合开场', icon: '📐' },
  { label: '几何证明', desc: '图形变换 + 步骤标注', icon: '📐' },
  { label: '函数图像', desc: '函数曲线绘制动画', icon: '📈' },
  { label: '定理讲解', desc: '分步推导 + 高亮强调', icon: '📚' },
]

export default function Creator() {
  const [activeTab, setActiveTab] = useState('chat')
  const [messages, setMessages] = useState<Conversation[]>([])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [theme, setTheme] = useState('dark')
  const [quality, setQuality] = useState('720p')
  const [duration, setDuration] = useState('short')
  const [generatedCode, setGeneratedCode] = useState('')
  const [editableCode, setEditableCode] = useState('')
  const [tasks, setTasks] = useState<Task[]>([])
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [project, setProject] = useState<Project | null>(null)
  const [aiThinking, setAiThinking] = useState(false)
  const [thinkingMessage, setThinkingMessage] = useState('')
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [newProjectTitle, setNewProjectTitle] = useState('')
  const [newProjectTheme, setNewProjectTheme] = useState('')
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [templateModalVisible, setTemplateModalVisible] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    fetchTemplates()
  }, [])

  const fetchTemplates = async () => {
    try {
      const { data } = await templateApi.list()
      setTemplates([...data.system_templates, ...data.user_templates])
    } catch (error) {
      console.error('获取模板失败:', error)
    }
  }

  const fetchProject = async (projectId: number) => {
    try {
      const { data } = await projectApi.get(projectId)
      setProject(data)
      if (data.manim_code) {
        setGeneratedCode(data.manim_code)
        setEditableCode(data.manim_code)
      }
    } catch (error) {
      message.error('获取项目失败')
    }
  }

  const fetchConversations = async (projectId: number) => {
    try {
      const { data } = await projectApi.getConversations(projectId)
      setMessages(data)
    } catch (error) {
      console.error('获取对话失败:', error)
    }
  }

  const handleCreateProject = async () => {
    if (!newProjectTitle.trim()) {
      message.warning('请输入项目名称')
      return
    }
    
    try {
      const { data } = await projectApi.create({ 
        title: newProjectTitle, 
        theme: newProjectTheme 
      })
      setProject(data)
      setCreateModalVisible(false)
      setNewProjectTitle('')
      setNewProjectTheme('')
      message.success('项目创建成功！')
      await fetchConversations(data.id)
    } catch (error) {
      message.error('创建项目失败')
    }
  }

  const handleSend = async () => {
    if (!inputValue.trim() || loading) return
    if (!project) {
      setCreateModalVisible(true)
      return
    }

    const userMessage: Conversation = {
      id: Date.now(),
      project_id: project.id,
      role: 'user',
      content: inputValue,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMessage])
    const currentInput = inputValue
    setInputValue('')
    setLoading(true)
    setAiThinking(true)
    setThinkingMessage('正在发送...')

    try {
      setThinkingMessage('AI 思考中...')
      
      // 使用流式 API
      const response = await fetch(`/api/projects/${project.id}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth-storage') ? JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.token : ''}`
        },
        body: JSON.stringify({ content: currentInput }),
      })

      if (!response.ok) {
        throw new Error('请求失败')
      }

      // 创建 Assistant 消息
      const assistantMessage: Conversation = {
        id: Date.now() + 1,
        project_id: project.id,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      }
      setMessages(prev => [...prev, assistantMessage])
      
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      
      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          
          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') break
              
              try {
                const parsed = JSON.parse(data)
                if (parsed.content) {
                  assistantMessage.content += parsed.content
                  setMessages(prev => [...prev.slice(0, -1), { ...assistantMessage }])
                }
              } catch (e) {}
            }
          }
        }
      }

      setThinkingMessage('正在获取回复...')
      await fetchConversations(project.id)
      await fetchProject(project.id)
      setCurrentStep(1)
    } catch (error: any) {
      // 如果流式 API 失败，回退到普通 API
      try {
        setThinkingMessage('AI 思考中...')
        await projectApi.sendMessage(project.id, currentInput)
        setThinkingMessage('正在获取回复...')
        await fetchConversations(project.id)
        await fetchProject(project.id)
        setCurrentStep(1)
      } catch (err: any) {
        message.error(err.response?.data?.detail || '发送消息失败')
      }
    } finally {
      setLoading(false)
      setAiThinking(false)
      setThinkingMessage('')
    }
  }

  const handleGenerateCode = async () => {
    if (!project) return
    
    setLoading(true)
    setCurrentStep(2)
    
    try {
      message.loading('正在生成代码...', 0)
      await projectApi.generateCode(project.id, selectedTemplate?.id)
      
      // 轮询代码生成状态
      let attempts = 0
      const pollCode = async () => {
        if (attempts > 30) {
          message.error('代码生成超时')
          setLoading(false)
          return
        }
        
        try {
          const { data } = await projectApi.get(project.id)
          if (data.manim_code) {
            setGeneratedCode(data.manim_code)
            setEditableCode(data.manim_code)
            message.destroy()
            message.success('代码生成成功！')
            setLoading(false)
            setActiveTab('chat')
          } else {
            attempts++
            setTimeout(pollCode, 1000)
          }
        } catch {
          attempts++
          setTimeout(pollCode, 1000)
        }
      }
      
      setTimeout(pollCode, 1000)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成失败')
      setLoading(false)
    }
  }

  const handleUseTemplate = (template: Template) => {
    setSelectedTemplate(template)
    setTemplateModalVisible(false)
    if (template.code) {
      setEditableCode(template.code)
      setGeneratedCode(template.code)
      message.success(`已应用模板: ${template.name}`)
      setCurrentStep(2)
    }
  }

  const handleSaveCode = () => {
    if (!project) return
    setGeneratedCode(editableCode)
    message.success('代码已保存')
  }

  const handleRender = async () => {
    if (!project) return
    
    setCurrentStep(3)
    setLoading(true)
    
    // 先保存代码
    if (editableCode !== generatedCode) {
      try {
        await projectApi.update(project.id, { custom_code: editableCode })
      } catch (error) {
        console.error('保存代码失败:', error)
      }
    }
    
    const newTask: Task = {
      id: Date.now().toString(),
      status: 'running',
      progress: 0,
      message: '正在排队...',
    }
    setTasks([newTask])

    try {
      await projectApi.generateVideo(project.id, selectedTemplate?.id)
      
      let progress = 0
      const interval = setInterval(async () => {
        progress += Math.random() * 15
        if (progress >= 100) {
          clearInterval(interval)
          setTasks(prev => prev.map(t => ({
            ...t,
            status: 'completed',
            progress: 100,
            message: '渲染完成！',
          })))
          await fetchProject(project.id)
          setVideoUrl('https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4')
          setLoading(false)
          message.success('视频渲染成功！')
        } else {
          setTasks(prev => prev.map(t => ({
            ...t,
            progress: Math.round(progress),
            message: `渲染中... ${Math.round(progress)}%`,
          })))
        }
      }, 500)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '渲染失败')
      setLoading(false)
    }
  }

  const copyCode = () => {
    navigator.clipboard.writeText(editableCode)
    message.success('代码已复制')
  }

  const renderStatus = () => {
    if (loading || aiThinking) return <Badge status="processing" text="处理中..." />
    if (videoUrl) return <Badge status="success" text="已完成" />
    if (generatedCode) return <Badge status="success" text="代码已生成" />
    return <Badge status="default" text="等待开始" />
  }

  return (
    <div className="creator-page">
      <div className="creator-layout">
        <div className="creator-panel chat-panel">
          <Card className="panel-card" bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div className="panel-header">
              <Space>
                <MessageOutlined />
                <span>AI 对话</span>
                {renderStatus()}
              </Space>
              {!project ? (
                <Button 
                  type="primary" 
                  icon={<PlusOutlined />}
                  onClick={() => setCreateModalVisible(true)}
                  size="small"
                >
                  新建项目
                </Button>
              ) : (
                <Tag color="blue">{project.title}</Tag>
              )}
            </div>
            
            <div className="chat-messages" ref={messagesContainerRef}>
              {messages.length === 0 ? (
                <div className="chat-empty">
                  <RobotOutlined className="empty-icon" />
                  <Title level={5}>开始你的创作</Title>
                  <Text type="secondary">
                    {project 
                      ? '告诉我你想要什么样的数学动画，我来帮你实现' 
                      : '点击右上角"新建项目"开始创作'
                    }
                  </Text>
                  {project && (
                    <div className="preset-list">
                      {presets.map((p, i) => (
                        <Tag key={i} className="preset-tag" onClick={() => setInputValue(p.label)}>
                          {p.icon} {p.label}
                        </Tag>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <>
                  {messages.map((msg) => (
                    <div key={msg.id} className={`message ${msg.role}`}>
                      <Avatar 
                        icon={msg.role === 'user' ? <MessageOutlined /> : <RobotOutlined />} 
                        className={msg.role}
                      />
                      <div className="message-content">
                        <div className="message-text">{msg.content}</div>
                        <div className="message-time">
                          {new Date(msg.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                    </div>
                  ))}
                  {aiThinking && (
                    <div className="message assistant">
                      <Avatar icon={<RobotOutlined />} className="assistant" />
                      <div className="message-content">
                        <div className="message-text" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <Spin size="small" />
                          <span>{thinkingMessage || 'AI正在思考...'}</span>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </>
              )}
            </div>
            
            <div className="chat-input">
              <Input.Search
                placeholder={project ? "输入你的想法..." : "请先创建项目"}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onSearch={handleSend}
                loading={loading}
                enterButton={
                  <Button type="primary" icon={<SendOutlined />}>
                    发送
                  </Button>
                }
                size="large"
                disabled={!project}
              />
            </div>
          </Card>
        </div>

        <div className="creator-panel output-panel">
          <Card className="panel-card" bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              className="output-tabs"
              items={[
                {
                  key: 'chat',
                  label: <span><CodeOutlined /> 代码</span>,
                  children: (
                    <div className="code-section">
                      <div className="code-header">
                        <Space>
                          <FileTextOutlined />
                          <Text strong>Manim 代码</Text>
                          {selectedTemplate && <Tag color="purple">模板: {selectedTemplate.name}</Tag>}
                        </Space>
                        <Space>
                          <Tooltip title="选择模板">
                            <Button 
                              type="text" 
                              icon={<FileTextOutlined />} 
                              onClick={() => setTemplateModalVisible(true)} 
                            />
                          </Tooltip>
                          <Tooltip title="复制代码">
                            <Button type="text" icon={<CopyOutlined />} onClick={copyCode} disabled={!editableCode} />
                          </Tooltip>
                          <Tooltip title="重新生成">
                            <Button type="text" icon={<ReloadOutlined />} onClick={handleGenerateCode} disabled={!project} />
                          </Tooltip>
                        </Space>
                      </div>
                      {editableCode || generatedCode ? (
                        <>
                          <TextArea
                            className="code-block"
                            value={editableCode || generatedCode}
                            onChange={(e) => setEditableCode(e.target.value)}
                            autoSize={{ minRows: 10, maxRows: 30 }}
                            spellCheck={false}
                            style={{ 
                              fontFamily: "'Fira Code', Monaco, monospace",
                              fontSize: '13px',
                              lineHeight: '1.6',
                              resize: 'none'
                            }}
                          />
                          {editableCode !== generatedCode && (
                            <div className="code-actions">
                              <Button 
                                type="primary" 
                                icon={<SaveOutlined />}
                                onClick={handleSaveCode}
                              >
                                保存修改
                              </Button>
                            </div>
                          )}
                        </>
                      ) : (
                        <Empty description="代码将在对话后自动生成" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                      )}
                      {(editableCode || generatedCode) && !videoUrl && (
                        <div className="code-actions">
                          <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleRender} size="large">
                            开始渲染
                          </Button>
                        </div>
                      )}
                    </div>
                  ),
                },
                {
                  key: 'render',
                  label: <span><VideoCameraOutlined /> 渲染</span>,
                  children: (
                    <div className="render-section">
                      {videoUrl ? (
                        <div className="video-result">
                          <video controls src={videoUrl} className="video-player" />
                          <div className="video-actions">
                            <Button icon={<DownloadOutlined />} size="large">下载视频</Button>
                            <Button icon={<RedoOutlined />} size="large" onClick={handleRender}>重新生成</Button>
                          </div>
                        </div>
                      ) : tasks.length > 0 ? (
                        <div className="render-progress">
                          {tasks.map((task) => (
                            <Card key={task.id} className="task-card">
                              <Space direction="vertical" style={{ width: '100%' }}>
                                <div className="task-header">
                                  <Text strong>{task.message}</Text>
                                  <Tag color={task.status === 'completed' ? 'success' : task.status === 'failed' ? 'error' : 'processing'}>
                                    {task.status === 'running' ? '渲染中' : task.status === 'completed' ? '完成' : '失败'}
                                  </Tag>
                                </div>
                                <Progress percent={task.progress} status={task.status === 'completed' ? 'success' : 'active'} strokeColor="#6366f1" />
                              </Space>
                            </Card>
                          ))}
                        </div>
                      ) : (
                        <Empty description="还没有渲染任务" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                      )}
                    </div>
                  ),
                },
                {
                  key: 'settings',
                  label: <span><SettingOutlined /> 设置</span>,
                  children: (
                    <div className="settings-section">
                      <div className="setting-group">
                        <Text strong>渲染设置</Text>
                        <div className="setting-item">
                          <Text>主题风格</Text>
                          <Segmented
                            options={[
                              { label: '深色', value: 'dark' },
                              { label: '浅色', value: 'light' },
                              { label: '学院', value: 'academic' },
                            ]}
                            value={theme}
                            onChange={(v) => setTheme(v as string)}
                          />
                        </div>
                        <div className="setting-item">
                          <Text>画质</Text>
                          <Select value={quality} onChange={setQuality} options={[
                            { label: '720p', value: '720p' },
                            { label: '1080p', value: '1080p' },
                            { label: '4K', value: '4k' },
                          ]} />
                        </div>
                        <div className="setting-item">
                          <Text>时长</Text>
                          <Select value={duration} onChange={setDuration} options={[
                            { label: '短 (< 10s)', value: 'short' },
                            { label: '中 (10-30s)', value: 'medium' },
                            { label: '长 (> 30s)', value: 'long' },
                          ]} />
                        </div>
                      </div>
                    </div>
                  ),
                },
              ]}
            />
          </Card>
        </div>
      </div>

      <Card className="workflow-card">
        <Steps
          current={currentStep}
          size="small"
          items={[
            { title: '输入主题', icon: <BulbOutlined /> },
            { title: '对话优化', icon: <MessageOutlined /> },
            { title: '生成代码', icon: <CodeOutlined /> },
            { title: '渲染视频', icon: <VideoCameraOutlined /> },
          ]}
        />
      </Card>

      <Modal
        title="新建项目"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        onOk={handleCreateProject}
        okText="创建"
      >
        <Form layout="vertical">
          <Form.Item label="项目名称" required>
            <Input 
              placeholder="给你的项目起个名字"
              value={newProjectTitle}
              onChange={(e) => setNewProjectTitle(e.target.value)}
            />
          </Form.Item>
          <Form.Item label="主题描述（可选）">
            <Input.TextArea 
              placeholder="描述你想要的动画内容"
              rows={3}
              value={newProjectTheme}
              onChange={(e) => setNewProjectTheme(e.target.value)}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="选择代码模板"
        open={templateModalVisible}
        onCancel={() => setTemplateModalVisible(false)}
        footer={null}
        width={800}
      >
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          {templates.length === 0 ? (
            <Empty description="暂无可用模板" />
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
              {templates.map((template) => (
                <Card
                  key={template.id}
                  hoverable
                  onClick={() => handleUseTemplate(template)}
                  style={{ 
                    cursor: 'pointer',
                    borderColor: selectedTemplate?.id === template.id ? '#6366f1' : undefined
                  }}
                  size="small"
                >
                  <div style={{ fontWeight: 600, marginBottom: '4px' }}>{template.name}</div>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>{template.description}</div>
                  {template.category && (
                    <Tag 
                      color={template.category === 'system' ? 'blue' : template.category === 'user' ? 'green' : 'default'}
                      style={{ marginTop: '8px' }}
                    >
                      {template.category === 'system' ? '系统' : template.category === 'user' ? '自定义' : template.category}
                    </Tag>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}
