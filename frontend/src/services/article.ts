import api from './api'

export interface Article {
  id: number
  user_id: number
  title: string | null
  topic: string
  outline: string | null
  content_html: string | null
  content_text: string | null
  images: Array<{ url: string; position: number; prompt: string }> | null
  status: string
  word_count: number
  created_at: string
  updated_at: string
}

export interface Usage {
  used_today: number
  limit: number
  remaining: number
  reset_time: string
}

export const articleApi = {
  getUsage: () => api.get<Usage>('/articles/usage'),
  create: (data: { topic: string; outline?: string }) => api.post<Article>('/articles', data),
  get: (id: number) => api.get<Article>(`/articles/${id}`),
  list: (limit: number = 10) => api.get<Article[]>(`/articles?limit=${limit}`),
  update: (id: number, data: Partial<Article>) => api.put<Article>(`/articles/${id}`, data),
  delete: (id: number) => api.delete(`/articles/${id}`),
  generateOutline: (id: number) => api.post<{ outline: string }>(`/articles/${id}/generate-outline`),
  generateContent: (id: number) => api.post<{ title: string; content: string; word_count: number }>(`/articles/${id}/generate-content`),
  generateImages: (id: number) => api.post<{ images: Array<{ url: string; position: number; prompt: string }> }>(`/articles/${id}/generate-images`),
  generateHtml: (id: number) => api.post<{ html: string }>(`/articles/${id}/generate-html`),
  generateAll: (id: number) => api.post<Article>(`/articles/${id}/generate-all`),
}