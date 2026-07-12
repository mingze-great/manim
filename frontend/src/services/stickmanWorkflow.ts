import api from './api'
import type { AiVideoJob } from './aiVideo'

export interface StickmanWorkflowJobCreate {
  topic: string
  title?: string
  sceneCount?: number
  voiceId?: string
  tone?: string
  pace?: string
  targetPlatform?: string
}

export const stickmanWorkflowApi = {
  createJob: (payload: StickmanWorkflowJobCreate) =>
    api.post<{ jobId: string; projectId: number; status: string }>('/stickman-workflow/jobs', payload),
  getJob: (jobId: string) => api.get<AiVideoJob>(`/stickman-workflow/jobs/${jobId}`),
}

