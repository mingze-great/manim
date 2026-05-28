import type { Template } from '@/services/template'

export type TemplateCategory = 'thinking' | 'math'

export function inferTemplateCategory(
  template: Pick<Template, 'name' | 'category' | 'description' | 'reference_code'>,
): TemplateCategory {
  const explicitCategory = String(template.category || '').trim().toLowerCase()
  if (explicitCategory === 'thinking' || explicitCategory === 'math') {
    return explicitCategory
  }

  const text = `${template.name || ''} ${template.description || ''}`.toLowerCase()
  if (text.includes('数学') || text.includes('math')) {
    return 'math'
  }
  if (text.includes('思维') || text.includes('thinking')) {
    return 'thinking'
  }

  if (template.reference_code?.trim()) {
    return 'math'
  }
  return 'thinking'
}
