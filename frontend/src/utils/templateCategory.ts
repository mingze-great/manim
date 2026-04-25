import type { Template } from '@/services/template'

export function inferTemplateCategory(template: Pick<Template, 'name' | 'category' | 'description' | 'reference_code'>): 'thinking' | 'math' {
  const name = String(template.name || '').trim()
  if (name.startsWith('思维')) {
    return 'thinking'
  }
  if (name.startsWith('数学')) {
    return 'math'
  }

  const explicitCategory = String(template.category || '').trim().toLowerCase()
  if (explicitCategory === 'thinking' || explicitCategory === 'math') {
    return explicitCategory
  }
  if (template.reference_code?.trim()) {
    return 'math'
  }
  return 'thinking'
}
