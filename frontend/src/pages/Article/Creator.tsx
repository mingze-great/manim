import { useState, useEffect, useRef } from 'react'
import { Card, Button, Input, message, Typography, Space, Steps, Alert, Divider, Popconfirm } from 'antd'
import { RocketOutlined, FileTextOutlined, EditOutlined, CheckOutlined, ReloadOutlined, DeleteOutlined } from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { articleApi, Usage, Article } from '@/services/article'
import CategorySelector from './components/CategorySelector'
import PhonePreview from './components/PhonePreview'

const { TextArea } = Input
const { Text, Title } = Typography

export default function ArticleCreator() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [currentStep, setCurrentStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [topic, setTopic] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('生活')
  const [usage, setUsage] = useState<Usage | null>(null)
  const [autoSaveStatus, setAutoSaveStatus] = useState<string>('')
  const [generatingStatus, setGeneratingStatus] = useState<string>('')
  const [useStream] = useState(true) // 默认使用流式生成
  
  const [article, setArticle] = useState<Article | null>(null)
  const [outline, setOutline] = useState('')
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [outlineRequirement, setOutlineRequirement] = useState('')
  const [contentRequirement, setContentRequirement] = useState('')
  
  const autoSaveTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    loadUsage()
  }, [])

  useEffect(() => {
    const topicParam = searchParams.get('topic')
    const categoryParam = searchParams.get('category')
    if (topicParam) setTopic(topicParam)
    if (categoryParam) setSelectedCategory(categoryParam)
  }, [searchParams])

  // 自动保存功能
  useEffect(() => {
    if (article && currentStep >= 2) {
      // 清除之前的定时器
      if (autoSaveTimerRef.current) {
        clearInterval(autoSaveTimerRef.current)
      }
      
      // 设置新的自动保存定时器（每30秒）
      autoSaveTimerRef.current = setInterval(() => {
        if (title || content || outline) {
          handleAutoSave()
        }
      }, 30000)
      
      // 页面关闭时提醒保存
      const handleBeforeUnload = (e: BeforeUnloadEvent) => {
        if (title || content || outline) {
          e.preventDefault()
          e.returnValue = ''
        }
      }
      window.addEventListener('beforeunload', handleBeforeUnload)
      
      return () => {
        if (autoSaveTimerRef.current) {
          clearInterval(autoSaveTimerRef.current)
        }
        window.removeEventListener('beforeunload', handleBeforeUnload)
      }
    }
  }, [article, currentStep, title, content, outline])

  const handleAutoSave = async () => {
    if (!article) return
    
    try {
      await articleApi.update(article.id, {
        title,
        content_text: content,
        outline
      })
      setAutoSaveStatus(`自动保存于 ${new Date().toLocaleTimeString()}`)
      setTimeout(() => setAutoSaveStatus(''), 3000)
    } catch (error) {
      console.error('Auto save failed:', error)
    }
  }

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
    setGeneratingStatus('正在生成大纲...')
    
    try {
      if (useStream) {
        // 流式生成
        setGeneratingStatus('正在连接AI模型...')
        const result = await articleApi.generateOutlineStream(
          article.id,
          outlineRequirement,
          (partialOutline) => {
            setOutline(partialOutline)
            setGeneratingStatus('正在生成大纲...')
          }
        )
        setOutline(result.outline)
        setTitle(result.title)
        setGeneratingStatus('')
        message.success('大纲生成成功')
      } else {
        // 非流式生成
        setGeneratingStatus('正在调用AI模型...')
        const { data } = await articleApi.generateOutline(article.id, outlineRequirement)
        setOutline(data.outline)
        setTitle(data.title)
        setGeneratingStatus('')
        message.success('大纲生成成功')
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '生成失败'
      message.error(errorMsg)
      setGeneratingStatus('')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateContent = async () => {
    if (!article) return
    
    setLoading(true)
    setGeneratingStatus('正在生成文案...')
    
    try {
      if (useStream) {
        // 流式生成
        setGeneratingStatus('正在连接AI模型...')
        const result = await articleApi.generateContentStream(
          article.id,
          contentRequirement,
          (partialContent) => {
            setContent(partialContent)
            setGeneratingStatus(`正在生成文案... (${partialContent.length}字)`)
          }
        )
        setContent(result.content)
        setGeneratingStatus('')
        message.success('文案生成成功')
      } else {
        // 非流式生成
        setGeneratingStatus('正在调用AI模型...')
        const { data } = await articleApi.generateContent(article.id, contentRequirement)
        setTitle(data.title)
        setContent(data.content)
        setGeneratingStatus('')
        message.success('文案生成成功')
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '生成失败'
      message.error(errorMsg)
      setGeneratingStatus('')
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
      const { data } = await articleApi.generateImages(article.id)
      
      // 刷新article数据以显示生成的图片
      const { data: articleData } = await articleApi.get(article.id)
      setArticle(articleData)
      
      const successMsg = data.failed > 0 
        ? `配图生成完成：成功${data.success}张，失败${data.failed}张`
        : `配图生成成功，共${data.success}张`
      message.success(successMsg)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRegenerateImage = async (imageIndex: number) => {
    if (!article) return
    
    setLoading(true)
    try {
      await articleApi.regenerateImage(article.id, imageIndex)
      
      // 刷新article数据
      const { data } = await articleApi.get(article.id)
      setArticle(data)
      
      message.success('图片重新生成成功')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '重新生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteImage = async (imageIndex: number) => {
    if (!article) return
    
    setLoading(true)
    try {
      await articleApi.deleteImage(article.id, imageIndex)
      
      // 刷新article数据
      const { data } = await articleApi.get(article.id)
      setArticle(data)
      
      message.success('图片删除成功')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败')
    } finally {
      setLoading(false)
    }
  }

  const handleMoveImage = async (fromIndex: number, toIndex: number) => {
    if (!article?.images) return
    
    const images = [...article.images]
    const [movedImage] = images.splice(fromIndex, 1)
    images.splice(toIndex, 0, movedImage)
    
    try {
      await articleApi.updateImages(article.id, images)
      
      // 刷新article数据
      const { data } = await articleApi.get(article.id)
      setArticle(data)
      
      message.success('图片位置已调整')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '调整失败')
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
    <div style={{ 
      padding: '24px', 
      maxWidth: '1200px', 
      margin: '0 auto',
      height: 'calc(100vh - 64px)',
      display: 'flex',
      flexDirection: 'column'
    }}>
      <Steps current={currentStep} items={steps} style={{ marginBottom: '24px', flexShrink: 0 }} />

      <div style={{ display: 'flex', gap: '24px', flex: 1, minHeight: 0 }}>
        <div style={{ flex: '1', overflow: 'auto' }}>
          <Card>
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              {generatingStatus && (
                <Alert
                  type="info"
                  message={generatingStatus}
                  showIcon
                  style={{ marginBottom: '12px' }}
                />
              )}
              
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
                    onTopicSelect={(topic) => setTopic(topic)}
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
                  <div style={{ marginBottom: '12px' }}>
                    <Text type="secondary" style={{ fontSize: '12px', display: 'block', marginBottom: '8px' }}>
                      补充要求（可选）：
                    </Text>
                    <Input.TextArea
                      placeholder="例如：重点关注XX方面、加入XX案例、使用XX风格..."
                      rows={2}
                      value={outlineRequirement}
                      onChange={(e) => setOutlineRequirement(e.target.value)}
                      disabled={loading}
                    />
                  </div>
                  
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
                      {outline ? '重新生成大纲' : '生成大纲'}
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
                  <div style={{ marginBottom: '12px' }}>
                    <Text type="secondary" style={{ fontSize: '12px', display: 'block', marginBottom: '8px' }}>
                      补充要求（可选）：
                    </Text>
                    <Input.TextArea
                      placeholder="例如：增加XX案例、修改XX部分、调整语气..."
                      rows={2}
                      value={contentRequirement}
                      onChange={(e) => setContentRequirement(e.target.value)}
                      disabled={loading}
                    />
                  </div>
                  
                  <Title level={4}>文章标题</Title>
                  <Input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="文章标题"
                    disabled={loading}
                  />
                  
                  <Divider />
                  
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Title level={4}>文章内容</Title>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                      {autoSaveStatus && (
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          {autoSaveStatus}
                        </Text>
                      )}
                      <div style={{ fontSize: '14px', color: content.length < 800 ? '#ff4d4f' : content.length > 2000 ? '#faad14' : '#52c41a' }}>
                        字数：{content.length} 字
                        {content.length < 800 && content.length > 0 && <span style={{ marginLeft: '8px' }}>(建议800字以上)</span>}
                        {content.length > 2000 && <span style={{ marginLeft: '8px' }}>(建议2000字以内)</span>}
                      </div>
                    </div>
                  </div>
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
                      {content ? '重新生成文案' : '生成文案'}
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
                  
                  {/* 显示已生成的图片 */}
                  {article?.images && article.images.length > 0 && (
                    <Card 
                      size="small" 
                      style={{ marginTop: '16px', marginBottom: '16px' }}
                      title={`已生成 ${article.images.length} 张配图`}
                    >
                      <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                        {article.images.map((img, idx) => (
                          <div key={idx} style={{ textAlign: 'center', width: '200px' }}>
                            <img 
                              src={img.url}
                              alt={`配图${idx + 1}`}
                              style={{ 
                                width: '100%', 
                                height: 'auto', 
                                borderRadius: '8px',
                                border: '1px solid #d9d9d9',
                                display: 'block',
                                marginBottom: '8px'
                              }}
                            />
                            <Text type="secondary" style={{ fontSize: '12px', display: 'block', marginBottom: '8px' }}>
                              {img.type === 'cover' ? '封面图' : `内容图${idx}`}
                            </Text>
                            
                            {/* 图片操作按钮 */}
                            <Space direction="vertical" size="small" style={{ width: '100%' }}>
                              <Button 
                                size="small" 
                                icon={<ReloadOutlined />}
                                onClick={() => handleRegenerateImage(idx)}
                                loading={loading}
                                style={{ width: '100%' }}
                              >
                                重新生成
                              </Button>
                              
                              <Space size="small" style={{ width: '100%' }}>
                                <Button 
                                  size="small"
                                  disabled={idx === 0}
                                  onClick={() => handleMoveImage(idx, idx - 1)}
                                  style={{ flex: 1 }}
                                >
                                  ↑ 上移
                                </Button>
                                <Button 
                                  size="small"
                                  disabled={idx === article.images!.length - 1}
                                  onClick={() => handleMoveImage(idx, idx + 1)}
                                  style={{ flex: 1 }}
                                >
                                  ↓ 下移
                                </Button>
                              </Space>
                              
                              <Popconfirm
                                title="确定删除这张图片吗？"
                                onConfirm={() => handleDeleteImage(idx)}
                                okText="删除"
                                cancelText="取消"
                              >
                                <Button 
                                  size="small" 
                                  danger
                                  icon={<DeleteOutlined />}
                                  loading={loading}
                                  style={{ width: '100%' }}
                                >
                                  删除图片
                                </Button>
                              </Popconfirm>
                            </Space>
                          </div>
                        ))}
                      </div>
                    </Card>
                  )}
                  
                  <Space>
                    <Button 
                      type="primary" 
                      icon={<RocketOutlined />}
                      onClick={handleGenerateImages}
                      loading={loading}
                    >
                      {article?.images && article.images.length > 0 ? '重新生成配图' : '生成配图'}
                    </Button>
                    <Button 
                      type="primary"
                      onClick={handleGenerateHtml}
                      loading={loading}
                      disabled={!article?.images || article.images.length === 0}
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

        <div style={{ width: '400px', flexShrink: 0 }}>
          <Card 
            title="手机预览" 
            style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
            bodyStyle={{ flex: 1, overflow: 'hidden', padding: '16px' }}
          >
            <PhonePreview article={article} />
          </Card>
        </div>
      </div>
    </div>
  )
}
