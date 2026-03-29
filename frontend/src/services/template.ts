import api from './api'

export interface Template {
  id: number
  name: string
  description: string | null
  category: string | null
  code: string
  prompt: string | null
  thumbnail: string | null
  is_system: boolean
  is_active: boolean
  is_visible: boolean
  user_id: number | null
  usage_count: number
  created_at: string
}

export interface TemplateList {
  system_templates: Template[]
  user_templates: Template[]
}

export const templateApi = {
  list: () => api.get<TemplateList>('/templates'),
  listActive: () => api.get<Template[]>('/templates/active'),
  get: (id: number) => api.get<Template>(`/templates/${id}`),
  create: (data: { name: string; description: string; category: string; code: string; prompt?: string; thumbnail?: string }) =>
    api.post<Template>('/templates', data),
  update: (id: number, data: Partial<{ name: string; description: string; code: string; prompt: string; thumbnail: string; is_visible: boolean }>) =>
    api.put<Template>(`/templates/${id}`, data),
  delete: (id: number) => api.delete(`/templates/${id}`),
}
