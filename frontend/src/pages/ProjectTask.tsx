import { useEffect, useState, useRef } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { Card, Progress, Button, Space, message, Spin, Tabs, Collapse, Select } from 'antd'
import { DownloadOutlined, PlayCircleOutlined, CodeOutlined, CloudUploadOutlined, CopyOutlined, DownOutlined, UpOutlined } from '@ant-design/icons'
import { projectApi, Task, Project } from '@/services/project'
import { templateApi, Template } from '@/services/template'
import { adminApi } from '@/services/admin'
import { useAuthStore } from '@/stores/authStore'
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
  const { user } = useAuthStore()
  const isAdmin = user?.is_admin
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
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(1)
  const [availableModels, setAvailableModels] = useState<{ value: string; label: string }[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('deepseek-v3.2')
  const [showFullCode, setShowFullCode] = useState(false)
  const [fixingCode, setFixingCode] = useState(false)
  const [fixProgress, setFixProgress] = useState(0)
  const [fixMessage, setFixMessage] = useState('')
  const [fixPreviewLines, setFixPreviewLines] = useState<string[]>([])
  const [fixFocusLine, setFixFocusLine] = useState<number | null>(null)
  const [fixSuccess, setFixSuccess] = useState(false)
  const [fixDescription, setFixDescription] = useState('')
  const codeRef = useRef<HTMLPreElement>(null)
  const terminalRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

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
      const { data } = await adminApi.getAvailableModels()
      setAvailableModels(data.models)
    } catch (error) {
      console.error('获取模型列表失败:', error)
    }
  }

  useEffect(() => {
    fetchProject()
    fetchTemplates()
    fetchAvailableModels()
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
    setCodeMessage('正在创建后台任务...')
    setGeneratedCode('')
    setActiveTab('code')

    try {
      const { data } = await projectApi.generateCodeAsync(
        Number(id),
        selectedTemplateId || undefined,
        selectedModel || undefined
      )
      
      setCodeMessage('任务已创建，正在后台处理...')
      
      startPolling(data.task_id)
    } catch (error: any) {
      console.error('创建任务失败:', error)
      message.error(error.response?.data?.detail || error.message || '创建任务失败')
      setGeneratingCode(false)
    }
  }

  const startPolling = (taskId: number) => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
    }
    
    pollingRef.current = setInterval(async () => {
      try {
        const { data } = await projectApi.getBackgroundTask(taskId)
        
        setCodeProgress(data.progress || 0)
        setCodeMessage(data.message || '处理中...')
        
        if (data.status === 'completed') {
          if (pollingRef.current) {
            clearInterval(pollingRef.current)
          }
          setGeneratingCode(false)
          if (data.code) {
            setGeneratedCode(data.code)
          }
          message.success('代码生成完成！')
          await fetchProject()
        } else if (data.status === 'failed') {
          if (pollingRef.current) {
            clearInterval(pollingRef.current)
          }
          setGeneratingCode(false)
          message.error(data.error || '生成失败')
        }
      } catch (error: any) {
        console.error('轮询任务状态失败:', error)
      }
    }, 2000)
  }

  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [])

  const checkExistingTask = async () => {
    try {
      const { data } = await projectApi.getLatestCodeTask(Number(id))
      if (data.task_id && (data.status === 'pending' || data.status === 'processing')) {
        setGeneratingCode(true)
        setCodeProgress(data.progress || 0)
        setCodeMessage(data.message || '恢复任务中...')
        startPolling(data.task_id)
      }
    } catch (error) {
      console.error('检查任务状态失败:', error)
    }
  }

  useEffect(() => {
    if (project) {
      checkExistingTask()
    }
  }, [project])

  const handleCopyCode = () => {
    if (!generatedCode) return
    navigator.clipboard.writeText(generatedCode)
    message.success('代码已复制到剪贴板')
  }

  const handleGenerateVideo = async () => {
    if (!generatedCode) {
      message.warning('请先生成代码')
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

const handleDownloadVideo = () => {
    const videoUrl = task?.video_url || project?.video_url
    if (videoUrl) {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
      const fullUrl = videoUrl.startsWith('http') ? videoUrl : `${API_BASE}${videoUrl}`
      
      const a = document.createElement('a')
      a.href = fullUrl
      a.download = `video_${id}_${Date.now()}.mp4`
      a.target = '_blank'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
message.success('视频下载已开始')
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

  const handleAutoFix = async () => {
    if (!generatedCode || !renderError) return
    
    setFixingCode(true)
    setFixProgress(0)
    setFixMessage('准备修复...')
    setFixPreviewLines([])
    setFixSuccess(false)
    setFixDescription('')
    
    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
      const token = useAuthStore.getState().token
      const errorLog = terminalLog ? terminalLog.slice(-2000) : renderError
      
      const response = await fetch(`${API_BASE}${projectApi.fixCodeStream(Number(id))}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          error_message: errorLog,
          current_code: generatedCode
        })
      })
      
      if (!response.ok) {
        throw new Error('请求失败')
      }
      
      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('无法读取响应')
      }
      
      const decoder = new TextDecoder()
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.type === 'progress') {
                setFixProgress(data.progress)
                setFixMessage(data.message)
              } else if (data.type === 'code_preview') {
                setFixPreviewLines(data.lines || [])
                setFixFocusLine(data.focus_line ?? null)
              } else if (data.type === 'done') {
                setFixProgress(100)
                setFixMessage('修复完成')
                if (data.fixed_code) {
                  setGeneratedCode(data.fixed_code)
                }
                setFixSuccess(true)
                setFixDescription(data.fix_description || '代码已修复')
                setRenderError(null)
                setTerminalLog('')
                message.success('修复成功！')
              } else if (data.type === 'error') {
                message.error(data.message || '修复失败')
              }
            } catch (e) {
              console.error('Parse error:', e)
            }
          }
        }
      }
    } catch (error: any) {
      message.error(error.message || '修复失败')
    } finally {
      setFixingCode(false)
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

                {/* 模板选择 */}
                <div className="mb-4">
                  <label className="block text-sm text-gray-500 mb-2">选择代码模板</label>
                  <Select
                    style={{ width: '100%', maxWidth: 300 }}
                    placeholder="默认模板"
                    allowClear
                    value={selectedTemplateId}
                    onChange={setSelectedTemplateId}
                    options={templates.map(t => ({
                      label: t.name,
                      value: t.id
                    }))}
                  />
                  <p className="text-xs text-gray-400 mt-1">视频风格模板。高定版效果更好但可能出错，若首次出错建议换其他模板</p>
                </div>

                {/* 模型选择 */}
                {availableModels.length > 0 && (
                  <div className="mb-4">
                    <label className="block text-sm text-gray-500 mb-2">选择生成模型</label>
                    <Select
                      style={{ width: '100%', maxWidth: 300 }}
                      placeholder="默认模型"
                      allowClear
                      value={selectedModel}
                      onChange={setSelectedModel}
                      options={availableModels}
                    />
                    <p className="text-xs text-gray-400 mt-1">默认：deepseek-v3.2。若出错可切换 glm-5 重试，仍失败请新建项目或联系我</p>
</div>
                )}

                {/* 修复进度显示 */}
                {fixingCode && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-gradient-to-r from-orange-50 to-yellow-50 dark:from-orange-900/20 dark:to-yellow-900/20 p-4 rounded-xl border border-orange-100 dark:border-orange-800 mb-4"
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <Spin />
                      <span className="text-orange-600 dark:text-orange-400 font-medium">🔧 正在修复代码...</span>
                    </div>
                    <Progress percent={fixProgress} strokeColor="#FF8C00" size="small" />
                    <p className="text-sm text-gray-500 mt-2">{fixMessage}</p>
                    
                    {/* 代码预览窗口 */}
                    {fixPreviewLines.length > 0 && (
                      <div className="mt-3 bg-gray-900 rounded-lg p-3 overflow-x-auto">
                        <pre className="text-xs text-gray-300">
                          {fixPreviewLines.map((line, i) => (
                            <div 
                              key={i} 
                              className={`px-2 py-0.5 ${i === fixFocusLine ? 'bg-orange-500/30 border-l-2 border-orange-500' : ''}`}
                            >
                              <span className="text-gray-500 mr-3">{String(i + 1).padStart(2, ' ')}</span>
                              {line}
                            </div>
                          ))}
                        </pre>
                      </div>
                    )}
                  </motion.div>
                )}

                {/* 修复成功提示 */}
                {fixSuccess && !fixingCode && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-green-50 dark:bg-green-900/20 border border-green-200 rounded-lg p-4 mb-4"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-green-600 text-lg">✅</span>
                      <span className="text-green-700 dark:text-green-400 font-medium">修复成功！</span>
                    </div>
                    <p className="text-sm text-green-600 dark:text-green-400 mt-1">{fixDescription}</p>
                    <p className="text-xs text-gray-500 mt-2">请点击「渲染视频」按钮重新渲染</p>
                  </motion.div>
                )}

                {/* 代码显示 */}
                {generatedCode && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 rounded-lg p-3 mb-4">
                      <p className="text-sm text-green-700">✅ 代码生成完成！请点击上方「渲染视频」按钮开始渲染</p>
                    </div>
                    <Collapse defaultActiveKey={['code']}>
                      <Panel 
                        header={
                          <div className="flex items-center gap-2">
                            <CodeOutlined className="text-[#0066FF]" />
                            <span>生成的 Manim 代码 ({generatedCode.split('\n').length} 行)</span>
                          </div>
                        } 
                        key="code"
                      >
                        <div className="code-block relative">
                          {isAdmin && (
                            <div className="flex justify-end gap-2 mb-2">
                              <Button 
                                size="small" 
                                icon={<CopyOutlined />}
                                onClick={handleCopyCode}
                              >
                                复制代码
                              </Button>
                              {generatedCode.split('\n').length > 10 && (
                                <Button 
                                  size="small" 
                                  icon={showFullCode ? <UpOutlined /> : <DownOutlined />}
                                  onClick={() => setShowFullCode(!showFullCode)}
                                >
                                  {showFullCode ? '收起' : '展开全部'}
                                </Button>
                              )}
                            </div>
                          )}
                          <pre 
                            ref={codeRef}
                            className="text-sm max-h-96 overflow-y-auto"
                          >
                            {isAdmin && showFullCode ? generatedCode : generatedCode.split('\n').slice(0, 10).join('\n')}
                            {(!isAdmin || !showFullCode) && generatedCode.split('\n').length > 10 && '\n...'}
                          </pre>
                          {(!isAdmin || !showFullCode) && generatedCode.split('\n').length > 10 && (
                            <div className="text-xs text-gray-400 mt-2 text-center">
                              共 {generatedCode.split('\n').length} 行代码
                            </div>
                          )}
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
                    {(project?.render_fail_count || 0) >= 3 ? (
                      <>
                        <p className="text-red-600 font-semibold mb-2">渲染已失败 {project?.render_fail_count} 次，建议：</p>
                        <ul className="text-sm text-gray-600 mb-3 list-disc pl-4">
                          <li>重新创建一个项目（推荐）</li>
                          <li>及时向我反馈，我会根据问题修复</li>
                        </ul>
                        <p className="text-orange-500 text-xs mb-3">⚠️ 请不要一直重试，会导致 Token 耗光</p>
                      </>
                    ) : (
                      <p className="text-red-600 mb-3">渲染失败，您可以选择：</p>
                    )}
                    <div className="flex gap-3 flex-wrap">
                      {(project?.render_fail_count || 0) < 3 && (
                        <>
                          <Button type="primary" onClick={handleAutoFix} loading={fixingCode}>
                            自动修复
                          </Button>
                          <Button onClick={handleBackToEdit}>
                            返回对话修复
                          </Button>
                        </>
                      )}
                      {(project?.render_fail_count || 0) >= 3 && (
                        <Button type="primary" onClick={() => navigate('/creator')}>
                          创建新项目
                        </Button>
                      )}
                    </div>
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
                      playsInline
                      webkit-playsinline="true"
                      x5-video-player-type="h5"
                      x5-video-player-fullscreen="true"
                      preload="metadata"
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
