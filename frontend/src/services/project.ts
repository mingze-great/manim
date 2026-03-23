import api from './api'

export interface Project {
  id: number
  user_id: number
  title: string
  theme: string
  final_script: string | null
  manim_code: string | null
  custom_code: string | null
  status: string
  video_url: string | null
  error_message: string | null
  template_id: number | null
  created_at: string
  updated_at: string
}

export interface Conversation {
  id: number
  project_id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface Task {
  id: number
  project_id: number
  status: string
  progress: number
  video_url: string | null
  error_message: string | null
  created_at: string
}

export interface PendingResponse {
  status: 'no_message' | 'pending' | 'completed' | 'error'
  response?: Conversation
  has_final_script?: boolean
  error?: string
}

export const projectApi = {
  list: () => api.get<Project[]>('/projects'),
  get: (id: number) => api.get<Project>(`/projects/${id}`),
  create: (data: { title: string; theme: string }) => api.post<Project>('/projects', data),
  update: (id: number, data: Partial<Project>) => api.put<Project>(`/projects/${id}`, data),
  delete: (id: number) => api.delete(`/projects/${id}`),
  getConversations: (id: number) => api.get<Conversation[]>(`/projects/${id}/conversations`),
  sendMessage: (id: number, content: string) => api.post<Conversation>(`/projects/${id}/chat`, { content }),
  getPendingResponse: (id: number) => api.get<PendingResponse>(`/projects/${id}/chat/pending`),
  sendMessageStream: (id: number, _content: string) => `/api/projects/${id}/chat/stream`,
  generateCodeStream: (id: number, templateId?: number) => 
    `/api/projects/${id}/generate-code/stream${templateId ? `?template_id=${templateId}` : ''}`,
  optimizeCodeStream: (id: number, feedback: string) => 
    `/api/projects/${id}/optimize-code/stream?feedback=${encodeURIComponent(feedback)}`,
  getTask: (projectId: number) => api.get<Task>(`/tasks/project/${projectId}`),
  regenerateCode: (id: number) => api.post(`/projects/${id}/regenerate-code`),
}
