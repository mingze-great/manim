import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Input, Button, Space, message, Modal, Empty } from 'antd'
import { SendOutlined, PlayCircleOutlined, SaveOutlined, RobotOutlined, UserOutlined, CodeOutlined, FileTextOutlined } from '@ant-design/icons'
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
  const [customCodeModalVisible, setCustomCodeModalVisible] = useState(false)
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

  const handleSaveCustomCode = async () => {
    try {
      await projectApi.update(Number(id), { custom_code: customCode })
      message.success('自定义代码已保存')
      setCustomCodeModalVisible(false)
    } catch (error) {
      message.error('保存失败')
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
    if (!project?.final_script) {
      message.warning('请先完成脚本对话')
      return
    }
    setTemplateModalVisible(true)
  }

  const handleConfirmTemplate = () => {
    setTemplateModalVisible(false)
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
              disabled={!project?.final_script}
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

      {/* 模板选择弹窗 */}
      <Modal
        title={
          <div className="flex items-center gap-2">
            <CodeOutlined className="text-[#0066FF]" />
            <span>生成设置</span>
          </div>
        }
        open={templateModalVisible}
        onCancel={() => setTemplateModalVisible(false)}
        onOk={handleConfirmTemplate}
        okText="确认生成"
        width={900}
      >
        {/* 自定义代码模板 - 更突出显示 */}
        <div className="mb-6 p-4 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-xl border-2 border-purple-200 dark:border-purple-800">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="font-medium text-base flex items-center gap-2">
                <span className="text-2xl">📋</span>
                <span className="text-purple-700 dark:text-purple-300">粘贴你的代码作为模板</span>
              </div>
              <div className="text-xs text-gray-500 mt-1">AI将完全按照你粘贴的代码风格生成新代码</div>
            </div>
            <Button 
              type="primary" 
              danger={!customCode}
              onClick={() => setCustomCodeModalVisible(true)}
              icon={<FileTextOutlined />}
            >
              {customCode ? '✅ 已设置' : '➕ 粘贴代码'}
            </Button>
          </div>
          {customCode && (
            <div className="bg-white/50 dark:bg-gray-800/50 p-3 rounded-lg max-h-32 overflow-y-auto border border-purple-100 dark:border-purple-900">
              <pre className="text-xs font-mono whitespace-pre-wrap text-gray-700 dark:text-gray-300">{customCode.slice(0, 300)}{customCode.length > 300 ? '...' : ''}</pre>
            </div>
          )}
          {!customCode && (
            <div className="text-center py-4 text-gray-400 text-sm">
              暂未粘贴代码，系统将使用默认风格
            </div>
          )}
        </div>
        
        {/* 系统模板选择 */}
        <div className="mb-4">
          <div className="font-medium mb-3 flex items-center gap-2">
            <span className="text-lg">🎨</span>
            <span>或选择系统模板</span>
          </div>
          {templates.length === 0 ? (
            <Empty description="暂无可用模板" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {templates.map((template) => (
                <div
                  key={template.id}
                  className={`p-3 border-2 rounded-xl cursor-pointer transition-all ${
                    selectedTemplate?.id === template.id
                      ? 'border-[#0066FF] bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-200 dark:border-gray-700 hover:border-[#0066FF]'
                  }`}
                  onClick={() => setSelectedTemplate(template)}
                >
                  <div className="font-medium text-sm">{template.name}</div>
                  <div className="text-xs text-gray-500">{template.description}</div>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* 提示信息 */}
        <div className="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded-lg border border-yellow-200 dark:border-yellow-800">
          <div className="text-sm text-yellow-800 dark:text-yellow-200">
            <strong>💡 提示：</strong>粘贴你的代码后，AI会完全按照该代码的风格（结构、动画、配色）生成新的动画。如果不粘贴，系统将使用默认风格。
          </div>
        </div>
      </Modal>

      <Modal
        title={
          <div className="flex items-center gap-2">
            <FileTextOutlined className="text-purple-500" />
            <span>粘贴你的代码作为模板</span>
          </div>
        }
        open={customCodeModalVisible}
        onCancel={() => setCustomCodeModalVisible(false)}
        onOk={handleSaveCustomCode}
        okText="保存并使用此模板"
        width={800}
      >
        <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="text-sm text-blue-700 dark:text-blue-300">
            <strong>📌 使用说明：</strong>粘贴你的Manim代码后，AI会分析并完全遵循该代码的风格来生成新内容。
          </div>
        </div>
        <TextArea
          value={customCode}
          onChange={(e) => setCustomCode(e.target.value)}
          placeholder={`请在这里粘贴你的Manim代码，例如：

from manim import *

class MyScene(Scene):
    def construct(self):
        # 你的代码风格将被完全复制
        text = Text("示例")
        self.play(Write(text))
        self.wait()
`}
          rows={20}
          className="font-mono text-sm rounded-lg"
        />
      </Modal>
    </div>
  )
}
