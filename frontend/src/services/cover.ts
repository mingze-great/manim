import api from './api'

export interface CoverStyle {
  id: number
  name: string
  description: string | null
  base_prompt: string
  example_image_url: string | null
  font_recommendation: string | null
  color_recommendation: string | null
}

export interface Cover {
  id: number
  style_id: number | null
  title_line1: string
  title_line2: string | null
  topic: string
  font_style: string | null
  font_color: string | null
  image_url: string | null
  local_url: string | null
  created_at: string
}

export const coverApi = {
  getStyles: () =>
    api.get<CoverStyle[]>('/covers/styles'),

  create: (data: {
    style_id?: number | null
    title_line1: string
    title_line2?: string
    topic: string
    font_style?: string
    font_color?: string
  }) =>
    api.post<Cover>('/covers', data),

  get: (id: number) =>
    api.get<Cover>(`/covers/${id}`),

  regenerate: (id: number) =>
    api.post<Cover>(`/covers/${id}/regenerate`),

  getHistory: (limit: number = 20) =>
    api.get<Cover[]>(`/covers/history?limit=${limit}`),

  download: (id: number) =>
    api.get(`/covers/${id}/download`, { responseType: 'blob' }),
}