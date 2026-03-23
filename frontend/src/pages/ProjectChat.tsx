import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { Input, Button, message, Modal, Spin, Card, Radio, Space, Alert } from 'antd'
import { SendOutlined, PlayCircleOutlined, RobotOutlined, UserOutlined, ReloadOutlined, CheckCircleOutlined, StopOutlined } from '@ant-design/icons'
import { projectApi, Conversation, Project } from '@/services/project'
import { templateApi, Template } from '@/services/template'
import { useAuthStore } from '@/stores/authStore'

const { TextArea } = Input

const statusBadgeMap: Record<string, { text: string; color: string }> = {
  draft: { text: '草稿', color: '#faad14' },
  chatting: { text: '对话中', color: '#1890ff' },
  chatting_completed: { text: '已确认', color: '#52c41a' },
  code_generated: { text: '代码就绪', color: '#722ed1' },
  rendering: { text: '渲染中', color: '#fa8c16' },
  completed: { text: '已完成', color: '#52c41a' },
  failed: { text: '失败', color: '#ff4d4f' },
}

export default function ProjectChat() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [project, setProject] = useState<Project | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [aiThinking, setAiThinking] = useState(false)
  const [lastMsgCount, setLastMsgCount] = useState(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const [templateModalOpen, setTemplateModalOpen] = useState(false)
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)
  const [loadingTemplates, setLoadingTemplates] = useState(false)
  const [lastAiCode, setLastAiCode] = useState<string | null>(null)
  const [showUseCodeButton, setShowUseCodeButton] = useState(false)
  const [errorFromRender, setErrorFromRender] = useState<string | null>(null)
  const [pendingCode, setPendingCode] = useState<string | null>(null)
  const [showCodeConfirm, setShowCodeConfirm] = useState(false)
  const [hasTemplate, setHasTemplate] = useState(false)

  useEffect(() => {
    fetchProject()
    fetchConversations()
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [id])

  useEffect(() => {
    if (conversations.length > lastMsgCount) {
      setLastMsgCount(conversations.length)
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [conversations, lastMsgCount])

  useEffect(() => {
    if (location.state?.errorLog && location.state?.fromRender) {
      const errorLog = location.state.errorLog as string
      setErrorFromRender(errorLog)
      setInput(`渲染遇到以下错误，请帮我修复代码：\n\`\`\`\n${errorLog.substring(0, 2000)}\n\`\`\``)
      window.history.replaceState({}, document.title)
    }
  }, [location.state])

  const fetchProject = async () => {
    try {
      const { data } = await projectApi.get(Number(id))
      setProject(data)
    } catch (error) {
      message.error('获取项目失败')
    }
  }

  const fetchConversations = async () => {
    try {
      const { data } = await projectApi.getConversations(Number(id))
      setConversations(data || [])
    } catch (error) {
      console.error('获取对话失败')
    }
  }

  const fetchTemplates = async () => {
    setLoadingTemplates(true)
    try {
      const { data } = await templateApi.list()
      const allTemplates = [...data.system_templates, ...data.user_templates]
      setTemplates(allTemplates)
    } catch (error) {
      message.error('获取模板失败')
    } finally {
      setLoadingTemplates(false)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    const isFixRequest = errorFromRender || userMessage.includes('修复') || userMessage.includes('错误')
    const tempId = Date.now()
    setLoading(true)
    setAiThinking(true)
    setErrorFromRender(null)
    
    const userMsg = {
      id: tempId,
      project_id: Number(id),
      role: 'user' as const,
      content: userMessage,
      created_at: new Date().toISOString()
    }
    setConversations(prev => [...prev, userMsg])
    setInput('')
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, 100)
    
    let aiContent = ''
    let aiTempId = tempId + 1
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    abortControllerRef.current = new AbortController()
    
    try {
      const token = useAuthStore.getState().token
      const streamUrl = projectApi.sendMessageStream(Number(id), userMessage)
      
      const response = await fetch(streamUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ content: userMessage }),
        signal: abortControllerRef.current.signal
      })
      
      if (!response.ok) {
        throw new Error('请求失败')
      }
      
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      
      if (!reader) {
        throw new Error('无法读取响应流')
      }
      
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
            if (data === '[DONE]') continue
            
            try {
              const parsed = JSON.parse(data)
              
              if (parsed.type === 'reasoning' || parsed.type === 'content') {
                aiContent += parsed.content
                setConversations(prev => {
                  const existing = prev.find(c => c.id === aiTempId)
                  if (existing) {
                    return prev.map(c => c.id === aiTempId ? { ...c, content: aiContent } : c)
                  } else {
                    return [...prev, {
                      id: aiTempId,
                      project_id: Number(id),
                      role: 'assistant' as const,
                      content: aiContent,
                      created_at: new Date().toISOString()
                    }]
                  }
                })
                setTimeout(() => {
                  messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
                }, 10)
              } else if (parsed.type === 'done') {
                await fetchProject()
                setAiThinking(false)
                
                if (parsed.code_updated && parsed.updated_code) {
                  setPendingCode(parsed.updated_code)
                  setHasTemplate(parsed.has_template || false)
                  setShowCodeConfirm(true)
                }
                
                const shouldGenerate = ['满意', '可以', '好了', '没问题', 'ok', 'OK', '好的', '可以了'].some(k => userMessage.includes(k))
                if (shouldGenerate && !isFixRequest && !parsed.code_updated) {
                  handleOpenTemplateModal()
                }
              } else if (parsed.type === 'error') {
                message.error(parsed.error || 'AI响应失败')
                setAiThinking(false)
              }
            } catch (e) {
              console.error('解析SSE数据失败:', e)
            }
          }
        }
      }
      
    } catch (error: any) {
      if (error.name === 'AbortError') {
        message.info('已中止生成')
        return
      }
      setConversations(prev => prev.filter(c => c.id !== tempId && c.id !== aiTempId))
      setAiThinking(false)
      message.error(error.message || '发送失败')
    } finally {
      setLoading(false)
    }
  }

  const handleOpenTemplateModal = () => {
    fetchTemplates()
    setTemplateModalOpen(true)
  }

  const handleConfirmTemplate = () => {
    setTemplateModalOpen(false)
    navigate(`/project/${id}/task${selectedTemplateId ? `?templateId=${selectedTemplateId}` : ''}`)
  }

  const handleGenerateCode = () => {
    navigate(`/project/${id}/task`)
  }

  const handleGenerateVideo = () => {
    navigate(`/project/${id}/task`)
  }

  const handleUseCode = async () => {
    if (!lastAiCode) return
    try {
      await projectApi.update(Number(id), { manim_code: lastAiCode, status: 'code_generated' })
      message.success('代码已保存，跳转到渲染页面')
      setShowUseCodeButton(false)
      setLastAiCode(null)
      fetchProject()
      setTimeout(() => navigate(`/project/${id}/task`), 500)
    } catch (error) {
      message.error('保存代码失败')
    }
  }

  const handleConfirmCode = async () => {
    if (!pendingCode) return
    try {
      await projectApi.update(Number(id), { manim_code: pendingCode, status: 'code_generated' })
      message.success('代码已保存')
      setShowCodeConfirm(false)
      setPendingCode(null)
      fetchProject()
    } catch (error) {
      message.error('保存代码失败')
    }
  }

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-800">
      {/* 头部 */}
      <div className="p-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">{project?.theme || '项目对话'}</h2>
          <span className="text-xs px-2 py-0.5 rounded" style={{ 
            backgroundColor: `${statusBadgeMap[project?.status || 'draft']?.color}20`,
            color: statusBadgeMap[project?.status || 'draft']?.color 
          }}>
            {statusBadgeMap[project?.status || 'draft']?.text}
          </span>
        </div>
        <Button icon={<ReloadOutlined />} size="small" onClick={() => { fetchProject(); fetchConversations(); }} />
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {conversations.length === 0 && (
          <div className="text-center text-gray-400 py-8 px-4">
            <RobotOutlined className="text-3xl mb-3 block" />
            <p className="text-sm mb-4">欢迎使用 AI 视频创作助手</p>
            <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-4 text-left text-xs">
              <p className="font-semibold mb-2">使用方法：</p>
              <p className="mb-1">1. 输入你想要的视频主题</p>
              <p className="mb-1">2. AI 会生成完整内容</p>
              <p className="mb-1">3. 满意后输入"满意"</p>
              <p>4. 选择模板生成视频</p>
            </div>
          </div>
        )}
        
        {conversations.map((conv) => (
          <div key={conv.id} className={`flex gap-2 ${conv.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
              conv.role === 'user' ? 'bg-indigo-500' : 'bg-emerald-500'
            } text-white text-sm`}>
              {conv.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
            </div>
            <div className={`max-w-[75%] rounded-lg p-2 text-sm ${
              conv.role === 'user' 
                ? 'bg-indigo-500 text-white' 
                : 'bg-gray-100 dark:bg-gray-700'
            }`}>
              <pre className="whitespace-pre-wrap text-inherit" style={{ fontFamily: 'inherit' }}>
                {conv.content}
              </pre>
            </div>
          </div>
        ))}

        {aiThinking && (
          <div className="flex gap-2 items-end">
            <div className="w-8 h-8 rounded-full bg-emerald-500 text-white flex items-center justify-center">
              <RobotOutlined />
            </div>
            <div className="bg-gray-100 dark:bg-gray-700 rounded-lg p-3 flex items-center gap-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <Button 
                size="small" 
                danger 
                icon={<StopOutlined />}
                onClick={() => {
                  if (abortControllerRef.current) {
                    abortControllerRef.current.abort()
                    setAiThinking(false)
                    setLoading(false)
                    message.info('已中止生成')
                  }
                }}
              >
                中止
              </Button>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 操作按钮 */}
      <div className="px-3 py-2 border-t border-gray-200 dark:border-gray-700">
        {errorFromRender && (
          <Alert
            type="warning"
            message="检测到渲染错误"
            description="错误信息已填充到输入框，可直接发送给AI修复代码"
            className="mb-3"
            closable
            onClose={() => setErrorFromRender(null)}
          />
        )}
        
        {showUseCodeButton && lastAiCode && (
          <div className="mb-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-green-600 font-medium">✅ AI生成了新代码</span>
              <div className="flex gap-2">
                <Button size="small" onClick={() => { setShowUseCodeButton(false); setLastAiCode(null); }}>
                  忽略
                </Button>
                <Button type="primary" size="small" icon={<CheckCircleOutlined />} onClick={handleUseCode}>
                  使用此代码
                </Button>
              </div>
            </div>
            <pre className="text-xs bg-gray-900 text-green-400 p-2 rounded overflow-auto max-h-32">
              {lastAiCode.split('\n').slice(0, 10).join('\n')}
              {lastAiCode.split('\n').length > 10 && '\n...'}
            </pre>
          </div>
        )}
        
        {project?.final_script && !project?.manim_code ? (
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={handleGenerateCode}
            block
            className="btn-gradient"
          >
            生成代码和视频
          </Button>
        ) : project?.manim_code ? (
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={handleGenerateVideo}
            block
            className="btn-gradient"
          >
            生成视频
          </Button>
        ) : (
          <p className="text-xs text-gray-400 text-center">
            输入"满意"确认内容，开始生成视频
          </p>
        )}
      </div>

      {/* 输入区域 */}
      <div className="p-3 border-t border-gray-200 dark:border-gray-700">
        <div className="text-xs text-gray-400 mb-2 text-center">
          ⚠️ 视频将在 3 小时后自动清除 | 对话内容将在 24 小时后清除
        </div>
        <div className="flex gap-2">
          <TextArea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onPressEnter={(e) => !e.shiftKey && handleSend()}
            placeholder="输入内容..."
            autoSize={{ minRows: 1, maxRows: 3 }}
            className="flex-1 text-sm"
          />
          <Button 
            type="primary" 
            icon={<SendOutlined />} 
            onClick={handleSend}
            loading={loading}
            className="btn-gradient"
          />
        </div>
      </div>

      {/* 代码确认弹窗 */}
      <Modal
        title={
          <div className="flex items-center gap-2">
            <CheckCircleOutlined className="text-green-500" />
            <span>AI 生成了新代码</span>
          </div>
        }
        open={showCodeConfirm}
        onCancel={() => { setShowCodeConfirm(false); setPendingCode(null); }}
        footer={null}
        width={700}
      >
        {hasTemplate && (
          <Alert
            type="warning"
            message="你之前选择了模板，使用新代码将覆盖模板风格"
            className="mb-3"
          />
        )}
        <div className="text-xs text-gray-500 mb-2">预览前10行：</div>
        <pre className="text-xs bg-gray-900 text-green-400 p-3 rounded-lg mb-4 overflow-auto max-h-48">
          {pendingCode?.split('\n').slice(0, 10).join('\n')}
          {pendingCode && pendingCode.split('\n').length > 10 && '\n...'}
        </pre>
        <div className="flex gap-2 justify-end">
          <Button onClick={() => { setShowCodeConfirm(false); setPendingCode(null); }}>
            忽略
          </Button>
          <Button type="primary" icon={<CheckCircleOutlined />} onClick={handleConfirmCode}>
            使用此代码并保存
          </Button>
        </div>
      </Modal>

      {/* 模板选择弹窗 */}
      <Modal
        title="选择模板（可选）"
        open={templateModalOpen}
        onCancel={() => setTemplateModalOpen(false)}
        footer={null}
        width={600}
      >
        <div className="mb-4">
          <p className="text-gray-500 text-sm mb-2">选择一个模板可以让AI生成更符合你需求的代码风格，也可以跳过直接生成。</p>
        </div>
        
        {loadingTemplates ? (
          <div className="flex justify-center py-8">
            <Spin />
          </div>
        ) : (
          <Radio.Group 
            value={selectedTemplateId} 
            onChange={(e) => setSelectedTemplateId(e.target.value)}
            className="w-full"
          >
            <Space direction="vertical" className="w-full" style={{ gap: 12 }}>
              {templates.map((template) => (
                <Card 
                  key={template.id}
                  size="small"
                  className={`cursor-pointer transition-all ${selectedTemplateId === template.id ? 'border-blue-500 bg-blue-50' : 'hover:border-gray-300'}`}
                  onClick={() => setSelectedTemplateId(template.id)}
                >
                  <div className="flex items-start gap-3">
                    <Radio value={template.id} />
                    <div className="flex-1">
                      <div className="font-medium flex items-center gap-2">
                        {template.name}
                        {template.is_system && <span className="text-xs bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded">系统</span>}
                      </div>
                      <div className="text-gray-500 text-sm mt-1">{template.description}</div>
                    </div>
                  </div>
                </Card>
              ))}
            </Space>
          </Radio.Group>
        )}
        
        <div className="flex justify-end gap-2 mt-4 pt-4 border-t">
          <Button onClick={() => navigate(`/project/${id}/task`)}>
            跳过，直接生成
          </Button>
          <Button type="primary" onClick={handleConfirmTemplate}>
            {selectedTemplateId ? '使用选中模板生成' : '直接生成代码'}
          </Button>
        </div>
      </Modal>
    </div>
  )
}
