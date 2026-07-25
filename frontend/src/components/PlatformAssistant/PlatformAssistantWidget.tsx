import { useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Button, Drawer, Input, Space, Spin, Tag, Typography, message as antMessage } from 'antd'
import {
  ArrowRightOutlined,
  MessageOutlined,
  RobotOutlined,
  SendOutlined,
} from '@ant-design/icons'
import {
  platformAssistantApi,
  type PlatformAssistantAction,
  type PlatformAssistantSource,
} from '@/services/platformAssistant'
import './PlatformAssistantWidget.css'

const { Text } = Typography

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  actions?: PlatformAssistantAction[]
  sources?: PlatformAssistantSource[]
}

const quickQuestions = [
  '如何生成火柴人视频',
  '如何选择素材库',
  '如何兑换邀请码',
  '如何查看作品',
  '合作者如何发码',
]

function moduleFromPath(pathname: string) {
  if (pathname.startsWith('/stickman-workflow')) return 'stickman-workflow'
  if (pathname.startsWith('/profile')) return 'profile'
  if (pathname.startsWith('/partner')) return 'partner'
  if (pathname.startsWith('/history')) return 'history'
  if (pathname.startsWith('/docs')) return 'docs'
  if (pathname.startsWith('/ai-video')) return 'ai-video'
  if (pathname.startsWith('/knowledge-ip')) return 'knowledge-ip'
  return 'platform'
}

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export default function PlatformAssistantWidget() {
  const location = useLocation()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: '你好，我是平台 AI 助手。你可以问我怎么生成视频、选择素材库、兑换邀请码或查看作品。',
      actions: [
        { label: '去火柴人工作流', route: '/stickman-workflow' },
        { label: '去个人中心兑换码', route: '/profile' },
      ],
      sources: [{ title: '平台使用引导', source: '内置知识库' }],
    },
  ])
  const inputRef = useRef<HTMLTextAreaElement | null>(null)
  const currentModule = useMemo(() => moduleFromPath(location.pathname), [location.pathname])

  const sendMessage = async (text: string) => {
    const cleanText = text.trim()
    if (!cleanText || loading) return

    const userMessage: ChatMessage = {
      id: createMessageId(),
      role: 'user',
      content: cleanText,
    }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const { data } = await platformAssistantApi.chat({
        message: cleanText,
        pagePath: location.pathname,
        module: currentModule,
      })
      setMessages((prev) => [
        ...prev,
        {
          id: createMessageId(),
          role: 'assistant',
          content: data.answer,
          actions: data.suggestedActions,
          sources: data.sources,
        },
      ])
    } catch (error) {
      antMessage.error('AI 助手暂时没有响应，请稍后再试')
      setMessages((prev) => [
        ...prev,
        {
          id: createMessageId(),
          role: 'assistant',
          content: '我现在暂时没连上服务。你可以先进入火柴人工作流，输入标题并保持默认配置生成；有邀请码就在个人中心兑换。',
          actions: [
            { label: '去火柴人工作流', route: '/stickman-workflow' },
            { label: '去个人中心兑换码', route: '/profile' },
          ],
          sources: [{ title: '离线引导', source: '前端兜底' }],
        },
      ])
    } finally {
      setLoading(false)
      window.setTimeout(() => inputRef.current?.focus(), 0)
    }
  }

  const handleAction = (route: string) => {
    navigate(route)
    setOpen(false)
  }

  return (
    <>
      <Button
        type="primary"
        size="large"
        icon={<RobotOutlined />}
        className="platform-assistant-fab"
        onClick={() => setOpen(true)}
      >
        AI助手
      </Button>

      <Drawer
        title={
          <Space size={10}>
            <RobotOutlined />
            <span>AI助手</span>
          </Space>
        }
        placement="right"
        width={420}
        open={open}
        onClose={() => setOpen(false)}
        className="platform-assistant-drawer"
      >
        <div className="platform-assistant-shell">
          <div className="platform-assistant-quick">
            {quickQuestions.map((question) => (
              <Button
                key={question}
                size="small"
                icon={<MessageOutlined />}
                onClick={() => sendMessage(question)}
                disabled={loading}
              >
                {question}
              </Button>
            ))}
          </div>

          <div className="platform-assistant-messages">
            {messages.map((item) => (
              <div key={item.id} className={`platform-assistant-message ${item.role}`}>
                <div className="platform-assistant-bubble">
                  {item.content.split('\n').map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </div>
                {item.role === 'assistant' && !!item.sources?.length && (
                  <div className="platform-assistant-sources">
                    {item.sources.slice(0, 3).map((source) => (
                      <Tag key={`${item.id}-${source.source}-${source.title}`} bordered={false}>
                        {source.title || source.source}
                      </Tag>
                    ))}
                  </div>
                )}
                {item.role === 'assistant' && !!item.actions?.length && (
                  <Space wrap className="platform-assistant-actions">
                    {item.actions.map((action) => (
                      <Button
                        key={`${item.id}-${action.route}`}
                        size="small"
                        type="link"
                        icon={<ArrowRightOutlined />}
                        onClick={() => handleAction(action.route)}
                      >
                        {action.label}
                      </Button>
                    ))}
                  </Space>
                )}
              </div>
            ))}
            {loading && (
              <div className="platform-assistant-message assistant">
                <div className="platform-assistant-bubble loading">
                  <Spin size="small" />
                  <Text type="secondary">正在结合当前页面生成回答...</Text>
                </div>
              </div>
            )}
          </div>

          <div className="platform-assistant-input">
            <Input.TextArea
              ref={inputRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onPressEnter={(event) => {
                if (!event.shiftKey) {
                  event.preventDefault()
                  sendMessage(input)
                }
              }}
              placeholder="问我平台怎么用..."
              autoSize={{ minRows: 2, maxRows: 4 }}
              maxLength={500}
              disabled={loading}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={() => sendMessage(input)}
              loading={loading}
              disabled={!input.trim()}
            />
          </div>
        </div>
      </Drawer>
    </>
  )
}
