import { useEffect, useState, useRef } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { Card, Progress, Button, Space, message, Spin, Tabs, Collapse } from 'antd'
import { DownloadOutlined, PlayCircleOutlined, CodeOutlined, CloudUploadOutlined, CopyOutlined, CheckOutlined } from '@ant-design/icons'
import { projectApi, Task, Project } from '@/services/project'
import { motion } from 'framer-motion'

const { Panel } = Collapse

const statusMap: Record<string, { text: string; color: string }> = {
  pending: { text: '等待中', color: '#faad14' },
  processing: { text: '处理中', color: '#0066FF' },
  code_generated: { text: '代码已生成', color: '#00CCFF' },
  completed: { text: '已完成', color: '#52c41a' },
  failed: { text: '失败', color: '#ff4d4f' },
}

export default function ProjectTask() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [task, setTask] = useState<Task | null>(null)
  const [loading, setLoading] = useState(true)
  const [generatingCode, setGeneratingCode] = useState(false)
  const [generatingVideo, setGeneratingVideo] = useState(false)
  const [codeProgress, setCodeProgress] = useState(0)
  const [codeMessage, setCodeMessage] = useState('')
  const [generatedCode, setGeneratedCode] = useState('')
  const [activeTab, setActiveTab] = useState('code')
  const [copied, setCopied] = useState(false)
  const codeRef = useRef<HTMLPreElement>(null)

  const fetchProject = async () => {
    try {
      const { data } = await projectApi.get(Number(id))
      setProject(data)
      if (data.manim_code) {
        setGeneratedCode(data.manim_code)
      }
    } catch (error: any) {
      message.error('获取项目失败: ' + (error.message || error.toString()))
    }
  }

  const fetchTask = async () => {
    try {
      if (!project?.id) return
      const tasksRes = await projectApi.getTask(project.id)
      setTask(tasksRes.data)
    } catch (error) {
      // 可能还没有任务
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProject()
  }, [id])

  useEffect(() => {
    if (project) {
      fetchTask()
    }
  }, [project])

  useEffect(() => {
    if (project && searchParams.get('autoGenerate') === 'true') {
      const timer = setTimeout(() => {
        if (!generatedCode && project.final_script) {
          handleGenerateCode()
        }
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [project, generatedCode])

  const handleGenerateCode = async () => {
    const templateId = searchParams.get('templateId')
    setGeneratingCode(true)
    setCodeProgress(0)
    setCodeMessage('正在开始生成...')
    setGeneratedCode('')
    setActiveTab('code')

    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
      const response = await fetch(
        `${API_BASE}/api/tasks/${id}/generate-code${templateId ? `?template_id=${templateId}` : ''}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth-token')}`
          }
        }
      )

      if (!response.ok) {
        const err = await response.text()
        throw new Error(err || '请求失败')
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('无法读取响应')
      }

      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        
        const parts = buffer.split('data: ')
        buffer = parts.pop() || ''

        for (const part of parts) {
          const trimmed = part.trim()
          if (!trimmed) continue
          
          try {
            const data = JSON.parse(trimmed)
            setCodeProgress(data.progress || 0)
            setCodeMessage(data.message || '')
            
            if (data.code) {
              setGeneratedCode(data.code)
            }
            
            if (data.step === 'error') {
              message.error(data.message)
            }
          } catch (e) {}
        }
      }

      if (buffer.trim()) {
        try {
          const data = JSON.parse(buffer.trim())
          if (data.code) setGeneratedCode(data.code)
        } catch (e) {}
      }

      message.success('代码生成完成！')
      await fetchProject()
    } catch (error: any) {
      console.error('生成代码失败:', error)
      message.error(error.message || '生成失败')
    } finally {
      setGeneratingCode(false)
    }
  }

  const handleGenerateVideo = async () => {
    if (!generatedCode) {
      message.warning('请先生成代码')
      return
    }
    
    const templateId = searchParams.get('templateId')
    setGeneratingVideo(true)
    
    try {
      const { data } = await projectApi.generateVideo(Number(id), templateId ? Number(templateId) : undefined)
      setTask(data)
      
      const pollInterval = setInterval(async () => {
        try {
          const { data: updatedTask } = await projectApi.getTask(data.id)
          setTask(updatedTask)
          
          if (updatedTask.status === 'processing') {
            // 渲染中会自动更新进度条
          }
          
          if (updatedTask.status !== 'processing' && updatedTask.status !== 'pending') {
            clearInterval(pollInterval)
            setGeneratingVideo(false)
            if (updatedTask.status === 'completed') {
              message.success('视频生成完成！')
            } else if (updatedTask.status === 'failed') {
              message.error(`生成失败：${updatedTask.error_message}`)
            }
          }
        } catch (e) {
          console.error('获取任务状态失败', e)
        }
      }, 2000)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成失败')
      setGeneratingVideo(false)
    }
  }

  const handleDownloadVideo = () => {
    if (task?.video_url) {
      window.open(task.video_url, '_blank')
    }
  }

  const handleCopyCode = () => {
    if (generatedCode) {
      navigator.clipboard.writeText(generatedCode)
      setCopied(true)
      message.success('代码已复制到剪贴板')
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleDownloadCode = () => {
    if (generatedCode) {
      const blob = new Blob([generatedCode], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `AI视频_scene_${id}.py`
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <Card
          title={
            <Space>
              <span className="text-lg font-bold">{project?.title}</span>
              {task && (
                <span style={{ color: statusMap[task.status]?.color }}>
                  ({statusMap[task.status]?.text})
                </span>
              )}
            </Space>
          }
          extra={
            <Button onClick={() => navigate(`/project/${id}/chat`)}>
              返回编辑
            </Button>
          }
        >
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            <Tabs.TabPane tab={<span><CodeOutlined /> 代码生成</span>} key="code">
              <div className="space-y-4">
                {/* 进度显示 */}
                {generatingCode && (
                  <motion.div 
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="bg-gradient-to-r from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 p-4 rounded-xl border border-blue-100 dark:border-blue-800"
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <Spin />
                      <span className="text-blue-600 dark:text-blue-400 font-medium">{codeMessage}</span>
                    </div>
                    <Progress 
                      percent={codeProgress} 
                      status="active"
                      strokeColor={{
                        '0%': '#0066FF',
                        '100%': '#00CCFF',
                      }}
                    />
                  </motion.div>
                )}

                {/* 生成代码按钮 */}
                <div className="flex gap-3">
                  <Button 
                    type="primary" 
                    icon={<CodeOutlined />}
                    onClick={handleGenerateCode}
                    loading={generatingCode}
                    size="large"
                    className="btn-gradient"
                  >
                    {generatedCode ? '重新生成代码' : '生成代码'}
                  </Button>
                  
                  {generatedCode && (
                    <>
                      <Button 
                        icon={<DownloadOutlined />}
                        onClick={handleDownloadCode}
                        size="large"
                      >
                        下载代码
                      </Button>
                      <Button 
                        icon={copied ? <CheckOutlined /> : <CopyOutlined />}
                        onClick={handleCopyCode}
                        size="large"
                        type={copied ? 'primary' : 'default'}
                      >
                        {copied ? '已复制' : '复制代码'}
                      </Button>
                    </>
                  )}
                </div>

                {/* 代码显示 */}
                {generatedCode && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <Collapse defaultActiveKey={['code']}>
                      <Panel 
                        header={
                          <div className="flex items-center gap-2">
                            <CodeOutlined className="text-[#0066FF]" />
                            <span>生成的 AI视频 代码</span>
                          </div>
                        } 
                        key="code"
                      >
                        <div className="code-block relative">
                          <pre 
                            ref={codeRef}
                            className="text-sm max-h-96 overflow-y-auto"
                          >
                            {generatedCode}
                          </pre>
                        </div>
                      </Panel>
                    </Collapse>
                  </motion.div>
                )}
              </div>
            </Tabs.TabPane>

            <Tabs.TabPane tab={<span><CloudUploadOutlined /> 视频渲染</span>} key="video">
              <div className="space-y-4">
                {/* 任务状态 */}
                {task ? (
                  <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="bg-gray-50 dark:bg-gray-800/50 p-6 rounded-xl"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <span className="font-medium">渲染状态</span>
                      <span 
                        className="status-badge"
                        style={{ 
                          backgroundColor: `${statusMap[task.status]?.color}20`,
                          color: statusMap[task.status]?.color 
                        }}
                      >
                        {statusMap[task.status]?.text}
                      </span>
                    </div>
                    <Progress 
                      percent={task.progress} 
                      status={task.status === 'failed' ? 'exception' : task.status === 'completed' ? 'success' : 'active'}
                      strokeColor={{
                        '0%': '#0066FF',
                        '100%': '#00CCFF',
                      }}
                    />
                    {task.error_message && (
                      <div className="text-red-500 mt-3 text-sm bg-red-50 dark:bg-red-900/20 p-3 rounded-lg">
                        错误: {task.error_message}
                      </div>
                    )}
                  </motion.div>
                ) : (
                  <div className="text-center py-12 text-gray-400">
                    尚未开始渲染
                  </div>
                )}

                {/* 渲染按钮 */}
                <div className="flex gap-3">
                  <Button 
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    onClick={handleGenerateVideo}
                    loading={generatingVideo}
                    disabled={!generatedCode}
                    size="large"
                    className="btn-gradient"
                  >
                    {task?.status === 'completed' ? '重新渲染' : '开始渲染视频'}
                  </Button>

                  {task?.video_url && (
                    <Button 
                      type="primary"
                      icon={<DownloadOutlined />}
                      onClick={handleDownloadVideo}
                      size="large"
                      className="btn-gradient"
                    >
                      下载视频
                    </Button>
                  )}
                </div>

                {/* 视频预览 */}
                {task?.video_url && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="mt-6"
                  >
                    <video
                      src={task.video_url}
                      controls
                      className="w-full rounded-xl shadow-lg"
                      style={{ maxHeight: '60vh' }}
                    >
                      您的浏览器不支持视频播放
                    </video>
                  </motion.div>
                )}
              </div>
            </Tabs.TabPane>
          </Tabs>
        </Card>
      </motion.div>
    </div>
  )
}
