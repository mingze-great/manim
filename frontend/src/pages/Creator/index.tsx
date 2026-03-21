import { useState, useEffect } from 'react'
import { Card, Button, Input, Modal, Form, Spin, message, Select } from 'antd'
import { 
  PlayCircleOutlined, BulbOutlined, RocketOutlined, 
  CodeOutlined, StarOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { projectApi } from '@/services/project'
import { templateApi, Template } from '@/services/template'
import './Creator.css'

const { TextArea } = Input

const quickStarts = [
  {
    id: 'mind',
    title: '思维导图',
    description: '展示多个概念的关系和层次',
    icon: '🧠',
    placeholder: '例如：世界十大顶级思维，包括刻意练习、复利思维、终身学习...'
  },
  {
    id: 'formula',
    title: '公式动画',
    description: '展示数学公式的推导过程',
    icon: '📐',
    placeholder: '例如：勾股定理、欧拉公式、二项式定理...'
  },
  {
    id: 'process',
    title: '流程步骤',
    description: '展示步骤流程和时间线',
    icon: '📋',
    placeholder: '例如：项目管理五大步骤...'
  },
  {
    id: 'custom',
    title: '自定义主题',
    description: '输入任意主题内容',
    icon: '✨',
    placeholder: '输入你想要展示的任何主题内容...'
  }
]

export default function Creator() {
  const navigate = useNavigate()
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(false)
  const [startModalVisible, setStartModalVisible] = useState(false)
  const [selectedQuickStart, setSelectedQuickStart] = useState<typeof quickStarts[0] | null>(null)
  const [themeContent, setThemeContent] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchTemplates()
  }, [])

  const fetchTemplates = async () => {
    try {
      const { data } = await templateApi.list()
      setTemplates([...data.system_templates, ...data.user_templates])
    } catch (error) {
      console.error('获取模板失败:', error)
    }
  }

  const handleQuickStart = (item: typeof quickStarts[0]) => {
    setSelectedQuickStart(item)
    setThemeContent('')
    setSelectedTemplate(null)
    form.resetFields()
    setStartModalVisible(true)
  }

  const handleStartCreate = async () => {
    if (!themeContent.trim()) {
      message.warning('请输入主题内容')
      return
    }

    setLoading(true)
    try {
      const { data } = await projectApi.create({ 
        title: `视频创作-${Date.now()}`,
        theme: themeContent 
      })
      
      if (selectedTemplate) {
        await projectApi.update(data.id, { template_id: selectedTemplate.id })
      }

      message.success('项目创建成功！')
      setStartModalVisible(false)
      navigate(`/project/${data.id}/chat`)
    } catch (error) {
      message.error('创建项目失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="creator-page">
      <div className="creator-hero">
        <div className="hero-content">
          <h1 className="hero-title">
            <RocketOutlined className="mr-3" />
            AI 视频创作助手
          </h1>
          <p className="hero-subtitle">
            选择一个主题风格，AI 将为你生成精彩的动画视频
          </p>
        </div>
      </div>

      <div className="creator-container">
        <div className="quick-starts">
          <h2 className="section-title">
            <StarOutlined className="mr-2" />
            快速开始
          </h2>
          <div className="quick-grid">
            {quickStarts.map((item) => (
              <Card
                key={item.id}
                hoverable
                className="quick-card"
                onClick={() => handleQuickStart(item)}
              >
                <div className="quick-icon">{item.icon}</div>
                <h3 className="quick-title">{item.title}</h3>
                <p className="quick-desc">{item.description}</p>
              </Card>
            ))}
          </div>
        </div>

        {templates.length > 0 && (
          <div className="template-section">
            <h2 className="section-title">
              <CodeOutlined className="mr-2" />
              选择代码模板
            </h2>
            <p className="section-desc">
              选择一个代码模板，AI 将按照该模板的风格生成动画
            </p>
            <div className="template-grid">
              {templates.map((template) => (
                <Card
                  key={template.id}
                  hoverable
                  className={`template-card ${selectedTemplate?.id === template.id ? 'selected' : ''}`}
                  onClick={() => setSelectedTemplate(template)}
                >
                  <div className="template-name">{template.name}</div>
                  <div className="template-desc">{template.description}</div>
                  <div className="template-category">
                    {template.category === 'system' ? '系统模板' : '自定义'}
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}

        <div className="usage-tips">
          <h3>
            <BulbOutlined className="mr-2" />
            使用提示
          </h3>
          <ul>
            <li>选择主题风格后，输入你的内容要点（如：世界十大思维：1.刻意练习 2.复利思维...）</li>
            <li>AI 会列出各要点的内容和动态描述，你可以审核调整</li>
            <li>确认内容后，AI 会结合代码模板生成完整的动画代码</li>
            <li>你可以直接下载生成的代码，在本地运行或进一步修改</li>
          </ul>
        </div>
      </div>

      <Modal
        title={
          <div className="flex items-center gap-2">
            <span className="text-2xl">{selectedQuickStart?.icon}</span>
            <span>创建 {selectedQuickStart?.title} 视频</span>
          </div>
        }
        open={startModalVisible}
        onCancel={() => setStartModalVisible(false)}
        footer={null}
        width={700}
      >
        <Spin spinning={loading}>
          <div className="py-4">
            <Form form={form} layout="vertical">
              <Form.Item 
                label="主题内容" 
                required
                help={selectedQuickStart?.placeholder}
              >
                <TextArea
                  value={themeContent}
                  onChange={(e) => setThemeContent(e.target.value)}
                  placeholder={selectedQuickStart?.placeholder}
                  rows={8}
                  className="text-base"
                />
              </Form.Item>

              {templates.length > 0 && (
                <Form.Item label="选择代码模板（可选）">
                  <Select
                    placeholder="不选择则使用默认风格"
                    value={selectedTemplate?.id}
                    onChange={(id) => {
                      const t = templates.find(t => t.id === id)
                      setSelectedTemplate(t || null)
                    }}
                    options={templates.map(t => ({
                      value: t.id,
                      label: t.name
                    }))}
                    allowClear
                    className="w-full"
                  />
                </Form.Item>
              )}
            </Form>

            <div className="flex justify-end gap-3 mt-4">
              <Button onClick={() => setStartModalVisible(false)}>
                取消
              </Button>
              <Button 
                type="primary" 
                icon={<PlayCircleOutlined />}
                onClick={handleStartCreate}
                loading={loading}
                className="btn-gradient"
                size="large"
              >
                开始创作
              </Button>
            </div>
          </div>
        </Spin>
      </Modal>
    </div>
  )
}
