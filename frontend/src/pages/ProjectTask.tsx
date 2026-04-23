import { useEffect, useState, useRef } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { Card, Progress, Button, Space, message, Spin, Tabs, Select } from 'antd'
import { DownloadOutlined, PlayCircleOutlined, PlaySquareOutlined, CloudUploadOutlined } from '@ant-design/icons'
import { projectApi, Task, Project } from '@/services/project'
import { useAuthStore } from '@/stores/authStore'
import { motion } from 'framer-motion'
import StickmanProjectTask from './StickmanProjectTask'
import TemplateShowcase from '@/components/TemplateShowcase'
import { resolveBackendUrl } from '@/services/api'
import { resolveBackendUrl } from '@/services/api'

const statusMap: Record<string, { text: string; color: string }> = {
  not_started: { text: '未开始', color: '#8c8c8c' },
  pending: { text: '等待中', color: '#faad14' },
  processing: { text: '处理中', color: '#0066FF' },
  code_generated: { text: '准备就绪', color: '#00CCFF' },
  completed: { text: '已完成', color: '#52c41a' },
  failed: { text: '失败', color: '#ff4d4f' },
  cancelled: { text: '已取消', color: '#8c8c8c' },
}

function isMathProjectCategory(category?: string | null) {
  if (!category) return false
  const raw = String(category).toLowerCase()
  return raw === 'math' || raw.includes('数学') || raw.includes('公式') || raw.includes('定理') || raw.includes('几何')
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
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)
  const [currentRenderTaskId, setCurrentRenderTaskId] = useState<number | null>(null)
  const terminalRef = useRef<HTMLDivElement>(null)
  const codePollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const renderPollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const renderStatus = task?.status || (generatingVideo ? 'processing' : project?.video_url ? 'completed' : 'not_started')
  const hasRenderedVideo = Boolean(project?.video_url || task?.status === 'completed')

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

  const fetchAvailableModels = async () => {
    try {
      const token = useAuthStore.getState().token
      const response = await fetch(resolveBackendUrl('/api/tasks/available-models'), {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      if (response.ok) {
        const data = await response.json()
        setAvailableModels(data.models || [])
        if (data.default_code_model && !selectedModel) {
          setSelectedModel(data.default_code_model)
        }
      } else {
        console.error('获取模型列表失败:', response.status)
      }
    } catch (error) {
      console.error('获取模型列表失败:', error)
    }
  }

  useEffect(() => {
    if (id) {
      fetchProject()
      fetchAvailableModels()
    }
  }, [id])

  useEffect(() => {
    if (project) {
      fetchTask()
    }
  }, [project])

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null

    const pollLatestCodeTask = async () => {
      if (!id) return
      try {
        const { data } = await projectApi.getLatestCodeTask(Number(id))
        if (data?.task_id && data.status && ['pending', 'processing'].includes(data.status)) {
          setGeneratingCode(true)
          setCodeProgress(data.progress || 0)
          setCodeMessage(data.message || '后台生成中...')

          timer = setInterval(async () => {
            try {
              const { data: taskData } = await projectApi.getBackgroundTask(data.task_id as number)
              setCodeProgress(taskData.progress || 0)
              setCodeMessage(taskData.message || '后台生成中...')

              if (taskData.status === 'completed') {
                setGeneratingCode(false)
                setCodeProgress(100)
                setCodeMessage('生成完成！')
                await fetchProject()
                clearInterval(timer!)
              } else if (taskData.status === 'failed' || taskData.status === 'cancelled') {
                setGeneratingCode(false)
                message.error(taskData.error || '生成失败')
                clearInterval(timer!)
              }
            } catch (e) {
              clearInterval(timer!)
            }
          }, 3000)
        }
      } catch (e) {}
    }

    pollLatestCodeTask()

    return () => {
      if (timer) clearInterval(timer)
    }
  }, [id])

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null

    const pollLatestRenderTask = async () => {
      if (!id) return
      try {
        const { data } = await projectApi.getLatestRenderTask(Number(id))
        if (data?.task_id && data.status && ['pending', 'processing'].includes(data.status)) {
          setCurrentRenderTaskId(data.task_id)
          setGeneratingVideo(true)
          setVideoProgress(data.progress || 0)
          setVideoMessage(data.message || '后台渲染中...')

          timer = setInterval(async () => {
            try {
              const { data: taskData } = await projectApi.getBackgroundTask(data.task_id as number)
              setTask(prev => prev ? { ...prev, ...taskData } as Task : taskData as unknown as Task)
              setVideoProgress(taskData.progress || 0)
              setVideoMessage(taskData.message || '后台渲染中...')
              if (taskData.log) {
                setTerminalLog(taskData.log)
              }

              if (taskData.status === 'completed') {
                setGeneratingVideo(false)
                setVideoProgress(100)
                setVideoMessage('渲染完成！')
                setCurrentRenderTaskId(null)
                await fetchProject()
                await fetchTask()
                clearInterval(timer!)
              } else if (taskData.status === 'failed' || taskData.status === 'cancelled') {
                setGeneratingVideo(false)
                setRenderError(taskData.error || null)
                setCurrentRenderTaskId(null)
                clearInterval(timer!)
              }
            } catch (e) {
              clearInterval(timer!)
            }
          }, 3000)
        }
      } catch (e) {}
    }

    pollLatestRenderTask()

    return () => {
      if (timer) clearInterval(timer)
    }
  }, [id])

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
    setCodeMessage('正在提交后台任务...')
    setGeneratedCode('')

    try {
      const { data } = await projectApi.generateCodeAsync(Number(id), selectedTemplateId || undefined)
      const taskId = data.task_id
      message.success('已开始后台生成，可关闭页面')

      if (codePollingRef.current) clearInterval(codePollingRef.current)

      const pollTimer = setInterval(async () => {
        try {
          const { data: taskData } = await projectApi.getBackgroundTask(taskId)
          setCodeProgress(taskData.progress || 0)
          setCodeMessage(taskData.message || '后台生成中...')

          if (taskData.status === 'completed') {
            clearInterval(pollTimer)
            setGeneratingCode(false)
            setCodeProgress(100)
            setCodeMessage('生成完成！')
            await fetchProject()
            message.success('生成完成！')
          } else if (taskData.status === 'failed' || taskData.status === 'cancelled') {
            clearInterval(pollTimer)
            setGeneratingCode(false)
            message.error(taskData.error || '生成失败')
          }
        } catch (error: any) {
          clearInterval(pollTimer)
          setGeneratingCode(false)
          message.error(error.message || '获取任务进度失败')
        }
      }, 3000)
      codePollingRef.current = pollTimer
    } catch (error: any) {
      console.error('生成失败:', error)
      message.error(error.message || '生成失败')
      setGeneratingCode(false)
    }
  }

  const handleGenerateVideo = async () => {
    if (!generatedCode) {
      message.warning('请先生成内容')
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
    setVideoMessage('正在提交后台渲染任务...')
    setTerminalLog('')
    setShowTerminal(true)
    setRenderError(null)

    try {
      const { data } = await projectApi.renderVideoAsync(Number(id))
      setCurrentRenderTaskId(data.task_id)
      setTerminalLog(prev => prev + `任务已提交 (ID: ${data.task_id})\n后台运行中，可关闭浏览器...\n`)
      message.success(data.message)

      if (renderPollingRef.current) clearInterval(renderPollingRef.current)

      const pollTimer = setInterval(async () => {
        try {
          const { data: taskData } = await projectApi.getBackgroundTask(data.task_id)
          setTask(prev => prev ? { ...prev, ...taskData } as Task : taskData as unknown as Task)
          setVideoProgress(taskData.progress || 0)
          setVideoMessage(taskData.message || '后台渲染中...')
          if (taskData.log) {
            setTerminalLog(taskData.log)
          }

          if (taskData.status === 'completed') {
            clearInterval(pollTimer)
            renderPollingRef.current = null
            setGeneratingVideo(false)
            setCurrentRenderTaskId(null)
            setVideoProgress(100)
            setVideoMessage('渲染完成！')
            await fetchProject()
            await fetchTask()
            message.success('视频渲染完成！')
          } else if (taskData.status === 'failed' || taskData.status === 'cancelled') {
            clearInterval(pollTimer)
            renderPollingRef.current = null
            setGeneratingVideo(false)
            setCurrentRenderTaskId(null)
            setRenderError(taskData.error || '渲染失败')
            if (taskData.log) {
              setTerminalLog(taskData.log)
            }
            message.error(taskData.error || '渲染失败')
          }
        } catch (error: any) {
          clearInterval(pollTimer)
          renderPollingRef.current = null
          setGeneratingVideo(false)
          setCurrentRenderTaskId(null)
          message.error(error.message || '获取渲染进度失败')
        }
      }, 3000)

      renderPollingRef.current = pollTimer
    } catch (error: any) {
      const errorMsg = error.message || '未知错误'
      message.error('渲染失败: ' + errorMsg)
      setRenderError(errorMsg)
      setTerminalLog(prev => prev + `\n❌ 渲染失败: ${errorMsg}\n`)
      setVideoProgress(0)
    } finally {
      await fetchProject()
    }
  }

  const handleCancelRender = async () => {
    if (!currentRenderTaskId) return
    try {
      await projectApi.cancelTask(currentRenderTaskId)
      setGeneratingVideo(false)
      setCurrentRenderTaskId(null)
      setTerminalLog(prev => prev + '\n⚠️ 用户取消渲染\n')
      message.warning('渲染任务已取消')
      if (renderPollingRef.current) {
        clearInterval(renderPollingRef.current)
        renderPollingRef.current = null
      }
      await fetchTask()
    } catch (error: any) {
      message.error(error.message || '取消失败')
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
            <Tabs.TabPane tab={<span><PlaySquareOutlined /> 内容生成</span>} key="code">
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

                <div className="mb-4">
                  <label className="block text-sm text-gray-500 mb-2">
                    选择模板风格
                    {project?.category && (
                      <span className="ml-2 text-xs text-blue-500">
                        ({project.category === 'math' ? '数学可视化' : '思维可视化'}模板)
                      </span>
                    )}
                  </label>
                  <TemplateShowcase
                    value={selectedTemplateId}
                    onChange={setSelectedTemplateId}
                    category={isMathProjectCategory(project?.category) ? 'math' : undefined}
                  />

                  <div className="flex items-center gap-3 mt-3">
                    <div>
                      <label className="block text-sm text-gray-500 mb-1">
                        AI 模型
                        <span className="text-xs text-green-500 ml-2">推荐 DeepSeek V3.2</span>
                      </label>
                      <Select
                        placeholder="默认 DeepSeek V3.2"
                        style={{ width: 220 }}
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
                  </div>
                </div>

                {/* 生成内容按钮 */}
                <div className="flex gap-3">
                  <Button
                    type="primary"
                    onClick={handleGenerateCode}
                    loading={generatingCode}
                    size="large"
                    className="btn-gradient"
                  >
                    {generatedCode ? '重新生成' : '开始生成'}
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
                    ✓ 生成完成，点击"前往渲染"开始制作视频
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
                          backgroundColor: `${statusMap[renderStatus]?.color}20`,
                          color: statusMap[renderStatus]?.color 
                        }}
                      >
                        {statusMap[renderStatus]?.text}
                      </span>
                    </div>
                    <Progress 
                      percent={task?.progress || videoProgress} 
                      status={task?.status === 'failed' || renderError ? 'exception' : hasRenderedVideo ? 'success' : 'active'}
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
                    <p className="text-red-600 mb-3">渲染失败，建议返回内容生成页面，更换 AI 模型重新生成后再试。</p>
                    <Button type="primary" onClick={() => setActiveTab('code')}>
                      返回内容生成
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
                    {hasRenderedVideo ? '重新渲染' : '开始渲染视频'}
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
                      src={resolveBackendUrl(project.video_url)}
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
    </>
  )
}
