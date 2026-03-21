import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Input, Button, Space, message, Modal } from 'antd'
import { SendOutlined, PlayCircleOutlined, SaveOutlined, RobotOutlined, UserOutlined, CodeOutlined } from '@ant-design/icons'
import { projectApi, Conversation, Project } from '@/services/project'
import { templateApi, Template } from '@/services/template'
import { motion, AnimatePresence } from 'framer-motion'
import Prism from 'prismjs'
import 'prismjs/components/prism-python'
import 'prismjs/themes/prism-tomorrow.css'

const { TextArea } = Input

const statusBadgeMap: Record<string, { text: string; color: string }> = {
  draft: { text: '草稿', color: '#faad14' },
  chatting: { text: '待确认', color: '#0066FF' },
  pending: { text: '等待中', color: '#faad14' },
  rendering: { text: '渲染中', color: '#0066FF' },
  completed: { text: '已完成', color: '#52c41a' },
  failed: { text: '失败', color: '#ff4d4f' },
}

function CodeBlock({ code }: { code: string }) {
  const codeRef = useRef<HTMLElement>(null)
  
  useEffect(() => {
    if (codeRef.current) {
      Prism.highlightElement(codeRef.current)
    }
  }, [code])
  
  return (
    <pre className="!bg-[#1e1e1e] !m-0 !p-3 !rounded-lg overflow-x-auto">
      <code ref={codeRef} className="language-python text-sm">
        {code}
      </code>
    </pre>
  )
}

function MessageContent({ content }: { content: string }) {
  const codeBlockRegex = /```python\n([\s\S]*?)```/g
  const parts: React.ReactNode[] = []
  let lastIndex = 0
  let match
  
  while ((match = codeBlockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(
        <pre key={`text-${lastIndex}`} className="whitespace-pre-wrap text-sm mb-2">
          {content.slice(lastIndex, match.index)}
        </pre>
      )
    }
    parts.push(
      <div key={`code-${match.index}`} className="mb-2 rounded-lg overflow-hidden">
        <CodeBlock code={match[1]} />
      </div>
    )
    lastIndex = match.index + match[0].length
  }
  
  if (lastIndex < content.length) {
    parts.push(
      <pre key={`text-${lastIndex}`} className="whitespace-pre-wrap text-sm">
        {content.slice(lastIndex)}
      </pre>
    )
  }
  
  return <>{parts.length > 0 ? parts : <pre className="whitespace-pre-wrap text-sm">{content}</pre>}</>
}

