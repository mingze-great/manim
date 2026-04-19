import { useEffect, useState, useRef, useCallback } from 'react'
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
  
  // WebSocket 和异步任务相关
  const [currentTaskId, setCurrentTaskId] = useState<number | null>(null)
  const [celeryStatus, setCeleryStatus] = useState<{ redis_connected: boolean; celery_active: boolean } | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  
  const terminalRef = useRef<HTMLDivElement>(null)

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

  // 检查 Celery 状态
  const checkCeleryStatus = async () => {
    try {
      const { data } = await projectApi.getCeleryStatus()
      setCeleryStatus(data)
    } catch (error) {
      console.error('检查 Celery 状态失败:', error)
    }
  }

  // WebSocket 连接
  const connectWebSocket = useCallback((taskId: number) => {
    if (wsRef.current) {
      wsRef.current.close()
    }
    
    const wsUrl = projectApi.connectTaskWebSocket(taskId)
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    
    ws.onopen = () => {
      console.log('WebSocket connected')
      // 发送心跳
      const heartbeat = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, 30000)
      ws.addEventListener('close', () => clearInterval(heartbeat))
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'pong') return
        
        // 更新进度
        if (data.progress !== undefined) {
          setCodeProgress(data.progress)
          setVideoProgress(data.progress)
        }
        if (data.status) {
          if (data.status === 'completed') {
            setGeneratingCode(false)
            setGeneratingVideo(false)
            message.success('任务完成！')
            fetchProject()
          } else if (data.status === 'failed') {
            setGeneratingCode(false)
            setGeneratingVideo(false)
            message.error(data.error_message || '任务失败')
          }
        }
        if (data.log) {
          setTerminalLog(prev => prev + data.log)
        }
      } catch (e) {}
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    ws.onclose = () => {
      console.log('WebSocket closed')
      wsRef.current = null
    }
  }, [fetchProject])

  // 轮询任务状态（备用方案）
  const startPolling = useCallback((taskId: number) => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
    }
    
    pollingRef.current = setInterval(async () => {
      try {
        const { data } = await projectApi.getAsyncTaskStatus(taskId)
        setCodeProgress(data.progress)
        setVideoProgress(data.progress)
        
        if (data.status === 'completed') {
          setGeneratingCode(false)
          setGeneratingVideo(false)
          message.success('任务完成！')
          if (pollingRef.current) clearInterval(pollingRef.current)
          fetchProject()
        } else if (data.status === 'failed') {
          setGeneratingCode(false)
          setGeneratingVideo(false)
          message.error(data.error_message || '任务失败')
          if (pollingRef.current) clearInterval(pollingRef.current)
        }
      } catch (error) {
        console.error('轮询任务状态失败:', error)
      }
    }, 2000)
  }, [fetchProject])

  // 清理 WebSocket 和轮询
  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close()
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [])

  // 恢复进行中的任务
  useEffect(() => {
    const recoverTasks = async () => {
      try {
        const { data } = await projectApi.getInProgressTasks()
        if (data.count > 0) {
          const projectTask = data.tasks.find(t => t.project_id === Number(id))
          if (projectTask) {
            setCurrentTaskId(projectTask.task_id)
            connectWebSocket(projectTask.task_id)
            startPolling(projectTask.task_id)
            if (projectTask.task_type === 'code_generation') {
              setGeneratingCode(true)
            } else {
              setGeneratingVideo(true)
            }
          }
        }
      } catch (error) {
        console.error('恢复任务失败:', error)
      }
    }
    
    if (id) {
      recoverTasks()
      checkCeleryStatus()
    }
  }, [id, connectWebSocket, startPolling])

  const handleGenerateCode = async () => {
    // 检查 Celery 状态
    if (celeryStatus && (!celeryStatus.redis_connected || !celeryStatus.celery_active)) {
      message.warning('后台服务暂时不可用，请稍后再试')
      return
    }
    
    setGeneratingCode(true)
    setCodeProgress(0)
    setCodeMessage('正在提交任务...')
    setGeneratedCode('')

    try {
      // 使用异步 API
      const { data } = await projectApi.generateCodeAsyncV2(Number(id), selectedTemplateId || undefined, selectedModel || undefined)
      
      setCurrentTaskId(data.task_id)
      setCodeMessage('任务已提交，后台运行中...')
      
      // 连接 WebSocket
      connectWebSocket(data.task_id)
      
      // 同时启动轮询作为备用
      startPolling(data.task_id)
      
      message.success(data.message)
    } catch (error: any) {
      console.error('提交任务失败:', error)
      message.error(error.response?.data?.detail || error.message || '提交失败')
      setGeneratingCode(false)
    }
  }

  const handleGenerateVideo = async () => {
    if (!generatedCode) {
      message.warning('请先生成脚本')
      return
    }
    
    // 检查 Celery 状态
    if (celeryStatus && (!celeryStatus.redis_connected || !celeryStatus.celery_active)) {
      message.warning('后台服务暂时不可用，请稍后再试')
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
    setVideoProgress(0)
    setVideoMessage('正在提交渲染任务...')
    setShowTerminal(true)
    setRenderError(null)
    setTerminalLog('⏱️ 提交后台渲染任务...\n')
    
    try {
      // 使用异步渲染 API
      const { data } = await projectApi.renderVideoAsync(Number(id))
      
      setCurrentTaskId(data.task_id)
      setTerminalLog(prev => prev + `✅ 任务已提交 (ID: ${data.task_id})\n`)
      setTerminalLog(prev => prev + '🔄 后台运行中，可关闭浏览器...\n')
      
      // 连接 WebSocket
      connectWebSocket(data.task_id)
      
      // 同时启动轮询作为备用
      startPolling(data.task_id)
      
      message.success(data.message)
    } catch (error: any) {
      console.error('提交渲染任务失败:', error)
      message.error(error.response?.data?.detail || error.message || '提交失败')
      setGeneratingVideo(false)
      setTerminalLog(prev => prev + `\n❌ 提交失败: ${error.message}\n`)
    }
  }

  // 取消任务
  const handleCancelTask = async () => {
    if (!currentTaskId) return
    
    try {
      await projectApi.cancelTask(currentTaskId)
      message.success('任务已取消')
      setGeneratingCode(false)
      setGeneratingVideo(false)
      setTerminalLog(prev => prev + '\n⚠️ 用户取消任务\n')
      
      // 关闭 WebSocket 和轮询
      if (wsRef.current) wsRef.current.close()
      if (pollingRef.current) clearInterval(pollingRef.current)
      setCurrentTaskId(null)
    } catch (error: any) {
      message.error('取消失败: ' + (error.message || '未知错误'))
    }
  }

  const handleCancelRender = () => {
    handleCancelTask()
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
