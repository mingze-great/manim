import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Input, message, Spin, Typography, Space, Image, Modal } from 'antd'
import { EditOutlined, CopyOutlined, DeleteOutlined, EyeOutlined, SaveOutlined, ReloadOutlined } from '@ant-design/icons'
import { articleApi, Article } from '@/services/article'

const { TextArea } = Input
const { Title, Text } = Typography

export default function ArticleEditor() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [article, setArticle] = useState<Article | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [editContent, setEditContent] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [previewVisible, setPreviewVisible] = useState(false)

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

  const handleRegenerateHtml = async () => {
    if (!article) return

    setLoading(true)
    try {
      await articleApi.generateHtml(article.id)
      message.success('HTML 重新生成成功')
      loadArticle()
    } catch (error: any) {
      message.error('生成失败')
      console.error('Regenerate error:', error)
    } finally {
      setLoading(false)
    }
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
    <div style={{ padding: '24px', maxWidth: '900px', margin: '0 auto' }}>
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
                  <Button icon={<EyeOutlined />} onClick={() => setPreviewVisible(true)}>
                    预览
                  </Button>
                  <Button icon={<CopyOutlined />} onClick={handleCopyHtml} type="primary">
                    复制 HTML
                  </Button>
                </>
              )}
            </Space>
          </div>

          <div>
            <Text type="secondary">主题: {article.topic}</Text>
            <Text type="secondary" style={{ marginLeft: '16px' }}>字数: {article.word_count}</Text>
          </div>

          {isEditing ? (
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Input
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                placeholder="文章标题"
              />
              <TextArea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                rows={12}
                placeholder="文章内容"
              />
              <Space>
                <Button icon={<SaveOutlined />} onClick={handleSave} loading={saving} type="primary">
                  保存
                </Button>
                <Button onClick={() => setIsEditing(false)}>
                  取消
                </Button>
              </Space>
            </Space>
          ) : (
            <>
              {article.images && article.images.length > 0 && (
                <div>
                  <Text strong>配图:</Text>
                  <div style={{ marginTop: '8px' }}>
                    <Image.PreviewGroup>
                      {article.images.map((img, index) => (
                        <Image
                          key={index}
                          src={img.url}
                          width={200}
                          height={150}
                          style={{ objectFit: 'cover', marginRight: '8px', borderRadius: '4px' }}
                        />
                      ))}
                    </Image.PreviewGroup>
                  </div>
                </div>
              )}

              <div>
                <Text strong>文章内容:</Text>
                <div style={{
                  marginTop: '12px',
                  padding: '16px',
                  background: '#f5f5f5',
                  borderRadius: '8px',
                  maxHeight: '400px',
                  overflowY: 'auto'
                }}>
                  <Text>{article.content_text}</Text>
                </div>
              </div>
            </>
          )}

          <Space style={{ marginTop: '16px' }}>
            <Button icon={<ReloadOutlined />} onClick={handleRegenerateHtml}>
              重新生成 HTML
            </Button>
            <Button icon={<DeleteOutlined />} danger onClick={handleDelete}>
              删除文章
            </Button>
          </Space>
        </Space>
      </Card>

      <Modal
        title="微信公众号预览"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        width={600}
        footer={null}
      >
        <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
          {article.content_html && (
            <div dangerouslySetInnerHTML={{ __html: article.content_html }} />
          )}
        </div>
      </Modal>
    </div>
  )
}