export default function ProjectChat() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [input, setInput] = useState('')
  const [customCode, setCustomCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [aiThinking, setAiThinking] = useState(false)
  const [thinkingMessage, setThinkingMessage] = useState('')
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [templateModalVisible, setTemplateModalVisible] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const fetchProject = async () => {
    try {
      const { data } = await projectApi.get(Number(id))
      setProject(data)
      setCustomCode(data.custom_code || '')
    } catch (error) {
      message.error('获取项目失败')
    }
  }

  const fetchConversations = async () => {
    try {
      console.log('Fetching conversations for project:', id)
      const { data } = await projectApi.getConversations(Number(id))
      console.log('Conversations received:', data)
      setConversations(data)
    } catch (error: any) {
      console.error('获取对话失败:', error)
      message.error('获取对话失败: ' + (error.message || error.toString()))
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

  useEffect(() => {
    fetchProject()
    fetchConversations()
    fetchTemplates()
  }, [id])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversations])

  const handleSend = async () => {
    if (!input.trim()) return
    
    setLoading(true)
    setAiThinking(true)
    setThinkingMessage('正在发送...')
    try {
      setThinkingMessage('AI 思考中...')
      console.log('Sending message:', input)
      const response = await projectApi.sendMessage(Number(id), input)
      console.log('Message sent, response:', response)
      setThinkingMessage('正在获取回复...')
      setInput('')
      await fetchConversations()
      await fetchProject()
    } catch (error: any) {
      console.error('发送失败:', error)
      const errorMsg = error.response?.data?.detail || error.message || '发送消息失败'
      message.error(errorMsg)
    } finally {
      setLoading(false)
      setAiThinking(false)
      setThinkingMessage('')
    }
  }

  const handleGenerateVideo = () => {
    // 直接打开模板选择弹窗，让用户粘贴代码模板
    setTemplateModalVisible(true)
  }

  const handleConfirmTemplate = () => {
    if (!customCode && !selectedTemplate) {
      message.warning('请先粘贴代码模板或选择系统模板')
      return
    }
    
    // 保存自定义代码到项目
    if (customCode) {
      projectApi.update(Number(id), { custom_code: customCode })
    }
    
    setTemplateModalVisible(false)
    // 跳转到代码生成页面
    navigate(`/project/${id}/task?templateId=${selectedTemplate?.id || ''}`)
  }

  const handleSaveAsTemplate = async () => {
    if (!project?.manim_code) {
      message.warning('没有可保存的代码')
      return
    }
    
    const name = prompt('请输入模板名称：')
    if (!name) return
    
    try {
      await templateApi.create({
        name,
        description: '用户保存的模板',
        category: 'custom',
        code: project.manim_code,
        thumbnail: null,
      })
      message.success('模板保存成功')
      fetchTemplates()
    } catch (error) {
      message.error('保存失败')
    }
  }

  return (
    <div className="h-[calc(100vh-140px)] flex gap-4 p-4">
      {/* 聊天区域 */}
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className="flex-1 flex flex-col glass-card"
      >
        {/* 头部 */}
        <div className="p-4 border-b border-gray-100 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#0066FF] to-[#00CCFF] flex items-center justify-center">
              <RobotOutlined className="text-white text-lg" />
            </div>
            <div>
              <h2 className="font-bold text-lg">{project?.title}</h2>
              <p className="text-sm text-gray-500">与AI助手对话优化脚本</p>
            </div>
          </div>
        </div>

        {/* 对话内容 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {conversations.length === 0 && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-12"
            >
              <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 flex items-center justify-center">
                <RobotOutlined className="text-3xl text-[#0066FF]/30" />
              </div>
              <p className="text-gray-400 mb-2">开始与AI助手对话</p>
              <p className="text-sm text-gray-400">例如："创建一个圆形逐渐放大的效果"</p>
            </motion.div>
          )}
          
          <AnimatePresence>
            {conversations.map((conv, index) => (
              <motion.div
                key={conv.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className={`flex ${conv.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex gap-2 max-w-[85%] ${conv.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${
                    conv.role === 'user' 
                      ? 'bg-gradient-to-br from-[#0066FF] to-[#00CCFF]' 
                      : 'bg-gray-100 dark:bg-gray-800'
                  }`}>
                    {conv.role === 'user' 
                      ? <UserOutlined className="text-white text-sm" />
                      : <RobotOutlined className="text-gray-600 dark:text-gray-300 text-sm" />
                    }
                  </div>
                  <div className={`chat-bubble ${
                    conv.role === 'user' 
                      ? 'chat-bubble-user' 
                      : 'chat-bubble-ai'
                  }`}>
                    <MessageContent content={conv.content} />
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          
          {aiThinking && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-start"
            >
              <div className="flex gap-2">
                <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                  <RobotOutlined className="text-gray-600 dark:text-gray-300 text-sm" />
                </div>
                <div className="chat-bubble chat-bubble-ai">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 rounded-full bg-[#0066FF] animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 rounded-full bg-[#0066FF] animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 rounded-full bg-[#0066FF] animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-sm text-gray-500">{thinkingMessage || 'AI正在思考...'}</span>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div className="p-4 border-t border-gray-100 dark:border-gray-700">
          <div className="flex gap-2">
            <TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder="输入你的想法 (Ctrl+Enter 发送)"
              rows={2}
              autoSize={{ minRows: 2, maxRows: 4 }}
              className="flex-1 rounded-lg"
            />
            <Button 
              type="primary" 
              icon={<SendOutlined />} 
              onClick={handleSend} 
              loading={loading}
              className="btn-gradient h-auto px-6"
            >
              发送
            </Button>
          </div>
        </div>
      </motion.div>

      {/* 侧边栏 */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        className="w-80 flex-shrink-0"
      >
        <div className="glass-card p-4 space-y-4">
          <h3 className="font-bold text-lg">项目信息</h3>
          
          <div>
            <div className="text-gray-500 text-sm mb-1">主题</div>
            <div className="text-gray-800 dark:text-gray-200">{project?.theme}</div>
          </div>
          
          <div>
            <div className="text-gray-500 text-sm mb-1">状态</div>
            <span 
              className="status-badge"
              style={{ 
                backgroundColor: `${statusBadgeMap[project?.status || 'draft']?.color}20`,
                color: statusBadgeMap[project?.status || 'draft']?.color 
              }}
            >
              {statusBadgeMap[project?.status || 'draft']?.text}
            </span>
          </div>
          
          {project?.final_script && (
            <div>
              <div className="text-gray-500 text-sm mb-2">最终脚本</div>
              <div className="bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg text-sm max-h-40 overflow-y-auto">
                <pre className="whitespace-pre-wrap text-xs">{project.final_script}</pre>
              </div>
            </div>
          )}
          
          <Space direction="vertical" className="w-full">
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleGenerateVideo}
              block
              className="btn-gradient"
            >
              生成视频
            </Button>
            {project?.manim_code && (
              <Button icon={<SaveOutlined />} onClick={handleSaveAsTemplate} block>
                保存为模板
              </Button>
            )}
          </Space>
        </div>
      </motion.div>

      {/* 模板选择弹窗 - 简化版 */}
      <Modal
        title={
          <div className="flex items-center gap-2">
            <CodeOutlined className="text-[#6366f1]" />
            <span>生成代码</span>
          </div>
        }
        open={templateModalVisible}
        onCancel={() => setTemplateModalVisible(false)}
        onOk={handleConfirmTemplate}
        okText="确认生成代码"
        width={800}
      >
        <div className="py-4">
          <div className="bg-gray-900 dark:bg-gray-800 p-4 rounded-xl mb-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-lg">📋</span>
              <span className="text-white font-medium">粘贴你的代码模板</span>
            </div>
            <div className="text-gray-400 text-sm mb-3">
              AI将完全按照你粘贴的代码风格生成内容代码
            </div>
            <TextArea
              value={customCode}
              onChange={(e) => setCustomCode(e.target.value)}
              placeholder={`\`\`\`python
from manim import *

class MyScene(Scene):
    def construct(self):
        # 粘贴你的代码风格模板...
        pass
\`\`\``}
              rows={16}
              className="font-mono text-sm !bg-gray-800 !text-green-400 !border-gray-700"
              style={{ 
                fontFamily: "'Fira Code', 'Consolas', monospace",
                lineHeight: '1.6',
              }}
            />
          </div>
          
          <div className="text-center text-gray-500 mb-4">— 或 —</div>
          
          <div className="mb-4">
            <div className="font-medium mb-2">🎨 选择系统模板</div>
            {templates.length === 0 ? (
              <div className="text-gray-400 text-center py-4">暂无可用模板</div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {templates.map((template) => (
                  <div
                    key={template.id}
                    className={`p-3 border-2 rounded-lg cursor-pointer transition-all text-sm ${
                      selectedTemplate?.id === template.id
                        ? 'border-[#6366f1] bg-purple-50 dark:bg-purple-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-[#6366f1]'
                    }`}
                    onClick={() => setSelectedTemplate(template)}
                  >
                    {template.name}
                  </div>
                ))}
              </div>
            )}
          </div>
          
          <div className="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded-lg text-sm">
            💡 <strong>提示：</strong>粘贴你的代码模板后，点击"确认生成代码"，AI将结合你的模板风格和对话中确定的内容生成最终代码。
          </div>
        </div>
      </Modal>
    </div>
  )
}
