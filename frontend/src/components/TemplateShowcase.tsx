import { useEffect, useMemo, useState } from 'react'
import { Empty, Modal, Spin, Tabs } from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import { templateApi, type Template } from '@/services/template'
import { resolveBackendUrl } from '@/services/api'
import { inferTemplateCategory, type TemplateCategory } from '@/utils/templateCategory'
import './TemplateShowcase.css'

interface TemplateShowcaseProps {
  value: number | null
  onChange: (templateId: number) => void
  category?: string
}

const CATEGORY_MAP: Record<TemplateCategory, string> = {
  thinking: '思维可视化',
  math: '数学可视化',
}

function getVideoUrl(template: Template) {
  return resolveBackendUrl(template.example_video_url)
}

function TemplateCard({
  template,
  value,
  onChange,
  onPreview,
}: {
  template: Template
  value: number | null
  onChange: (templateId: number) => void
  onPreview: (template: Template) => void
}) {
  const videoUrl = getVideoUrl(template)

  return (
    <div
      className={`showcase-card ${value === template.id ? 'showcase-card-selected' : ''}`}
      onClick={() => onChange(template.id)}
    >
      <div className="showcase-card-video">
        {videoUrl ? (
          <video
            src={videoUrl}
            muted
            loop
            autoPlay
            playsInline
            preload="metadata"
            className="showcase-video"
          />
        ) : (
          <div className="showcase-placeholder">
            <PlayCircleOutlined />
          </div>
        )}
        <div
          className="showcase-card-overlay"
          onClick={(event) => {
            event.stopPropagation()
            onPreview(template)
          }}
        >
          <PlayCircleOutlined className="showcase-play-icon" />
          <span>{videoUrl ? '查看完整示例' : '暂无示例视频'}</span>
        </div>
      </div>
      <div className="showcase-card-info">
        <div className="showcase-card-name" title={template.name}>
          {template.name}
        </div>
        {template.description && (
          <div className="showcase-card-desc" title={template.description}>
            {template.description}
          </div>
        )}
      </div>
      {value === template.id && <div className="showcase-card-check">✓</div>}
    </div>
  )
}

export default function TemplateShowcase({ value, onChange, category }: TemplateShowcaseProps) {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [previewTemplate, setPreviewTemplate] = useState<Template | null>(null)

  useEffect(() => {
    let cancelled = false

    const fetchTemplates = async () => {
      setLoading(true)
      try {
        const { data } = await templateApi.list({ limit: 100 })
        const activeTemplates = [...data.system_templates, ...data.user_templates].filter(
          (template) => template.is_active !== false && template.is_visible !== false,
        )
        if (!cancelled) setTemplates(activeTemplates)
      } catch {
        if (!cancelled) setTemplates([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchTemplates()

    return () => {
      cancelled = true
    }
  }, [])

  const normalizedCategory = category === 'math' ? 'math' : category === 'thinking' ? 'thinking' : undefined
  const categories: TemplateCategory[] = normalizedCategory ? [normalizedCategory] : ['thinking', 'math']
  const templatesByCategory = useMemo(() => {
    return categories.reduce<Record<TemplateCategory, Template[]>>(
      (result, currentCategory) => {
        result[currentCategory] = templates.filter((template) => inferTemplateCategory(template) === currentCategory)
        return result
      },
      { thinking: [], math: [] },
    )
  }, [categories, templates])
  const previewUrl = previewTemplate ? getVideoUrl(previewTemplate) : ''

  if (loading) return <Spin />

  const renderTemplateRow = (currentCategory: TemplateCategory) => {
    const categoryTemplates = templatesByCategory[currentCategory]

    if (!categoryTemplates.length) {
      return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可用模板" />
    }

    return (
      <div className="showcase-scroll-wrapper">
        <div className="showcase-card-row">
          {categoryTemplates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              value={value}
              onChange={onChange}
              onPreview={setPreviewTemplate}
            />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="template-showcase">
      {normalizedCategory ? (
        <>
          <div className="showcase-category-label">{CATEGORY_MAP[normalizedCategory]}模板</div>
          {renderTemplateRow(normalizedCategory)}
        </>
      ) : (
        <Tabs
          defaultActiveKey="thinking"
          items={categories.map((currentCategory) => ({
            key: currentCategory,
            label: CATEGORY_MAP[currentCategory],
            children: renderTemplateRow(currentCategory),
          }))}
        />
      )}

      <Modal
        open={!!previewTemplate}
        onCancel={() => setPreviewTemplate(null)}
        footer={null}
        width={800}
        title={previewTemplate?.name}
        className="showcase-preview-modal"
      >
        {previewUrl ? (
          <video src={previewUrl} controls autoPlay className="showcase-preview-video" />
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无示例视频" />
        )}
        {previewTemplate?.description && <p className="showcase-preview-desc">{previewTemplate.description}</p>}
      </Modal>
    </div>
  )
}
