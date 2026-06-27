import api from './api'

export interface AiVideoJobCreate {
  title?: string
  prompt?: string
  script: string
  videoType: string
  contentType?: string
  style: string
  visualStyle?: string
  aspectRatio: string
  voiceProvider: string
  voiceId: string
  subtitleMode: string
  brandKitId?: string
  targetPlatform: string
  tone?: string
  pace?: string
  goal?: string
  customPrompt?: string
  sceneCount?: number
  draftScenes?: any[]
}

export interface AiVideoJob {
  jobId: string
  id: number
  projectId: number
  status: string
  progress: number
  stage: string
  message: string
  outputUrl: string | null
  coverUrl: string | null
  errorMessage: string | null
  createdAt: string
  updatedAt: string
  completedAt: string | null
}

export interface AiVideoProject {
  id: number
  title: string
  videoType: string
  aspectRatio: string
  status: string
  coverUrl: string | null
  outputUrl: string | null
  currentVersionId: number | null
  createdAt: string
  updatedAt: string
  projectJson?: any
}

export interface AiVideoOverview {
  stats: {
    totalProjects: number
    generating: number
    completed: number
    monthlyExports: number
  }
  recentProjects: AiVideoProject[]
  queue: AiVideoJob[]
}

export interface AiVideoCapability {
  module: string
  storageRoot: string
  renderServiceUrl: string
  renderService: { available: boolean; status?: any; message?: string }
  cosyVoiceService?: { available: boolean; status?: any; message?: string }
  ffmpeg: { available: boolean; path?: string | null }
  isolation: Record<string, any>
  limits: Record<string, any>
}

export interface AiVideoExport {
  id: number
  projectId: number
  title: string
  versionNo: number
  outputUrl: string | null
  coverUrl: string | null
  status: string
  createdAt: string
}

export const aiVideoApi = {
  overview: () => api.get<AiVideoOverview>('/ai-video/overview'),
  capabilities: () => api.get<AiVideoCapability>('/ai-video/capabilities'),
  templates: () => api.get('/ai-video/templates'),
  storyboardDraft: (payload: AiVideoJobCreate) => api.post<{ projectJson: any; scenes: any[]; recommendations: string[] }>('/ai-video/storyboard-draft', payload),
  createJob: (payload: AiVideoJobCreate) => api.post<{ jobId: string; projectId: number; status: string }>('/ai-video/jobs', payload),
  getJob: (jobId: string) => api.get<AiVideoJob>(`/ai-video/jobs/${jobId}`),
  cancelJob: (jobId: string) => api.post<AiVideoJob>(`/ai-video/jobs/${jobId}/cancel`),
  retryJob: (jobId: string) => api.post<{ jobId: string; projectId: number; status: string }>(`/ai-video/jobs/${jobId}/retry`),
  listProjects: () => api.get<AiVideoProject[]>('/ai-video/projects'),
  getProject: (id: number) => api.get<AiVideoProject>(`/ai-video/projects/${id}`),
  planEdit: (id: number, message: string) => api.post<{ editPlan: string[]; canApply: boolean }>(`/ai-video/projects/${id}/edit`, { message, mode: 'plan_then_apply' }),
  applyEdit: (id: number, editPlan: string[], message?: string) => api.post(`/ai-video/projects/${id}/apply-edit`, { editPlan, message }),
  versions: (id: number) => api.get(`/ai-video/projects/${id}/versions`),
  rollbackVersion: (projectId: number, versionId: number) => api.post(`/ai-video/projects/${projectId}/versions/${versionId}/rollback`),
  exports: () => api.get<AiVideoExport[]>('/ai-video/exports'),
  brandKits: () => api.get('/ai-video/brand-kits'),
  createBrandKit: (payload: { name: string; colors: string[] }) => api.post('/ai-video/brand-kits', payload),
}
