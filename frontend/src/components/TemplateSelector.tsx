import { useState, useEffect } from 'react'
import { Tabs, Modal, Button, Spin, Empty, Tag } from 'antd'
import { PlayCircleOutlined, CheckCircleFilled } from '@ant-design/icons'
import { templateApi, Template, TemplateCategory } from '@/services/template'

interface TemplateSelectorProps {
  onSelect: (templateId: number | null) => void
  selectedId?: number | null
}

export default function TemplateSelector({ onSelect, selectedId }: TemplateSelectorProps) {
  const [categories, setCategories] = useState<TemplateCategory[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [activeCategory, setActiveCategory] = useState<string>('all')
  const [detailVisible, setDetailVisible] = useState(false)
  const [detailTemplate, setDetailTemplate] = useState<Template | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string>('')
  const [previewVisible, setPreviewVisible] = useState(false)

  const fetchCategories = async () => {
    try {
      const { data } = await templateApi.categories()
      setCategories(data.categories || [])
    } catch (error) {
      console.error('获取分类失败:', error)
    }
  }

  const fetchTemplates = async (categoryCode?: string) => {
    setLoading(true)
    try {
      const { data } = await templateApi.list(categoryCode)
      const all = [...data.system_templates, ...data.user_templates]
      const active = all.filter(t => t.is_active !== false)
      setTemplates(active)
    } catch (error) {
      console.error('获取模板失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCategories()
    fetchTemplates()
  }, [])

  const handleCategoryChange = (code: string) => {
    setActiveCategory(code)
    if (code === 'all') {
      fetchTemplates()
    } else {
      fetchTemplates(code)
    }
  }

  const handleCardClick = (template: Template) => {
    setDetailTemplate(template)
    setDetailVisible(true)
  }

  const handleSelect = (templateId: number) => {
    onSelect(templateId === selectedId ? null : templateId)
    setDetailVisible(false)
  }

  const handlePreviewVideo = (template: Template, e?: React.MouseEvent) => {
    e?.stopPropagation()
    if (template.example_video_url) {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
      setPreviewUrl(template.example_video_url.startsWith('http')
        ? template.example_video_url
        : `${API_BASE}${template.example_video_url}`)
      setPreviewVisible(true)
    }
  }

  const getThumbnailUrl = (template: Template) => {
    if (template.thumbnail) {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
      return template.thumbnail.startsWith('http')
        ? template.thumbnail
        : `${API_BASE}${template.thumbnail}`
    }
    return null
  }

  const categoryTabs = [
    { key: 'all', label: '全部' },
    ...categories.map(c => ({ key: c.code, label: c.name }))
  ]

  return (
    <div className="template-selector">
      {/* 分类标签 */}
      <Tabs
        activeKey={activeCategory}
        onChange={handleCategoryChange}
        size="small"
        items={categoryTabs.map(tab => ({
          key: tab.key,
          label: tab.label
        }))}
        className="template-category-tabs"
      />

      {/* 模板卡片网格 */}
      {loading ? (
        <div className="flex justify-center py-8">
          <Spin />
        </div>
      ) : templates.length === 0 ? (
        <Empty description="暂无模板" />
      ) : (
        <div className="template-grid">
          {templates.map(template => {
            const thumbUrl = getThumbnailUrl(template)
            const isSelected = template.id === selectedId

            return (
              <div
                key={template.id}
                className={`template-card ${isSelected ? 'template-card-selected' : ''}`}
                onClick={() => handleCardClick(template)}
              >
                <div className="template-card-thumb">
                  {thumbUrl ? (
                    <img src={thumbUrl} alt={template.name} />
                  ) : (
                    <div className="template-card-placeholder">
                      <PlayCircleOutlined style={{ fontSize: 32, color: '#999' }} />
                    </div>
                  )}
                  {template.example_video_url && (
                    <div
                      className="template-card-play"
                      onClick={(e) => handlePreviewVideo(template, e)}
                    >
                      <PlayCircleOutlined />
                    </div>
                  )}
                  {isSelected && (
                    <div className="template-card-check">
                      <CheckCircleFilled />
                    </div>
                  )}
                </div>
                <div className="template-card-info">
                  <span className="template-card-name">{template.name}</span>
                  {template.usage_count > 0 && (
                    <span className="template-card-usage">{template.usage_count}次使用</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* 模板详情弹窗 */}
      <Modal
        title={detailTemplate?.name}
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={600}
      >
        {detailTemplate && (
          <div>
            {/* 视频预览 */}
            {detailTemplate.example_video_url && (
              <div className="mb-4">
                <video
                  src={previewUrl || (() => {
                    const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
                    return detailTemplate.example_video_url.startsWith('http')
                      ? detailTemplate.example_video_url
                      : `${API_BASE}${detailTemplate.example_video_url}`
                  })()}
                  controls
                  style={{ width: '100%', borderRadius: 8 }}
                  poster={getThumbnailUrl(detailTemplate) || undefined}
                />
              </div>
            )}
            
            {/* 描述 */}
            {detailTemplate.description && (
              <p className="text-gray-600 mb-4">{detailTemplate.description}</p>
            )}
            
            {/* 使用次数 */}
            <div className="flex items-center gap-2 mb-4 text-sm text-gray-400">
              <span>使用次数：{detailTemplate.usage_count || 0}</span>
              {detailTemplate.category && (
                <Tag>{detailTemplate.category}</Tag>
              )}
            </div>
            
            {/* 操作按钮 */}
            <div className="flex gap-3 justify-end">
              <Button onClick={() => setDetailVisible(false)}>取消</Button>
              <Button
                type="primary"
                icon={detailTemplate.id === selectedId ? <CheckCircleFilled /> : undefined}
                onClick={() => handleSelect(detailTemplate.id)}
              >
                {detailTemplate.id === selectedId ? '已选择' : '选择此模板'}
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* 视频预览弹窗 */}
      <Modal
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width={800}
        destroyOnClose
      >
        {previewUrl && (
          <video
            src={previewUrl}
            controls
            autoPlay
            style={{ width: '100%' }}
          />
        )}
      </Modal>
    </div>
  )
}
