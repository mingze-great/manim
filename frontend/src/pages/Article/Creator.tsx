import { useState, useEffect } from 'react'
import { Card, Button, Input, message, Progress, Typography, Space } from 'antd'
import { EditOutlined, RocketOutlined, FileTextOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { articleApi, Usage } from '@/services/article'

const { TextArea } = Input
const { Text } = Typography

export default function ArticleCreator() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [topic, setTopic] = useState('')
  const [usage, setUsage] = useState<Usage | null>(null)
  const [step, setStep] = useState(0)

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

  const handleGenerate = async () => {
    if (!topic.trim()) {
      message.warning('请输入文章主题')
      return
    }

    if (usage && usage.remaining <= 0) {
      message.error('今日使用次数已达上限')
      return
    }

    setLoading(true)
    setStep(0)

    try {
      setStep(1)
      const { data: article } = await articleApi.create({ topic })

      setStep(2)
      await articleApi.generateOutline(article.id)

      setStep(3)
      await articleApi.generateContent(article.id)

      setStep(4)
      await articleApi.generateImages(article.id)

      setStep(5)
      await articleApi.generateHtml(article.id)

      message.success('文章生成完成')
      navigate(`/article/${article.id}`)
    } catch (error: any) {
      const detail = error.response?.data?.detail || error.message || '生成失败'
      message.error(detail)
      console.error('生成文章失败:', error)
    } finally {
      setLoading(false)
      setStep(0)
      loadUsage()
    }
  }

  const getStepText = () => {
    switch (step) {
      case 1: return '创建文章...'
      case 2: return '生成大纲...'
      case 3: return '生成内容...'
      case 4: return '生成配图...'
      case 5: return '生成 HTML...'
      default: return ''
    }
  }

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <Card>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center' }}>
            <FileTextOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
            <h1 style={{ marginTop: '16px' }}>公众号文章生成器</h1>
            <p style={{ color: '#666' }}>输入主题，自动生成700-1000字文章及配图</p>
          </div>

          {usage && (
            <div style={{ textAlign: 'center', padding: '12px', background: '#f5f5f5', borderRadius: '8px' }}>
              <Text type="secondary">
                今日已用 {usage.used_today} 次 / 剩余 {usage.remaining} 次
              </Text>
            </div>
          )}

          <TextArea
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="输入文章主题，例如：如何养成早起的好习惯..."
            rows={4}
            disabled={loading}
          />

          {loading && (
            <div style={{ textAlign: 'center' }}>
              <Progress percent={step * 20} status="active" />
              <Text type="secondary">{getStepText()}</Text>
            </div>
          )}

          <Button
            type="primary"
            icon={<RocketOutlined />}
            onClick={handleGenerate}
            loading={loading}
            disabled={!usage || usage.remaining <= 0}
            block
            size="large"
          >
            一键生成文章
          </Button>

          <Button
            icon={<EditOutlined />}
            onClick={() => navigate('/article/history')}
            block
          >
            查看历史文章
          </Button>
        </Space>
      </Card>
    </div>
  )
}