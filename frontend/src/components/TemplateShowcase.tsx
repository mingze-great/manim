import { useEffect, useState } from 'react'
import { Card, Empty, Radio, Spin, Tag } from 'antd'
import api from '@/services/api'

interface TemplateItem {
  id: number
  name: string
  description?: string | null
  category?: string | null
}

interface TemplateShowcaseProps {
  value: number | null
  onChange: (value: number | null) => void
  category?: string
}

interface TemplateListResponse {
  system_templates?: TemplateItem[]
  user_templates?: TemplateItem[]
}

export default function TemplateShowcase({ value, onChange, category }: TemplateShowcaseProps) {
  const [templates, setTemplates] = useState<TemplateItem[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    const fetchTemplates = async () => {
      setLoading(true)
      try {
        const { data } = await api.get<TemplateListResponse>('/templates', {
          params: { category, visible_only: true },
        })
        const items = [
          ...(data.system_templates || []),
          ...(data.user_templates || []),
        ]
        if (!cancelled) setTemplates(items)
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
  }, [category])

  if (loading) return <Spin />
  if (!templates.length) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可用模板" />

  return (
    <Radio.Group value={value} onChange={(event) => onChange(event.target.value)} className="w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {templates.map((template) => (
          <Radio.Button key={template.id} value={template.id} className="h-auto p-0 border-0 bg-transparent">
            <Card size="small" className={value === template.id ? 'border-blue-500' : ''}>
              <div className="font-medium">{template.name}</div>
              {template.description && <div className="text-xs text-gray-500 mt-1">{template.description}</div>}
              {template.category && <Tag className="mt-2">{template.category}</Tag>}
            </Card>
          </Radio.Button>
        ))}
      </div>
    </Radio.Group>
  )
}
