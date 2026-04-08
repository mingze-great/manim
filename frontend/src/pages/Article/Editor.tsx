import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Input, message, Spin, Typography, Space, Modal, Divider, Alert } from 'antd'
import { EditOutlined, CopyOutlined, DeleteOutlined, SaveOutlined, ReloadOutlined, RocketOutlined } from '@ant-design/icons'
import { articleApi, Article } from '@/services/article'
import PhonePreview from './components/PhonePreview'

const { TextArea } = Input
const { Title, Text } = Typography

export default function ArticleEditor() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [article, setArticle] = useState<Article | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [editOutline, setEditOutline] = useState('')
  const [editContent, setEditContent] = useState('')
  const [isEditing, setIsEditing] = useState(false)

  useEffect(() => {
    loadArticle()
  }, [id])

  const loadArticle = async () => {
    if (!id) return

    setLoading(true)
    try {
      const { data } = await articleApi.get(parseInt(id))
      setArticle(data)
      setEditTitle(data.title || '')
      setEditOutline(data.outline || '')
      setEditContent(data.content_text || '')
    } catch (error: any) {
      message.error('加载文章失败')
      console.error('Load article error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!article) return

    setSaving(true)
    try {
      await articleApi.update(article.id, {
        title: editTitle,
        outline: editOutline,
        content_text: editContent
      })
      message.success('保存成功')
      setIsEditing(false)
      loadArticle()
    } catch (error: any) {
      message.error('保存失败')
      console.error('Save error:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleGenerateImages = async () => {
    if (!article) return

    setLoading(true)
    try {
      await articleApi.generateImages(article.id)
      message.success('配图生成成功')
      loadArticle()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成失败')
      console.error('Generate images error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateHtml = async () => {
    if (!article) return

    setLoading(true)
    try {
      await articleApi.generateHtml(article.id)
      message.success('HTML 生成成功')
      loadArticle()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成失败')
      console.error('Generate HTML error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCopyHtml = () => {
    if (!article?.content_html) {
      message.warning('请先生成 HTML')
      return
    }

    navigator.clipboard.writeText(article.content_html)
      .then(() => message.success('已复制到剪贴板，可直接粘贴到微信公众号'))
      .catch(() => message.error('复制失败'))
  }

  const handleDelete = async () => {
    if (!article) return

    Modal.confirm({
      title: '确认删除',
      content: '删除后无法恢复，确定要删除这篇文章吗？',
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await articleApi.delete(article.id)
          message.success('删除成功')
          navigate('/article/history')
        } catch (error: any) {
          message.error('删除失败')
          console.error('Delete error:', error)
        }
      }
    })
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!article) {
    return <div style={{ padding: '24px', textAlign: 'center' }}>文章不存在</div>
  }

  return (
    <div style={{ height: 'calc(100vh - 64px)', display: 'flex' }}>
      <div style={{ flex: '1', padding: '24px', overflowY: 'auto', borderRight: '1px solid #f0f0f0' }}>
        <Card>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Title level={3}>{isEditing ? '编辑文章' : article.title || '公众号文章'}</Title>
              <Space>
                {!isEditing && (
                  <>
                    <Button icon={<EditOutlined />} onClick={() => setIsEditing(true)}>
                      编辑
                    </Button>
                    <Button type="primary" icon={<CopyOutlined />} onClick={handleCopyHtml}>
                      复制 HTML
                    </Button>
                  </>
                )}
              </Space>
            </div>

            <div>
              <Text type="secondary">主题: {article.topic}</Text>
              <Text type="secondary" style={{ marginLeft: '16px' }}>创作方向: {article.category}</Text>
              <Text type="secondary" style={{ marginLeft: '16px' }}>字数: {article.word_count}</Text>
            </div>

            {isEditing ? (
              <>
                <div>
                  <Text strong>文章标题</Text>
                  <Input
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    placeholder="文章标题"
                    style={{ marginTop: '8px' }}
                  />
                </div>

                <div>
                  <Text strong>文章大纲</Text>
                  <TextArea
                    value={editOutline}
                    onChange={(e) => setEditOutline(e.target.value)}
                    rows={4}
                    placeholder="文章大纲"
                    style={{ marginTop: '8px' }}
                  />
                </div>

                <div>
                  <Text strong>文章内容</Text>
                  <TextArea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    rows={12}
                    placeholder="文章内容"
                    style={{ marginTop: '8px' }}
                  />
                </div>

                <Space>
                  <Button icon={<SaveOutlined />} onClick={handleSave} loading={saving} type="primary">
                    保存
                  </Button>
                  <Button onClick={() => setIsEditing(false)}>
                    取消
                  </Button>
                </Space>
              </>
            ) : (
              <>
                {article.images && article.images.length > 0 && (
                  <div>
                    <Text strong>配图: {article.images.length} 张</Text>
                  </div>
                )}

                <div>
                  <Text strong>文章内容:</Text>
                  <div
                    style={{
                      marginTop: '12px',
                      padding: '16px',
                      background: '#f5f5f5',
                      borderRadius: '8px',
                      maxHeight: '400px',
                      overflowY: 'auto',
                      whiteSpace: 'pre-wrap'
                    }}
                  >
                    {article.content_text}
                  </div>
                </div>
              </>
            )}

            <Divider />

            <Space wrap>
              <Button 
                icon={<RocketOutlined />} 
                onClick={handleGenerateImages}
                disabled={isEditing}
              >
                生成配图
              </Button>
              <Button 
                icon={<ReloadOutlined />} 
                onClick={handleGenerateHtml}
                disabled={isEditing}
              >
                重新生成 HTML
              </Button>
              <Button 
                icon={<DeleteOutlined />} 
                danger 
                onClick={handleDelete}
                disabled={isEditing}
              >
                删除文章
              </Button>
            </Space>
          </Space>
        </Card>
      </div>

      <div style={{ width: '400px', padding: '24px', background: '#fafafa', overflowY: 'auto' }}>
        <Card title="手机预览" style={{ height: '100%' }}>
          <PhonePreview article={article} />
        </Card>
      </div>
    </div>
  )
}