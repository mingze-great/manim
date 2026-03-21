import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Input, Button, message, Modal } from 'antd'
import { SendOutlined, PlayCircleOutlined, RobotOutlined, UserOutlined, ReloadOutlined } from '@ant-design/icons'
import { projectApi, Conversation, Project } from '@/services/project'
import { templateApi, Template } from '@/services/template'
import { motion } from 'framer-motion'

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
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [aiThinking, setAiThinking] = useState(false)
  const [showTemplateModal, setShowTemplateModal] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchProject()
    fetchConversations()
    fetchTemplates()
  }, [id])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversations])

  const fetchProject = async () => {
    try {
      const { data } = await projectApi.get(Number(id))
      setProject(data)
      if (data.template_id && templates.length > 0) {
        const t = templates.find(t => t.id === data.template_id)
        if (t) setSelectedTemplate(t)
      }
    } catch (error) {
      message.error('获取项目失败')
    }
  }

  const fetchConversations = async () => {
    try {
      const { data } = await projectApi.getConversations(Number(id))
      setConversations(data)
    } catch (error) {
      message.error('获取对话失败')
    }
  }

  const fetchTemplates = async () => {
    try {
      const { data } = await templateApi.list()
      setTemplates([...data.system_templates, ...data.user_templates])
    } catch (error) {
      message.error('获取模板失败')
    }
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    setLoading(true)
    setAiThinking(true)
    try {
      await projectApi.sendMessage(Number(id), input)
      setInput('')
      await fetchConversations()
      await fetchProject()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '发送失败')
    } finally {
      setLoading(false)
      setAiThinking(false)
    }
  }

  const handleSelectTemplate = async () => {
    if (!selectedTemplate) {
      message.warning('请选择模板')
      return
    }
    try {
      await projectApi.update(Number(id), { template_id: selectedTemplate.id })
      setShowTemplateModal(false)
      message.success(`已选择模板: ${selectedTemplate.name}`)
      await fetchProject()
    } catch (error) {
      message.error('选择模板失败')
    }
  }

  const handleGenerateVideo = () => {
    if (!project?.manim_code) {
      message.warning('请先在对话中确认内容，AI会自动生成代码')
      return
    }
    navigate(`/project/${id}/task`)
  }

  const handleRegenerateCode = async () => {
    if (!project?.final_script) {
      message.warning('没有可重新生成的内容')
      return
    }
    try {
      await projectApi.regenerateCode(Number(id))
      message.success('代码已重新生成')
    } catch (error) {
      message.error('重新生成失败')
    }
  }

  const canGenerateVideo = project?.manim_code && project?.status !== 'draft'

  return (
    <div className="h-[calc(100vh-140px)] flex gap-4 p-4">
      {/* 聊天区域 */}
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className="flex-1 flex flex-col"
      >
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm flex-1 flex flex-col overflow-hidden">
          {/* 聊天头部 */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold">{project?.theme || '项目对话'}</h2>
            <p className="text-sm text-gray-500 mt-1">输入主题内容，AI将为你策划动画</p>
          </div>

          {/* 消息列表 */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {conversations.length === 0 && (
              <div className="text-center text-gray-400 py-12">
                <RobotOutlined className="text-4xl mb-4" />
                <p>开始输入你的主题内容吧</p>
                <p className="text-sm mt-2">例如：世界十大顶级思维：1.刻意练习 2.复利思维 3.终身学习...</p>
              </div>
            )}
            
            {conversations.map((conv) => (
              <motion.div
                key={conv.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex gap-3 ${conv.role === 'user' ? 'flex-row-reverse' : ''}`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  conv.role === 'user' ? 'bg-indigo-500' : 'bg-emerald-500'
                } text-white`}>
                  {conv.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                </div>
                <div className={`max-w-[70%] rounded-lg p-3 ${
                  conv.role === 'user' 
                    ? 'bg-indigo-500 text-white' 
                    : 'bg-gray-100 dark:bg-gray-700'
                }`}>
                  <pre className="whitespace-pre-wrap text-sm font-sans" style={{ fontFamily: 'inherit' }}>
                    {conv.content}
                  </pre>
                </div>
              </motion.div>
            ))}

            {aiThinking && (
              <div className="flex gap-3">
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

          {/* 输入区域 */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex gap-3">
              <TextArea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onPressEnter={(e) => !e.shiftKey && handleSend()}
                placeholder="输入主题内容，如：世界十大顶级思维，包括刻意练习、复利思维..."
                autoSize={{ minRows: 1, maxRows: 4 }}
                className="flex-1"
              />
              <Button 
                type="primary" 
                icon={<SendOutlined />} 
                onClick={handleSend}
                loading={loading}
                className="btn-gradient"
              >
                发送
              </Button>
            </div>
          </div>
        </div>
      </motion.div>

      {/* 侧边栏 */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        className="w-80 flex-shrink-0"
      >
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-4 space-y-4">
          <h3 className="font-bold">操作面板</h3>
          
          <div>
            <div className="text-gray-500 text-sm mb-2">当前模板</div>
            <Button block onClick={() => setShowTemplateModal(true)}>
              {selectedTemplate ? selectedTemplate.name : '选择模板'}
            </Button>
          </div>

          <div>
            <div className="text-gray-500 text-sm mb-2">状态</div>
            <span 
              className="inline-block px-2 py-1 rounded text-xs"
              style={{ 
                backgroundColor: `${statusBadgeMap[project?.status || 'draft']?.color}20`,
                color: statusBadgeMap[project?.status || 'draft']?.color 
              }}
            >
              {statusBadgeMap[project?.status || 'draft']?.text}
            </span>
          </div>

          {project?.manim_code && (
            <div>
              <Button 
                icon={<ReloadOutlined />} 
                onClick={handleRegenerateCode}
                block
              >
                重新生成代码
              </Button>
            </div>
          )}

          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleGenerateVideo}
              disabled={!canGenerateVideo}
              block
              size="large"
              className="btn-gradient"
            >
              生成视频
            </Button>
            {canGenerateVideo && (
              <p className="text-xs text-gray-500 text-center mt-2">
                点击使用最新代码生成视频
              </p>
            )}
          </div>

          {project?.final_script && (
            <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="text-gray-500 text-sm mb-2">内容摘要</div>
              <div className="bg-gray-50 dark:bg-gray-700/50 p-2 rounded text-xs max-h-32 overflow-y-auto">
                <pre className="whitespace-pre-wrap">{project.final_script.slice(0, 200)}...</pre>
              </div>
            </div>
          )}
        </div>
      </motion.div>

      {/* 模板选择弹窗 */}
      <Modal
        title="选择代码模板"
        open={showTemplateModal}
        onOk={handleSelectTemplate}
        onCancel={() => setShowTemplateModal(false)}
        okText="确认选择"
      >
        <div className="py-4">
          <p className="text-gray-500 mb-4">
            选择一个模板，AI将按照该模板的风格生成动画代码
          </p>
          <div className="space-y-2">
            {templates.map((template) => (
              <div
                key={template.id}
                className={`p-3 border-2 rounded-lg cursor-pointer transition-all ${
                  selectedTemplate?.id === template.id
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-indigo-300'
                }`}
                onClick={() => setSelectedTemplate(template)}
              >
                <div className="font-medium">{template.name}</div>
                <div className="text-sm text-gray-500">{template.description}</div>
              </div>
            ))}
          </div>
        </div>
      </Modal>
    </div>
  )
}
