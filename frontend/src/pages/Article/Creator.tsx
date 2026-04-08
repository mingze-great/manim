import { useState, useEffect } from 'react'
import { Card, Button, Input, message, Typography, Space, Steps, Alert, Divider } from 'antd'
import { RocketOutlined, FileTextOutlined, EditOutlined, CheckOutlined, ReloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { articleApi, Usage, Article } from '@/services/article'
import CategorySelector from './components/CategorySelector'
import PhonePreview from './components/PhonePreview'

const { TextArea } = Input
const { Text, Title } = Typography

export default function ArticleCreator() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [topic, setTopic] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('生活')
  const [usage, setUsage] = useState<Usage | null>(null)
  
  const [article, setArticle] = useState<Article | null>(null)
  const [outline, setOutline] = useState('')
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')

  useEffect(() => {
    loadUsage()
  }, [])

  const loadUsage = async () => {
    try {
      const { data } = await articleApi.getUsage()
      setUsage(data)
    } catch (error) {
      console.error('Failed to load usage:', error)
    }
  }

  const handleCreateArticle = async () => {
    if (!topic.trim()) {
      message.warning('请输入文章主题')
      return
    }

    if (usage && usage.remaining <= 0) {
      message.error('今日使用次数已达上限')
      return
    }

    setLoading(true)
    try {
      const { data } = await articleApi.create({ 
        topic, 
        category: selectedCategory 
      })
      setArticle(data)
      setCurrentStep(1)
      message.success('文章创建成功')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '创建失败')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateOutline = async () => {
    if (!article) return
    
    setLoading(true)
    try {
      const { data } = await articleApi.generateOutline(article.id)
      setOutline(data.outline)
      message.success('大纲生成成功')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateContent = async () => {
    if (!article) return
    
    setLoading(true)
    try {
      const { data } = await articleApi.generateContent(article.id)
      setTitle(data.title)
      setContent(data.content)
      message.success('文案生成成功')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveContent = async () => {
    if (!article) return
    
    setLoading(true)
    try {
      await articleApi.update(article.id, {
        title,
        content_text: content,
        outline
      })
      message.success('保存成功')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateImages = async () => {
    if (!article) return
    
    setLoading(true)
    try {
      await articleApi.generateImages(article.id)
      message.success('配图生成成功')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateHtml = async () => {
    if (!article) return
    
    setLoading(true)
    try {
      await articleApi.generateHtml(article.id)
      const { data } = await articleApi.get(article.id)
      setArticle(data)
      message.success('HTML 生成成功')
      setCurrentStep(4)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCopyHtml = () => {
    if (!article?.content_html) {
      message.warning('暂无 HTML 内容')
      return
    }
    
    navigator.clipboard.writeText(article.content_html)
      .then(() => message.success('已复制，可粘贴到微信公众号'))
      .catch(() => message.error('复制失败'))
  }

  const nextStep = () => setCurrentStep(currentStep + 1)
  const prevStep = () => setCurrentStep(currentStep - 1)

  const steps = [
    { title: '选择方向', icon: <FileTextOutlined /> },
    { title: '生成大纲', icon: <EditOutlined /> },
    { title: '生成文案', icon: <EditOutlined /> },
    { title: '生成配图', icon: <RocketOutlined /> },
    { title: '预览完成', icon: <CheckOutlined /> }
  ]

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <Steps current={currentStep} items={steps} style={{ marginBottom: '24px' }} />

      <div style={{ display: 'flex', gap: '24px' }}>
        <div style={{ flex: '1' }}>
          <Card>
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <div style={{ textAlign: 'center' }}>
                <FileTextOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
                <Title level={3} style={{ marginTop: '16px' }}>公众号文章生成器</Title>
              </div>

              {usage && (
                <Alert
                  type="info"
                  message={`今日已用 ${usage.used_today} 次 / 剩余 ${usage.remaining} 次`}
                  showIcon
                />
              )}

              {currentStep === 0 && (
                <>
                  <CategorySelector 
                    value={selectedCategory} 
                    onChange={setSelectedCategory} 
                  />
                  
                  <TextArea
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="输入文章主题，例如：如何培养孩子的阅读习惯..."
                    rows={4}
                    disabled={loading}
                  />

                  <Button
                    type="primary"
                    icon={<RocketOutlined />}
                    onClick={handleCreateArticle}
                    loading={loading}
                    disabled={!usage || usage.remaining <= 0}
                    block
                    size="large"
                  >
                    创建文章
                  </Button>
                </>
              )}

              {currentStep === 1 && (
                <>
                  <Title level={4}>文章大纲</Title>
                  <TextArea
                    value={outline}
                    onChange={(e) => setOutline(e.target.value)}
                    rows={8}
                    disabled={loading}
                    placeholder="点击生成大纲..."
                  />
                  
                  <Space>
                    <Button 
                      icon={<ReloadOutlined />} 
                      onClick={handleGenerateOutline}
                      loading={loading}
                    >
                      重新生成大纲
                    </Button>
                    <Button 
                      type="primary" 
                      onClick={nextStep}
                      disabled={!outline}
                    >
                      下一步：生成文案
                    </Button>
                  </Space>
                </>
              )}

              {currentStep === 2 && (
                <>
                  <Title level={4}>文章标题</Title>
                  <Input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="文章标题"
                    disabled={loading}
                  />
                  
                  <Divider />
                  
                  <Title level={4}>文章内容</Title>
                  <TextArea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    rows={12}
                    disabled={loading}
                    placeholder="点击生成文案..."
                  />
                  
                  <Space>
                    <Button 
                      icon={<ReloadOutlined />} 
                      onClick={handleGenerateContent}
                      loading={loading}
                    >
                      重新生成文案
                    </Button>
                    <Button onClick={handleSaveContent} loading={loading}>
                      保存修改
                    </Button>
                    <Button 
                      type="primary" 
                      onClick={nextStep}
                      disabled={!content}
                    >
                      下一步：生成配图
                    </Button>
                  </Space>
                </>
              )}

              {currentStep === 3 && (
                <>
                  <Alert
                    type="warning"
                    message="文案满意后，生成配图"
                    description="配图将根据文案内容智能插入合适位置"
                    showIcon
                  />
                  
                  <div style={{ marginTop: '16px' }}>
                    <Text strong>当前文案字数：</Text>
                    <Text>{content.length} 字</Text>
                  </div>
                  
                  <Space>
                    <Button 
                      type="primary" 
                      icon={<RocketOutlined />}
                      onClick={handleGenerateImages}
                      loading={loading}
                    >
                      生成配图
                    </Button>
                    <Button 
                      type="primary"
                      onClick={handleGenerateHtml}
                      loading={loading}
                      disabled={!article?.images}
                    >
                      生成 HTML 并预览
                    </Button>
                  </Space>
                </>
              )}

              {currentStep === 4 && (
                <>
                  <Alert
                    type="success"
                    message="文章生成完成！"
                    description="可以在右侧预览效果，确认后复制到微信公众号"
                    showIcon
                  />
                  
                  <Space style={{ marginTop: '16px' }}>
                    <Button type="primary" onClick={handleCopyHtml}>
                      复制 HTML 到剪贴板
                    </Button>
                    <Button onClick={() => navigate(`/article/${article?.id}`)}>
                      查看详情
                    </Button>
                    <Button onClick={() => navigate('/article/history')}>
                      查看历史
                    </Button>
                  </Space>
                </>
              )}

              {currentStep > 0 && currentStep < 4 && (
                <Button onClick={prevStep}>上一步</Button>
              )}
            </Space>
          </Card>
        </div>

        <div style={{ width: '400px' }}>
          <Card title="手机预览" style={{ height: '100%' }}>
            <PhonePreview article={article} />
          </Card>
        </div>
      </div>
    </div>
  )
}