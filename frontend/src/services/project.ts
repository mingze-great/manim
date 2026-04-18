import api from './api'

export interface Project {
  id: number
  user_id: number
  title: string
  theme: string
  category: string | null
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
  module_type?: string
  storyboard_count?: number
  aspect_ratio?: string
  generation_mode?: string
  voice_source?: string
  tts_provider?: string
  tts_voice?: string
  tts_rate?: string
  voice_file_path?: string
  voice_duration?: number
  storyboard_json?: string
  image_assets_json?: string
  generation_flags?: string
  style_reference_image_path?: string
  style_reference_notes?: string
  style_reference_profile?: string
  preview_image_asset_json?: string
  preview_regen_count?: number
  quota_consumed?: boolean
}

export interface Conversation {
  id: number
  project_id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface StickmanVoiceOption {
  label: string
  value: string
  provider?: string
  gender?: string
  style?: string
  preview_url?: string
}

export interface Task {
  id: number
  project_id: number
  status: string
  progress: number
  video_url: string | null
  error_message: string | null
  created_at: string
  log?: string
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

export interface PendingResponse {
  status: 'no_message' | 'pending' | 'completed' | 'error'
  response?: Conversation
  has_final_script?: boolean
  error?: string
}

export const projectApi = {
  list: () => api.get<Project[]>('/projects'),
  get: (id: number) => api.get<Project>(`/projects/${id}`),
  create: (data: { title: string; theme: string; category?: string }) => api.post<Project>('/projects', data),
  update: (id: number, data: Partial<Project>) => api.put<Project>(`/projects/${id}`, data),
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
  getStickmanVoiceLibrary: () =>
    api.get<{ voices: StickmanVoiceOption[] }>('/projects/stickman/voice-library'),
  previewStickmanVoice: (payload: { text?: string; tts_provider?: string; tts_voice?: string; tts_rate?: string }) =>
    api.post<Blob>('/projects/stickman/preview-voice', payload, { responseType: 'blob' }),
  generateStickmanScript: (projectId: number) =>
    api.post<Project>(`/projects/${projectId}/stickman/script`),
  updateStickmanStoryboards: (projectId: number, payload: { storyboards: any[]; final_script?: string }) =>
    api.put<Project>(`/projects/${projectId}/stickman/storyboards`, payload),
  generateStickmanImages: (projectId: number) =>
    api.post<Project>(`/projects/${projectId}/stickman/images`),
  regenerateStickmanImage: (projectId: number, sceneIndex: number, payload?: { prompt?: string }) =>
    api.post<Project>(`/projects/${projectId}/stickman/images/${sceneIndex}/regenerate`, payload || {}),
  uploadStyleReference: (projectId: number, file: File, notes?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (notes) formData.append('notes', notes)
    return api.post<Project>(`/projects/${projectId}/style-reference`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  uploadVoiceReference: (projectId: number, file: File, source?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source', source || 'upload')
    return api.post<Project>(`/projects/${projectId}/voice-reference`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  uploadStoryboardImages: (projectId: number, files: File[], startIndex?: number) => {
    const formData = new FormData()
    files.forEach(f => formData.append('files', f))
    if (startIndex !== undefined) formData.append('start_index', String(startIndex))
    return api.post<Project>(`/projects/${projectId}/stickman/storyboard-images`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  generateStickmanVideo: (projectId: number) =>
    `/api/tasks/${projectId}/stickman-generate`,
  composeStickmanVideo: (projectId: number) =>
    `/api/tasks/${projectId}/stickman-compose`,
  // 异步渲染（后台运行，可关闭浏览器）
  renderVideoAsync: (projectId: number) =>
    api.post<{ task_id: number; celery_task_id: string; message: string }>(`/tasks/${projectId}/render-async`),
  // 异步生成代码（后台运行，可关闭浏览器）
  generateCodeAsyncV2: (projectId: number, templateId?: number, model?: string) => {
    const params = new URLSearchParams()
    if (templateId) params.append('template_id', String(templateId))
    if (model) params.append('model', model)
    const query = params.toString()
    return api.post<{ task_id: number; celery_task_id: string; message: string }>(
      `/tasks/${projectId}/generate-code-async${query ? `?${query}` : ''}`
    )
  },
  // 查询异步渲染任务状态
  getAsyncTaskStatus: (taskId: number) =>
    api.get<{ task_id: number; status: string; progress: number; video_url: string | null; error_message: string | null; celery_task_id: string }>(`/tasks/task/${taskId}/status`),
  
  // 检查 Celery 和 Redis 状态
  getCeleryStatus: () =>
    api.get<{ redis_connected: boolean; celery_active: boolean; active_tasks: number; status: string }>('/tasks/celery-status'),
  
  // 获取用户进行中的任务
  getInProgressTasks: () =>
    api.get<{ tasks: Array<{ task_id: number; project_id: number; status: string; progress: number; celery_task_id: string; created_at: string }>; count: number }>('/tasks/in-progress'),
  
  // 取消任务
  cancelTask: (taskId: number) =>
    api.post<{ task_id: number; status: string; message: string }>(`/tasks/task/${taskId}/cancel`),
  
  // 获取任务列表
  getTaskList: (params?: { status?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams()
    if (params?.status) query.append('status', params.status)
    if (params?.page) query.append('page', String(params.page))
    if (params?.page_size) query.append('page_size', String(params.page_size))
    return api.get<{ tasks: Task[]; total: number; page: number; page_size: number; total_pages: number }>(`/tasks/list?${query.toString()}`)
  },
  
  // 获取任务日志
  getTaskLog: (taskId: number) =>
    api.get<{ task_id: number; log: string; status: string; error_message: string }>(`/tasks/task/${taskId}/log`),
}
