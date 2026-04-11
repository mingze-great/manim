import api from './api'

export interface Project {
  id: number
  user_id: number
  title: string
  theme: string
  category: string | null
  module_type: 'manim' | 'stickman'
  storyboard_count: number
  aspect_ratio: string
  generation_mode: 'one_click' | 'step_by_step'
  voice_source: 'ai' | 'upload' | 'record'
  voice_file_path: string | null
  voice_duration: number | null
  tts_provider: string
  tts_voice: string
  tts_rate: string
  style_reference_image_path: string | null
  style_reference_notes: string | null
  style_reference_profile: string | null
  preview_image_asset_json: string | null
  preview_regen_count: number
  storyboard_json: string | null
  image_assets_json: string | null
  generation_flags: string | null
  final_script: string | null
  manim_code: string | null
  custom_code: string | null
  status: string
  video_url: string | null
  error_message: string | null
  template_id: number | null
  render_fail_count: number
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
  task_type: string
  status: string
  progress: number
  video_url: string | null
  error_message: string | null
  log?: string | null
  created_at: string
}

export interface BackgroundTask {
  task_id: number
  task_type: string
  status: string
  progress: number
  message: string | null
  error: string | null
  code?: string
  created_at: string | null
  started_at: string | null
  completed_at: string | null
}

export interface StickmanVoiceOption {
  label: string
  value: string
  provider: string
  gender?: string
  style?: string
  preview_url?: string
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
  create: (data: { title: string; theme: string; category?: string; module_type?: 'manim' | 'stickman'; storyboard_count?: number; aspect_ratio?: string; generation_mode?: 'one_click' | 'step_by_step'; voice_source?: 'ai' | 'upload' | 'record'; tts_provider?: string; tts_voice?: string; tts_rate?: string }) => api.post<Project>('/projects', data),
  update: (id: number, data: Partial<Project>) => api.put<Project>(`/projects/${id}`, data),
  uploadVoiceReference: (id: number, file: File, source: 'upload' | 'record') => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source', source)
    return api.post<Project>(`/projects/${id}/voice-reference`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  uploadStyleReference: (id: number, file: File, notes?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (notes) formData.append('notes', notes)
    return api.post<Project>(`/projects/${id}/style-reference`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  generateStickmanPreviewImage: (id: number, regenerate: boolean = false) => api.post<Project>(`/projects/${id}/stickman/preview-image`, { regenerate }),
  getStickmanVoiceLibrary: () => api.get<{ voices: StickmanVoiceOption[] }>(`/projects/stickman/voice-library`),
  previewStickmanVoice: (data: { text?: string; tts_provider?: string; tts_voice?: string; tts_rate?: string }) =>
    api.post<Blob>(`/projects/stickman/preview-voice`, data, { responseType: 'blob' as any }),
  createCustomStickmanVoice: (file: File, label: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('label', label)
    return api.post<{ message: string; voice: StickmanVoiceOption }>(`/projects/stickman/custom-voice`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  generateStickmanScript: (id: number) => api.post<Project>(`/projects/${id}/stickman/script`),
  updateStickmanStoryboards: (id: number, data: { storyboards: any[]; final_script?: string }) => api.put<Project>(`/projects/${id}/stickman/storyboards`, data),
  generateStickmanImages: (id: number) => api.post<Project>(`/projects/${id}/stickman/images`),
  regenerateStickmanImage: (id: number, sceneIndex: number, data?: { prompt?: string }) => api.post<Project>(`/projects/${id}/stickman/images/${sceneIndex}/regenerate`, data || {}),
  delete: (id: number) => api.delete(`/projects/${id}`),
  batchDelete: (ids: number[]) => api.post('/projects/batch-delete', { project_ids: ids }),
  getConversations: (id: number) => api.get<Conversation[]>(`/projects/${id}/conversations`),
  sendMessage: (id: number, content: string) => api.post<Conversation>(`/projects/${id}/chat`, { content }),
  getPendingResponse: (id: number) => api.get<PendingResponse>(`/projects/${id}/chat/pending`),
  sendMessageStream: (id: number, _content: string) => `/api/projects/${id}/chat/stream`,
  generateCodeStream: (id: number, templateId?: number) => 
    `/api/projects/${id}/generate-code/stream${templateId ? `?template_id=${templateId}` : ''}`,
  optimizeCodeStream: (id: number, feedback: string) => 
    `/api/projects/${id}/optimize-code/stream?feedback=${encodeURIComponent(feedback)}`,
  getTask: (projectId: number) => api.get<Task>(`/tasks/project/${projectId}`),
  generateStickmanStream: (projectId: number) => `/api/tasks/${projectId}/stickman-generate`,
  generateStickmanComposeStream: (projectId: number) => `/api/tasks/${projectId}/stickman-compose`,
  regenerateCode: (id: number) => api.post(`/projects/${id}/regenerate-code`),
  fixCode: (projectId: number, data: { error_message: string; current_code: string }) =>
    api.post<{ success: boolean; fixed_code?: string; fix_description?: string; message?: string }>(
      `/tasks/${projectId}/fix-code`,
      data
    ),
  fixCodeStream: (projectId: number) =>
    `/api/tasks/${projectId}/fix-code-stream`,
  generateCodeAsync: (projectId: number, templateId?: number) =>
    api.post<{ task_id: number; status: string; message: string }>(
      `/tasks/${projectId}/generate-code-async${templateId ? `?template_id=${templateId}` : ''}`
    ),
  getBackgroundTask: (taskId: number) =>
    api.get<BackgroundTask>(`/tasks/background/${taskId}`),
  getLatestCodeTask: (projectId: number) =>
    api.get<{ task_id: number | null; status: string | null; progress: number; message: string | null; error: string | null }>(
      `/tasks/${projectId}/latest-code-task`
    ),
  updateConversation: (convId: number, content: string) =>
    api.put<{ message: string; conversation: Conversation; final_script_updated: boolean }>(
      `/projects/conversations/${convId}`,
      { content }
    ),
  useCustomScript: (projectId: number, script: string, autoFormat: boolean = true) =>
    api.post<{ message: string; final_script: string; formatted: boolean }>(
      `/projects/${projectId}/use-custom-script`,
      { script, auto_format: autoFormat }
    ),
}
