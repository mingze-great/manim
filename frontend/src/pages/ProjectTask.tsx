import { useEffect, useState, useRef } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { Card, Progress, Button, Space, message, Spin, Tabs, Collapse, Select, Modal } from 'antd'
import { DownloadOutlined, PlayCircleOutlined, PlaySquareOutlined, CloudUploadOutlined, EyeOutlined } from '@ant-design/icons'
import { projectApi, Task, Project } from '@/services/project'
import { templateApi, Template } from '@/services/template'
import { useAuthStore } from '@/stores/authStore'
import { motion } from 'framer-motion'

const { Panel } = Collapse

const statusMap: Record<string, { text: string; color: string }> = {
  pending: { text: '等待中', color: '#faad14' },
  processing: { text: '处理中', color: '#0066FF' },
  code_generated: { text: '脚本就绪', color: '#00CCFF' },
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
  const [videoProgress, setVideoProgress] = useState(0)
  const [videoMessage, setVideoMessage] = useState('')
  const [generatedCode, setGeneratedCode] = useState('')
  const [activeTab, setActiveTab] = useState('code')
  const [terminalLog, setTerminalLog] = useState('')
  const [showTerminal, setShowTerminal] = useState(false)
  const [renderError, setRenderError] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)
  const [videoPreviewVisible, setVideoPreviewVisible] = useState(false)
  const [previewVideoUrl, setPreviewVideoUrl] = useState<string>('')
  const codeRef = useRef<HTMLPreElement>(null)
  const terminalRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null)

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
    } catch (error: any) {
      if (error.response?.status !== 404) {
        console.error('获取任务失败:', error)
      }
    } finally {
      setLoading(false)
    }
  }

  const fetchTemplates = async () => {
    try {
      const { data } = await templateApi.list()
      const allTemplates = [...data.system_templates, ...data.user_templates]
      setTemplates(allTemplates.filter(t => t.is_active !== false))
    } catch (error) {
      console.error('获取模板失败:', error)
    }
  }
  
  const fetchAvailableModels = async () => {
    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
      const response = await fetch(`${API_BASE}/api/tasks/available-models`)
      if (response.ok) {
        const data = await response.json()
        setAvailableModels(data.models || [])
      }
    } catch (error) {
      console.error('获取模型列表失败:', error)
    }
  }

