import api from './api'

export interface Template {
  id: number
  name: string
  description: string | null
  category: string | null
  code: string
  thumbnail: string | null
  is_system: boolean
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
  get: (id: number) => api.get<Template>(`/templates/${id}`),
  create: (data: { name: string; description: string; category: string; code: string; thumbnail?: string }) =>
    api.post<Template>('/templates', data),
  update: (id: number, data: Partial<{ name: string; description: string; code: string; thumbnail: string }>) =>
    api.put<Template>(`/templates/${id}`, data),
  delete: (id: number) => api.delete(`/templates/${id}`),
}
