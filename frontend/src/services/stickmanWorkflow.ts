import api from './api'
import type { AiVideoJob } from './aiVideo'

export interface StickmanWorkflowMaterialLibrary {
  key: string
  name: string
  description?: string
  image_url?: string | null
  image_count?: number
  material_count?: number
  is_active?: boolean
  is_visible?: boolean
}

export interface StickmanWorkflowSceneStyle {
  key: string
  label: string
  name?: string
  description?: string
  sampleImageUrl?: string | null
  image_url?: string | null
}

export interface StickmanWorkflowConfig {
  materialLibraries: StickmanWorkflowMaterialLibrary[]
  sceneStyles?: StickmanWorkflowSceneStyle[]
  backgroundTemplates: Array<{ key: string; name: string; description?: string; preview?: string }>
  voices: Array<{ label: string; value: string; provider?: string; previewUrl?: string }>
  defaults: {
    voiceId: string
    materialLibrary: string
    imageMode: string
    scriptMode?: string
  }
  capabilities: {
    canUseAiImages: boolean
    visibleImageModes?: Array<'material_only' | 'ai_image'>
    canChooseImageMode?: boolean
    canUploadBackground: boolean
    materialMode?: 'material_only' | 'ai_image' | 'hybrid'
    maxVideoSeconds: number
  }
}

export interface StickmanWorkflowJobCreate {
  title: string
  topic?: string
  voiceId?: string
  materialLibrary?: string
  tone?: string
  pace?: string
  targetPlatform?: string
  scriptMode?: 'ai' | 'custom'
  customScript?: string
  targetSeconds?: number
  backgroundMode?: string
  backgroundTemplate?: string
  uploadedBackgroundUrl?: string
  imageMode?: 'material_only' | 'ai_image' | 'hybrid'
}

export interface StickmanWorkflowDurationEstimate {
  estimatedSeconds: number
  maxVideoSeconds: number
  allowed: boolean
}

export const stickmanWorkflowApi = {
  getConfig: () => api.get<StickmanWorkflowConfig>('/stickman-workflow/config'),
  estimateDuration: (script: string) =>
    api.post<StickmanWorkflowDurationEstimate>('/stickman-workflow/duration-estimate', { script }),
  uploadBackground: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<{ url: string; filename: string }>('/stickman-workflow/backgrounds', formData)
  },
  previewVoiceUrl: (previewUrl?: string | null) => previewUrl || '',
  createJob: (payload: StickmanWorkflowJobCreate) =>
    api.post<{ jobId: string; projectId: number; status: string }>('/stickman-workflow/jobs', payload),
  listJobs: () => api.get<AiVideoJob[]>('/stickman-workflow/jobs'),
  getJob: (jobId: string) => api.get<AiVideoJob>(`/stickman-workflow/jobs/${jobId}`),
}