useEffect(() => {
    if (id) {
      fetchProject()
      fetchTemplates()
      fetchAvailableModels()
    }
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
    setGeneratingCode(true)
    setCodeProgress(0)
    setCodeMessage('正在开始生成...')
    setGeneratedCode('')
    setActiveTab('code')

    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
      const token = (useAuthStore.getState().token) || ''
      console.log('[generateCode] API_BASE:', API_BASE)
      console.log('[generateCode] id:', id)
      console.log('[generateCode] templateId:', selectedTemplateId)
      let streamUrl = `${API_BASE}/api/tasks/${id}/generate-code`
      if (selectedTemplateId) {
        streamUrl += `?template_id=${selectedTemplateId}`
        if (selectedModel) {
          streamUrl += `&model=${selectedModel}`
        }
      } else if (selectedModel) {
        streamUrl += `?model=${selectedModel}`
      }
      console.log('[generateCode] streamUrl:', streamUrl)
      let headers: any = {
        'Content-Type': 'application/json'
      }
      if (token) headers['Authorization'] = `Bearer ${token}`

      let response = await fetch(streamUrl, {
        headers
      })

      if (response.status === 401) {
        message.error('未通过身份验证，请重新登录后再试')
        setLoading(false)
        return
      }

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

      message.success('脚本生成完成！')
      await fetchProject()
    } catch (error: any) {
      console.error('生成脚本失败:', error)
      message.error(error.message || '生成失败')
    } finally {
      setGeneratingCode(false)
    }
  }

  const handleGenerateVideo = async () => {
    if (!generatedCode) {
      message.warning('请先生成脚本')
      return
    }
    
    setGeneratingVideo(true)
    setVideoProgress(5)
    setVideoMessage('正在准备渲染...')
    setTerminalLog('')
    setShowTerminal(true)
    setRenderError(null)
    setTask(null)
    
    abortControllerRef.current = new AbortController()
    
    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
      const token = useAuthStore.getState().token
      const streamUrl = `${API_BASE}/api/tasks/${id}/render`
      
      const response = await fetch(streamUrl, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        signal: abortControllerRef.current.signal
      })
      
      if (response.status === 401) {
        message.error('登录已过期，请重新登录')
        setGeneratingVideo(false)
        setTerminalLog(prev => prev + '\n❌ 登录已过期，请重新登录\n')
        return
      }
      
      if (!response.ok) {
        throw new Error(`请求失败 (${response.status})`)
      }
      
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      
      if (!reader) {
        throw new Error('无法读取服务器响应')
      }
      
      readerRef.current = reader
      
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            try {
              const parsed = JSON.parse(data)
              
              if (parsed.type === 'error') {
                setTerminalLog(prev => prev + `\n❌ ${parsed.content}\n`)
                setRenderError(parsed.content)
                message.error(parsed.content)
              } else if (parsed.type === 'success') {
                setTerminalLog(prev => prev + `\n✅ ${parsed.content}\n`)
                setVideoProgress(100)
                setVideoMessage('渲染完成！')
                if (parsed.video_url) {
                  setProject(prev => prev ? { ...prev, video_url: parsed.video_url, status: 'completed' } : null)
                }
                message.success('视频渲染完成！')
              } else if (parsed.type === 'info' || parsed.type === 'output') {
                setTerminalLog(prev => prev + parsed.content + '\n')
                const content = parsed.content.toLowerCase()
                if (content.includes('animation') || content.includes('rendering')) {
                  setVideoProgress(prev => Math.min(prev + 2, 90))
                  setVideoMessage('正在渲染动画...')
                } else if (content.includes('combining') || content.includes('writing')) {
                  setVideoProgress(prev => Math.min(prev + 3, 95))
                  setVideoMessage('正在合成视频...')
                } else if (content.includes('file')) {
                  setVideoProgress(15)
                  setVideoMessage('准备渲染环境...')
                }
              }
              
              setTimeout(() => {
                terminalRef.current?.scrollTo({ top: terminalRef.current.scrollHeight, behavior: 'smooth' })
              }, 50)
            } catch (e) {
              console.error('Parse error:', e)
            }
          }
        }
      }
    } catch (error: any) {
      const errorMsg = error.message || '未知错误'
      message.error('渲染失败: ' + errorMsg)
      setRenderError(errorMsg)
      setTerminalLog(prev => prev + `\n❌ 渲染失败: ${errorMsg}\n`)
      setVideoProgress(0)
    } finally {
      setGeneratingVideo(false)
      await fetchProject()
    }
  }

  const handleDownloadVideo = async () => {
    const videoUrl = task?.video_url || project?.video_url
    if (videoUrl) {
      try {
        const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
        const token = useAuthStore.getState().token
        const fullUrl = videoUrl.startsWith('http') ? videoUrl : `${API_BASE}${videoUrl}`
        
        const response = await fetch(fullUrl, {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        })
        
        if (!response.ok) {
          throw new Error('下载失败')
        }
        
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `video_${id}_${Date.now()}.mp4`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        message.success('视频下载成功')
      } catch (error) {
        message.error('视频下载失败，请重试')
      }
    }
  }

  const handleBackToEdit = () => {
    const errorLog = terminalLog ? terminalLog.split('\n').slice(-100).join('\n') : ''
    navigate(`/project/${id}/chat`, { 
      state: { 
        renderErrorLog: errorLog,
        currentCode: generatedCode,
        fromRender: true 
      } 
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spin size="large" />
      </div>
    )
  }

  return (
    <>
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
            <Tabs.TabPane tab={<span><PlaySquareOutlined /> 脚本生成</span>} key="code">
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

                {/* 模板选择 */}
                <div className="mb-4">
                  <label className="block text-sm text-gray-500 mb-2">选择视频风格模板</label>
                  <div className="flex items-center gap-2 flex-wrap">
                    <Select
                      style={{ width: '100%', maxWidth: 300 }}
                      placeholder="默认风格"
                      allowClear
                      value={selectedTemplateId}
                      onChange={setSelectedTemplateId}
                      options={templates.map(t => ({
                        label: t.name,
                        value: t.id
                      }))}
                    />
                    {selectedTemplateId && templates.find(t => t.id === selectedTemplateId)?.example_video_url && (
                      <Button
                        icon={<EyeOutlined />}
                        onClick={() => {
                          const template = templates.find(t => t.id === selectedTemplateId)
                          if (template?.example_video_url) {
                            const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
                            setPreviewVideoUrl(template.example_video_url.startsWith('http') 
                              ? template.example_video_url 
                              : `${API_BASE}${template.example_video_url}`)
                            setVideoPreviewVisible(true)
                          }
                        }}
                      >
                        预览示例
                      </Button>
                    )}
                  </div>
                  {selectedTemplateId && templates.find(t => t.id === selectedTemplateId)?.description && (
                    <div className="text-xs text-gray-400 mt-1">
                      {templates.find(t => t.id === selectedTemplateId)?.description}
                    </div>
                  )}
                </div>

                {/* 生成脚本按钮 */}
                <div className="flex gap-3">
                  <Button 
                    type="primary" 
                    icon={<PlaySquareOutlined />}
                    onClick={handleGenerateCode}
                    loading={generatingCode}
                    size="large"
                    className="btn-gradient"
                  >
                    {generatedCode ? '重新生成脚本' : '生成脚本'}
                  </Button>
                </div>

                {/* 脚本显示 */}
                {generatedCode && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <Collapse defaultActiveKey={['code']}>
                      <Panel 
                        header={
                          <div className="flex items-center gap-2">
                            <PlaySquareOutlined className="text-[#0066FF]" />
                            <span>生成的动画脚本</span>
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
                {/* 渲染进度显示 */}
                {generatingVideo && (
                  <motion.div 
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 p-4 rounded-xl border border-purple-100 dark:border-purple-800"
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <Spin />
                      <span className="text-purple-600 dark:text-purple-400 font-medium">{videoMessage}</span>
                    </div>
                    <Progress 
                      percent={videoProgress} 
                      status="active"
                      strokeColor={{
                        '0%': '#722ed1',
                        '100%': '#eb2f96',
                      }}
                    />
                  </motion.div>
                )}

                {/* 任务状态 */}
                {(task || generatingVideo || project?.video_url) ? (
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
                          backgroundColor: `${statusMap[task?.status || (generatingVideo ? 'processing' : 'completed')]?.color}20`,
                          color: statusMap[task?.status || (generatingVideo ? 'processing' : 'completed')]?.color 
                        }}
                      >
                        {statusMap[task?.status || (generatingVideo ? 'processing' : 'completed')]?.text}
                      </span>
                    </div>
                    <Progress 
                      percent={task?.progress || videoProgress} 
                      status={task?.status === 'failed' || renderError ? 'exception' : task?.status === 'completed' || project?.video_url ? 'success' : 'active'}
                      strokeColor={{
                        '0%': '#0066FF',
                        '100%': '#00CCFF',
                      }}
                    />
                    {renderError && (
                      <div className="text-red-500 mt-3 text-sm bg-red-50 dark:bg-red-900/20 p-3 rounded-lg">
                        错误: {renderError}
                      </div>
                    )}
                  </motion.div>
                ) : (
                  <div className="text-center py-12 text-gray-400">
                    尚未开始渲染
                  </div>
                )}

                {/* 终端输出 */}
                {(showTerminal || terminalLog) && (
                  <div className="mt-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">终端输出</span>
                      <Button size="small" onClick={() => setShowTerminal(!showTerminal)}>
                        {showTerminal ? '收起' : '展开'}
                      </Button>
                    </div>
                    {showTerminal && (
                      <div 
                        ref={terminalRef}
                        className="bg-gray-900 text-gray-100 p-4 rounded-lg text-xs font-mono max-h-64 overflow-auto"
                      >
                        {terminalLog || '等待渲染开始...\n'}
                      </div>
                    )}
                  </div>
                )}

                {/* 渲染失败时的返回按钮 */}
                {renderError && (
                  <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200">
                    <p className="text-red-600 mb-3">渲染失败，返回对话让智能助手修复问题。</p>
                    <Button type="primary" onClick={handleBackToEdit}>
                      返回对话修复
                    </Button>
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

                  {project?.video_url && (
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
                {project?.video_url && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="mt-6"
                  >
                    <video
                      src={project.video_url.startsWith('http') ? project.video_url : `${import.meta.env.VITE_API_BASE_URL || ''}${project.video_url}`}
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
      
      <TemplateVideoPreviewModal 
        visible={videoPreviewVisible} 
        videoUrl={previewVideoUrl} 
        onClose={() => setVideoPreviewVisible(false)} 
      />
    </>
  )
}


function TemplateVideoPreviewModal({ visible, videoUrl, onClose }: { visible: boolean; videoUrl: string; onClose: () => void }) {
  return (
    <Modal
      title="模板示例视频"
      open={visible}
      onCancel={onClose}
      footer={null}
      width={800}
      centered
    >
      <video
        src={videoUrl}
        controls
        className="w-full rounded-lg"
        autoPlay
      />
    </Modal>
  )
}
