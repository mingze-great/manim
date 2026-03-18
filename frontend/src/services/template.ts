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
  create: (data: Omit<Template, 'id' | 'is_system' | 'user_id' | 'usage_count' | 'created_at'>) =>
    api.post<Template>('/templates', data),
  delete: (id: number) => api.delete(`/templates/${id}`),
}
