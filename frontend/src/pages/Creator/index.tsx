import { useState, useRef, useEffect } from 'react'
import { 
  Card, Button, Input, Tabs, Steps, Progress, Spin, 
  Space, Tag, Typography, message, Badge, Tooltip,
  Empty, Segmented, Select, Avatar
} from 'antd'
import {
  SendOutlined, RobotOutlined, CodeOutlined, PlayCircleOutlined,
  CopyOutlined, ReloadOutlined, DownloadOutlined,
  SettingOutlined, BulbOutlined, MessageOutlined, FileTextOutlined,
  VideoCameraOutlined, RedoOutlined
} from '@ant-design/icons'
import './Creator.css'

const { Text, Title } = Typography

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

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
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [theme, setTheme] = useState('dark')
  const [quality, setQuality] = useState('720p')
  const [duration, setDuration] = useState('short')
  const [generatedCode, setGeneratedCode] = useState('')
  const [tasks, setTasks] = useState<Task[]>([])
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!inputValue.trim() || loading) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setLoading(true)

    setTimeout(() => {
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '好的，我已经理解了你的需求。让我为你生成一个基于勾股定理的动画脚本。你希望包含哪些具体内容？\n\n1. 三角形的绘制过程\n2. 各边长的标注\n3. 证明步骤的展示\n\n请告诉我你的具体需求。',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, assistantMessage])
      setLoading(false)
      setCurrentStep(1)
    }, 1500)
  }

  const handleGenerateCode = () => {
    setLoading(true)
    setCurrentStep(2)
    
    setTimeout(() => {
      const code = `from manim import *

class PythagoreanTheorem(Scene):
    def construct(self):
        title = Text("勾股定理").scale(1.5)
        self.play(Write(title))
        self.wait()
        self.play(title.animate.shift(UP * 3))
        
        triangle = Polygon(
            [-2, -1, 0], [2, -1, 0], [2, 1, 0],
            color=BLUE, fill_opacity=0.3
        )
        
        self.play(Create(triangle))
        self.wait()
        
        formula = MathTex("a^2 + b^2 = c^2").scale(1.5)
        self.play(Write(formula))
        self.wait()
`
      setGeneratedCode(code)
      setLoading(false)
      message.success('代码生成成功！')
    }, 2000)
  }

  const handleRender = () => {
    setCurrentStep(3)
    setLoading(true)
    
    const newTask: Task = {
      id: Date.now().toString(),
      status: 'running',
      progress: 0,
      message: '正在排队...',
    }
    setTasks([newTask])

    let progress = 0
    const interval = setInterval(() => {
      progress += Math.random() * 15
      if (progress >= 100) {
        clearInterval(interval)
        setTasks(prev => prev.map(t => ({
          ...t,
          status: 'completed',
          progress: 100,
          message: '渲染完成！',
        })))
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
  }

  const copyCode = () => {
    navigator.clipboard.writeText(generatedCode)
    message.success('代码已复制')
  }

  const renderStatus = () => {
    if (loading) return <Badge status="processing" text="处理中..." />
    if (videoUrl) return <Badge status="success" text="已完成" />
    if (generatedCode) return <Badge status="success" text="代码已生成" />
    return <Badge status="default" text="等待开始" />
  }

  return (
    <div className="creator-page">
      <div className="creator-layout">
        <div className="creator-panel chat-panel">
          <Card className="panel-card" bodyStyle={{ padding: 0 }}>
            <div className="panel-header">
              <Space>
                <MessageOutlined />
                <span>AI 对话</span>
                {renderStatus()}
              </Space>
            </div>
            <div className="chat-messages">
              {messages.length === 0 ? (
                <div className="chat-empty">
                  <RobotOutlined className="empty-icon" />
                  <Title level={5}>开始你的创作</Title>
                  <Text type="secondary">
                    告诉我你想要什么样的数学动画，我来帮你实现
                  </Text>
                  <div className="preset-list">
                    {presets.map((p, i) => (
                      <Tag key={i} className="preset-tag" onClick={() => setInputValue(p.label)}>
                        {p.icon} {p.label}
                      </Tag>
                    ))}
                  </div>
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
                          {msg.timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                    </div>
                  ))}
                  {loading && (
                    <div className="message assistant">
                      <Avatar icon={<RobotOutlined />} className="assistant" />
                      <div className="message-content">
                        <Spin size="small" /> 正在思考...
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </>
              )}
            </div>
            <div className="chat-input">
              <Input.Search
                placeholder="输入你的想法..."
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
              />
            </div>
          </Card>
        </div>

        <div className="creator-panel output-panel">
          <Card className="panel-card" bodyStyle={{ padding: 0 }}>
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
                        </Space>
                        <Space>
                          <Tooltip title="复制代码">
                            <Button type="text" icon={<CopyOutlined />} onClick={copyCode} />
                          </Tooltip>
                          <Tooltip title="重新生成">
                            <Button type="text" icon={<ReloadOutlined />} onClick={handleGenerateCode} />
                          </Tooltip>
                        </Space>
                      </div>
                      {generatedCode ? (
                        <pre className="code-block"><code>{generatedCode}</code></pre>
                      ) : (
                        <Empty description="代码将在对话后自动生成" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                      )}
                      {generatedCode && !videoUrl && (
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
                            <Button icon={<RedoOutlined />} size="large">重新生成</Button>
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
    </div>
  )
}
