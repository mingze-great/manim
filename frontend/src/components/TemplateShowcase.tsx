import { useState, useRef, useEffect } from 'react'
import { Modal, Tabs, Spin } from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import { templateApi, Template } from '@/services/template'
import './TemplateShowcase.css'

interface TemplateShowcaseProps {
  value: number | null
  onChange: (templateId: number) => void
  category?: string
}

const CATEGORY_MAP: Record<string, string> = {
  thinking: '思维可视化',
  math: '数学可视化',
}

function inferTemplateCategory(template: Template): 'thinking' | 'math' {
  const explicitCategory = String(template.category || '').trim().toLowerCase()
  if (explicitCategory === 'thinking' || explicitCategory === 'math') {
    return explicitCategory
  }
  if (template.reference_code?.trim()) {
    return 'math'
  }
  const raw = `${template.category || ''} ${template.name || ''} ${template.description || ''}`.toLowerCase()
  const mathHints = ['math', '数学', '公式', '定理', '几何', '函数', '矩阵', '傅里叶', '欧拉', '微积分', '物理']
  return mathHints.some((hint) => raw.includes(hint)) ? 'math' : 'thinking'
}

function TemplateCard({ t, value, onChange, onPreview }: {
  t: Template
  value: number | null
  onChange: (id: number) => void
  onPreview: (t: Template) => void
}) {
  const getVideoUrl = (template: Template) => template.example_video_url || ''

  return (
    <div
      className={`showcase-card ${value === t.id ? 'showcase-card-selected' : ''}`}
      onClick={() => onChange(t.id)}
    >
      <div className="showcase-card-video">
        {getVideoUrl(t) ? (
          <video
            src={getVideoUrl(t)}
            muted
            loop
            autoPlay
            playsInline
            className="showcase-video"
            onMouseEnter={e => (e.target as HTMLVideoElement).play()}
            onMouseLeave={e => { const v = e.target as HTMLVideoElement; v.pause(); v.currentTime = 0; }}
          />
        ) : (
          <div className="showcase-placeholder">
            <PlayCircleOutlined />
          </div>
        )}
        <div className="showcase-card-overlay" onClick={e => { e.stopPropagation(); onPreview(t); }}>
          <PlayCircleOutlined className="showcase-play-icon" />
          <span>查看完整示例</span>
        </div>
      </div>
      <div className="showcase-card-info">
        <div className="showcase-card-name">{t.name}</div>
        {t.description && <div className="showcase-card-desc">{t.description}</div>}
      </div>
      {value === t.id && <div className="showcase-card-check">✓</div>}
    </div>
  )
}

export default function TemplateShowcase({ value, onChange, category }: TemplateShowcaseProps) {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [previewTemplate, setPreviewTemplate] = useState<Template | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchTemplates()
  }, [category])

  const fetchTemplates = async () => {
    setLoading(true)
    try {
      const { data } = await templateApi.list()
      const all = [...data.system_templates, ...data.user_templates].filter(t => t.is_active !== false)
      setTemplates(all)
    } catch {
    } finally {
      setLoading(false)
    }
  }

  const getVideoUrl = (t: Template) => t.example_video_url || ''
  const categories = ['thinking', 'math']
  const defaultTab = category === 'math' ? 'math' : 'thinking'
  const getTemplatesByCategory = (cat: string) => templates.filter(t => inferTemplateCategory(t) === cat)

  if (loading) return <Spin />

  // 单分类模式：直接展示该类别的模板，不显示 Tab
  if (category) {
    return (
      <div className="template-showcase">
        <div className="showcase-category-label">
          {CATEGORY_MAP[category] || category}模板
        </div>
        <div className="showcase-scroll-wrapper">
          <div className="showcase-card-row" ref={scrollRef}>
            {getTemplatesByCategory(category).map(t => (
              <TemplateCard
                key={t.id}
                t={t}
                value={value}
                onChange={onChange}
                onPreview={setPreviewTemplate}
              />
            ))}
            {getTemplatesByCategory(category).length === 0 && (
              <div className="showcase-empty">暂无该分类的模板</div>
            )}
          </div>
        </div>

        <Modal
          open={!!previewTemplate}
          onCancel={() => setPreviewTemplate(null)}
          footer={null}
          width={800}
          title={previewTemplate?.name}
          className="showcase-preview-modal"
        >
          {previewTemplate && getVideoUrl(previewTemplate) && (
            <video
              src={getVideoUrl(previewTemplate)}
              controls
              autoPlay
              className="showcase-preview-video"
            />
          )}
          {previewTemplate?.description && (
            <p className="showcase-preview-desc">{previewTemplate.description}</p>
          )}
        </Modal>
      </div>
    )
  }

  // 多分类模式：显示 Tab 切换
  return (
    <div className="template-showcase">
      <Tabs
        defaultActiveKey={defaultTab}
        items={categories.map(cat => ({
          key: cat,
          label: CATEGORY_MAP[cat] || cat,
          children: (
            <div className="showcase-scroll-wrapper">
              <div className="showcase-card-row" ref={scrollRef}>
                {getTemplatesByCategory(cat).map(t => (
                  <TemplateCard
                    key={t.id}
                    t={t}
                    value={value}
                    onChange={onChange}
                    onPreview={setPreviewTemplate}
                  />
                ))}
                {getTemplatesByCategory(cat).length === 0 && (
                  <div className="showcase-empty">暂无该分类的模板</div>
                )}
              </div>
            </div>
          ),
        }))}
      />

      <Modal
        open={!!previewTemplate}
        onCancel={() => setPreviewTemplate(null)}
        footer={null}
        width={800}
        title={previewTemplate?.name}
        className="showcase-preview-modal"
      >
        {previewTemplate && getVideoUrl(previewTemplate) && (
          <video
            src={getVideoUrl(previewTemplate)}
            controls
            autoPlay
            className="showcase-preview-video"
          />
        )}
        {previewTemplate?.description && (
          <p className="showcase-preview-desc">{previewTemplate.description}</p>
        )}
      </Modal>
    </div>
  )
}
