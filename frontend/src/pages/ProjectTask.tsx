import { useEffect, useState, useRef } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { Card, Progress, Button, Space, message, Spin, Tabs, Select, Modal } from 'antd'
import { DownloadOutlined, PlayCircleOutlined, PlaySquareOutlined, CloudUploadOutlined, EyeOutlined } from '@ant-design/icons'
import { projectApi, Task, Project } from '@/services/project'
import { templateApi, Template } from '@/services/template'
import { useAuthStore } from '@/stores/authStore'
import { motion } from 'framer-motion'
import StickmanProjectTask from './StickmanProjectTask'

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
  const { user } = useAuthStore()
  const [project, setProject] = useState<Project | null>(null)
  const [task, setTask] = useState<Task | null>(null)
  const [loading, setLoading] = useState(true)
  const [generatingCode, setGeneratingCode] = useState(false)
  const [generatingVideo, setGeneratingVideo] = useState(false)
  const [downloadingVideo, setDownloadingVideo] = useState(false)
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
  const terminalRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null)
  const renderStartTimeRef = useRef<number>(0)
  const lastOutputTimeRef = useRef<number>(0)
  const renderTimeoutRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const CLIENT_RENDER_TIMEOUT = 330000

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
      const activeTemplates = allTemplates.filter(t => t.is_active !== false)
      setTemplates(activeTemplates)
      if (activeTemplates.length > 0 && !selectedTemplateId) {
        setSelectedTemplateId(activeTemplates[0].id)
      }
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
        if (data.default_code_model && !selectedModel) {
          setSelectedModel(data.default_code_model)
        }
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

    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
      const token = (useAuthStore.getState().token) || ''
      let streamUrl = `${API_BASE}/api/tasks/${id}/generate-code`
      if (selectedTemplateId) {
        streamUrl += `?template_id=${selectedTemplateId}`
        if (selectedModel) {
          streamUrl += `&model=${selectedModel}`
        }
      } else if (selectedModel) {
        streamUrl += `?model=${selectedModel}`
      }
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
    
    const visualPermission: any = user?.module_permissions?.visual
    if (visualPermission && !user?.is_admin) {
      const used = visualPermission.used_today || 0
      const limit = visualPermission.daily_limit || 0
      if (limit > 0 && used >= limit) {
        const periodLabel = visualPermission.period === 'monthly' ? '本月' : '今日'
        message.error(`${periodLabel}配额已用完（${used}/${limit}），请明天再试`)
        return
      }
    }
    
    setGeneratingVideo(true)
    setVideoProgress(5)
    setVideoMessage('正在准备渲染...')
    setTerminalLog('')
    setShowTerminal(true)
    setRenderError(null)
    setTask(null)
    
    abortControllerRef.current = new AbortController()
    renderStartTimeRef.current = Date.now()
    lastOutputTimeRef.current = Date.now()
    
    const checkTimeout = () => {
      const now = Date.now()
      const elapsed = now - renderStartTimeRef.current
      const noOutputElapsed = now - lastOutputTimeRef.current
      
      if (elapsed > CLIENT_RENDER_TIMEOUT) {
        setRenderError(`渲染超时（超过${Math.floor(CLIENT_RENDER_TIMEOUT / 60000)}分钟）`)
        setTerminalLog(prev => prev + `\n⚠️ 客户端检测：渲染超时，正在终止...\n`)
        abortControllerRef.current?.abort()
        return true
      }
      
      if (noOutputElapsed > 120000) {
        setTerminalLog(prev => prev + `\n⚠️ 警告：${Math.floor(noOutputElapsed / 1000)}秒无输出\n`)
      }
      
      return false
    }
    
    renderTimeoutRef.current = setInterval(checkTimeout, 10000)
    
    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
      const token = useAuthStore.getState().token
      const streamUrl = `${API_BASE}/api/tasks/${id}/render`
      
      setTerminalLog(prev => prev + `⏱️ 渲染开始时间: ${new Date().toLocaleTimeString()}\n`)
      setTerminalLog(prev => prev + `🛡️ 超时保护: 服务器${300}秒, 客户端${Math.floor(CLIENT_RENDER_TIMEOUT / 60000)}分钟\n\n`)
      
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
                lastOutputTimeRef.current = Date.now()
                setTerminalLog(prev => prev + `\n❌ ${parsed.content}\n`)
                setRenderError(parsed.content)
                message.error(parsed.content)
              } else if (parsed.type === 'success') {
                lastOutputTimeRef.current = Date.now()
                const elapsed = Math.floor((Date.now() - renderStartTimeRef.current) / 1000)
                setTerminalLog(prev => prev + `\n✅ ${parsed.content} (总耗时: ${elapsed}秒)\n`)
                setVideoProgress(100)
                setVideoMessage('渲染完成！')
                if (parsed.video_url) {
                  setProject(prev => prev ? { ...prev, video_url: parsed.video_url, status: 'completed' } : null)
                }
                message.success('视频渲染完成！')
              } else if (parsed.type === 'info' || parsed.type === 'output') {
                lastOutputTimeRef.current = Date.now()
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
      if (error.name === 'AbortError') {
        const errorMsg = '渲染已取消（超时保护）'
        message.warning(errorMsg)
        setRenderError(errorMsg)
        setTerminalLog(prev => prev + `\n⚠️ ${errorMsg}\n`)
      } else {
        const errorMsg = error.message || '未知错误'
        message.error('渲染失败: ' + errorMsg)
        setRenderError(errorMsg)
        setTerminalLog(prev => prev + `\n❌ 渲染失败: ${errorMsg}\n`)
      }
      setVideoProgress(0)
    } finally {
      if (renderTimeoutRef.current) {
        clearInterval(renderTimeoutRef.current)
        renderTimeoutRef.current = null
      }
      setGeneratingVideo(false)
      await fetchProject()
    }
  }

  const handleCancelRender = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      setTerminalLog(prev => prev + '\n⚠️ 用户取消渲染\n')
      message.warning('正在取消渲染...')
    }
  }

  const handleDownloadVideo = async () => {
    const videoUrl = task?.video_url || project?.video_url
    if (!videoUrl) return
    
    setDownloadingVideo(true)
    
    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
      const token = useAuthStore.getState().token
      const fullUrl = videoUrl.startsWith('http') ? videoUrl : `${API_BASE}${videoUrl}`
      
      message.loading({ content: '准备下载...', key: 'download', duration: 0 })
      
      const response = await fetch(fullUrl, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
      
      if (!response.ok) {
        throw new Error('下载失败')
      }
      
      const contentLength = response.headers.get('content-length')
      const total = contentLength ? parseInt(contentLength, 10) : 0
      
      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('无法读取响应')
      }
      
      const chunks: Uint8Array[] = []
      let receivedLength = 0
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        chunks.push(value)
        receivedLength += value.length
        
        if (total > 0) {
          const progress = Math.round((receivedLength / total) * 100)
          message.loading({ content: `下载中... ${progress}%`, key: 'download', duration: 0 })
        }
      }
      
      const blob = new Blob(chunks)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `video_${id}_${Date.now()}.mp4`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      
      message.success({ content: '视频下载成功！', key: 'download' })
    } catch (error) {
      console.error('下载失败:', error)
      message.error({ content: '视频下载失败，请重试', key: 'download' })
    } finally {
      setDownloadingVideo(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spin size="large" />
      </div>
    )
  }

  if (project?.module_type === 'stickman') {
    return <StickmanProjectTask />
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

                {/* 模板和模型选择 */}
                <div className="mb-4">
                  <div className="flex items-center gap-3 flex-wrap mb-2">
                    <div>
                      <label className="block text-sm text-gray-500 mb-1">视频风格模板</label>
                      <Select
                        style={{ width: 200 }}
                        placeholder="默认风格"
                        allowClear
                        value={selectedTemplateId}
                        onChange={setSelectedTemplateId}
                        options={templates.map(t => ({
                          label: t.name,
                          value: t.id
                        }))}
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm text-gray-500 mb-1">
                        AI 模型
                        <span className="text-xs text-green-500 ml-2">推荐首次使用 DeepSeek V3.2</span>
                      </label>
                      <Select
                        placeholder="默认 DeepSeek V3.2"
                        style={{ width: 200 }}
                        value={selectedModel}
                        onChange={setSelectedModel}
                        allowClear
                      >
                        {availableModels.map(m => (
                          <Select.Option key={m} value={m}>
                            {m === 'deepseek-v3.2' ? 'DeepSeek V3.2（推荐）' : 
                             m === 'qwen3-coder-next' ? 'Qwen3 Coder（备用）' :
                             m === 'deepseek-v3.1' ? 'DeepSeek V3.1' :
                             m === 'qwen3.5-plus' ? 'Qwen3.5 Plus' : m}
                          </Select.Option>
                        ))}
                      </Select>
                    </div>
                    
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
                        style={{ marginTop: '22px' }}
                      >
                        预览示例
                      </Button>
                    )}
                  </div>
                  
                  {/* 提示文字 */}
                  <div className="text-xs text-gray-400 space-y-1">
                    <p>• 视频风格模板：选择后生成的脚本会按模板风格渲染，不选则使用默认风格</p>
                    <p>• AI 模型：推荐首次使用 DeepSeek V3.2，出错时自动切换到 Qwen3 Coder</p>
                    {selectedTemplateId && templates.find(t => t.id === selectedTemplateId)?.description && (
                      <p className="text-blue-500">• {templates.find(t => t.id === selectedTemplateId)?.description}</p>
                    )}
                  </div>
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
                  {generatedCode && (
                    <Button 
                      type="default"
                      icon={<CloudUploadOutlined />}
                      onClick={() => setActiveTab('video')}
                      size="large"
                      className="text-green-600 border-green-600 hover:bg-green-50"
                    >
                      前往渲染
                    </Button>
                  )}
                </div>

                {generatedCode && (
                  <div className="text-green-600 text-sm">
                    ✓ 脚本生成完成，点击"前往渲染"开始制作视频
                  </div>
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

                {/* 终端输出 - 仅管理员可见 */}
                {(showTerminal || terminalLog) && user?.is_admin && (
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
                    <p className="text-red-600 mb-3">渲染失败，建议返回脚本生成页面，更换 AI 模型重新生成脚本后再试。</p>
                    <Button type="primary" onClick={() => setActiveTab('code')}>
                      返回脚本生成
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
                  
                  {generatingVideo && (
                    <Button 
                      danger
                      onClick={handleCancelRender}
                      size="large"
                    >
                      取消渲染
                    </Button>
                  )}

                  {project?.video_url && (
                    <Button 
                      type="primary"
                      icon={<DownloadOutlined />}
                      onClick={handleDownloadVideo}
                      loading={downloadingVideo}
                      disabled={downloadingVideo}
                      size="large"
                      className="btn-gradient"
                    >
                      {downloadingVideo ? '下载中...' : '下载视频'}
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
