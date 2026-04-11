import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, List, Button, Typography, Space, Spin, Empty, Popconfirm, message } from 'antd'
import { DeleteOutlined, EyeOutlined, PlusOutlined } from '@ant-design/icons'
import { articleApi, Article } from '@/services/article'

const { Text, Title } = Typography

export default function ArticleHistory() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [articles, setArticles] = useState<Article[]>([])

  useEffect(() => {
    loadArticles()
  }, [])

  const loadArticles = async () => {
    setLoading(true)
    try {
      const { data } = await articleApi.list(20)
      setArticles(data)
    } catch (error: any) {
      message.error('加载历史文章失败')
      console.error('Load articles error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await articleApi.delete(id)
      message.success('删除成功')
      loadArticles()
    } catch (error: any) {
      message.error('删除失败')
      console.error('Delete error:', error)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div style={{ padding: '24px', maxWidth: '900px', margin: '0 auto' }}>
      <Card>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={3}>历史文章</Title>
            <Button icon={<PlusOutlined />} type="primary" onClick={() => navigate('/article')}>
              新建文章
            </Button>
          </div>

          {articles.length === 0 ? (
            <Empty description="暂无历史文章" />
          ) : (
            <List
              dataSource={articles}
              renderItem={(article) => (
                <List.Item
                  actions={[
                    <Button
                      icon={<EyeOutlined />}
                      onClick={() => navigate(`/article/${article.id}`)}
                    >
                      查看
                    </Button>,
                    <Popconfirm
                      title="确认删除"
                      description="删除后无法恢复，确定要删除吗？"
                      onConfirm={() => handleDelete(article.id)}
                      okText="删除"
                      cancelText="取消"
                      okButtonProps={{ danger: true }}
                    >
                      <Button icon={<DeleteOutlined />} danger>
                        删除
                      </Button>
                    </Popconfirm>
                  ]}
                >
                  <List.Item.Meta
                    title={article.title || '未命名文章'}
                    description={
                      <Space direction="vertical" size="small">
                        <Text type="secondary">主题: {article.topic}</Text>
                        <Text type="secondary">字数: {article.word_count} | 状态: {article.status}</Text>
                        <Text type="secondary">创建时间: {formatDate(article.created_at)}</Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Space>
      </Card>
    </div>
  )
}