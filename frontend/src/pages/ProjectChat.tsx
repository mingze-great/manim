import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Input, Button, message, Modal } from 'antd'
import { SendOutlined, PlayCircleOutlined, RobotOutlined, UserOutlined, ReloadOutlined } from '@ant-design/icons'
import { projectApi, Conversation, Project } from '@/services/project'

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
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [project, setProject] = useState<Project | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [aiThinking, setAiThinking] = useState(false)
  const [lastMsgCount, setLastMsgCount] = useState(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchProject()
    fetchConversations()
  }, [id])

  useEffect(() => {
    if (conversations.length > lastMsgCount) {
      setLastMsgCount(conversations.length)
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [conversations, lastMsgCount])

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
      setConversations(data)
    } catch (error) {
      console.error('获取对话失败')
    }
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    const tempId = Date.now()
    setLoading(true)
    setAiThinking(true)
    
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
    
    try {
      // 发送用户消息（立即返回）
      await projectApi.sendMessage(Number(id), userMessage)
      
      // 轮询获取AI响应
      let pollCount = 0
      const maxPolls = 150 // 最多轮询150次（5分钟）
      
      const pollForResponse = async () => {
        if (pollCount >= maxPolls) {
          setAiThinking(false)
          message.error('AI响应超时，请重试')
          return
        }
        
        pollCount++
        try {
          const { data } = await projectApi.getPendingResponse(Number(id))
          
          if (data.status === 'completed' && data.response) {
            // 添加 AI 回复
            setConversations(prev => [...prev, {
              ...data.response,
              id: data.response.id || Date.now() + 1,
              role: 'assistant' as const
            }])
            await fetchProject()
            setAiThinking(false)
            
            // 滚动到底部
            setTimeout(() => {
              messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
            }, 100)
            
            const shouldGenerate = ['满意', '可以', '好了', '没问题', 'ok', 'OK', '好的', '可以了'].some(k => userMessage.includes(k))
            if (shouldGenerate) {
              Modal.confirm({
                title: '内容确认',
                content: '你已确认内容满意，现在开始生成代码和视频？',
                okText: '开始生成',
                cancelText: '继续对话',
                onOk: () => navigate(`/project/${id}/task?autoGenerate=true`)
              })
            }
          } else if (data.status === 'error') {
            setAiThinking(false)
            message.error(data.error || 'AI响应失败')
          } else {
            // 继续轮询
            setTimeout(pollForResponse, 2000)
          }
        } catch (error) {
          // 网络错误，继续重试
          setTimeout(pollForResponse, 3000)
        }
      }
      
      // 延迟一下开始轮询，确保用户消息已保存
      setTimeout(pollForResponse, 1000)
      
    } catch (error: any) {
      // 移除用户消息
      setConversations(prev => prev.filter(c => c.id !== tempId))
      setAiThinking(false)
      message.error(error.response?.data?.detail || '发送失败')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateCode = () => {
    navigate(`/project/${id}/task`)
  }

  const handleGenerateVideo = () => {
    navigate(`/project/${id}/task`)
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
        <Button icon={<ReloadOutlined />} size="small" onClick={fetchConversations} />
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
              <p>4. 开始生成视频</p>
            </div>
            <p className="text-xs mt-4 text-gray-500">例如：世界十大顶级思维：刻意练习、复利思维...</p>
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
          <div className="flex gap-2">
            <div className="w-8 h-8 rounded-full bg-emerald-500 text-white flex items-center justify-center">
              <RobotOutlined />
            </div>
            <div className="bg-gray-100 dark:bg-gray-700 rounded-lg p-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 操作按钮 */}
      <div className="px-3 py-2 border-t border-gray-200 dark:border-gray-700">
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
    </div>
  )
}
