import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'
import { getApiBase } from './api'

const API_BASE = getApiBase()

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export interface User {
  id: number
  username: string
  email: string
  phone?: string | null
  is_active: boolean
  is_admin: boolean
  role?: 'user' | 'partner' | 'admin'
  referred_by_partner_id?: number | null
  referral_code?: string | null
  frontend_version?: 'legacy' | 'v2'
  is_approved: boolean
  expires_at?: string
  created_at: string
  daily_video_limit?: number
  module_permissions?: Record<string, { enabled: boolean; daily_limit: number; used_today?: number; last_reset_date?: string | null }>
  total_articles?: number
  token_usage?: number
  recent_articles?: Array<{ id: number; title: string; status_text: string; created_at: string }>
  recent_projects?: Array<{ id: number; title: string; status_text: string; created_at: string }>
  latest_task?: { project_title: string; status: string; error_message?: string | null; log?: string | null; created_at?: string | null } | null
}

export interface UserStats {
  total_projects: number
  total_tasks: number
  completed_tasks: number
  failed_tasks: number
}

export interface AuditLog {
  id: number
  user_id: number | null
  username: string | null
  action: string
  resource: string | null
  resource_id: number | null
  details: string | null
  ip_address: string | null
  created_at: string
}

export interface SystemStats {
  total_users: number
  active_users: number
  total_projects: number
  total_videos: number
  api_calls_today: number
  cpu_usage: number
  memory_usage: number
  disk_usage: number
}

export interface InvitationCode {
  code: string
  expires_at: string | null
  is_used: boolean
  used_by: number | null
  used_at: string | null
  created_at: string
}

export interface TokenUsageItem {
  id: number
  username: string
  chat_token_usage: number
  code_token_usage: number
  total_token_usage: number
  rank: number
}

export interface TokenUsageResponse {
  users: TokenUsageItem[]
  total_chat_tokens: number
  total_code_tokens: number
  total_tokens: number
}

export interface ModuleStatsItem {
  total: number
  today: number
  success: number
  failed: number
  success_rate: number
}

export interface ModuleStatsResponse {
  visual: ModuleStatsItem
  stickman: ModuleStatsItem
  explainer: ModuleStatsItem
  article: ModuleStatsItem
}

export interface AdminPartner {
  id: number
  user_id: number
  display_name: string
  commission_rate_bps: number
  status: string
  referral_code?: string
  created_at?: string | null
}

export interface AdminReferral {
  id: number
  username: string
  phone?: string | null
  partner_id: number
  referral_code?: string | null
  is_approved: boolean
  created_at?: string | null
}

export interface AdminCommission {
  id: number
  partner_id: number
  user_id: number
  order_id?: number | null
  amount: number
  commission_amount: number
  status: string
  source: string
  created_at?: string | null
}

export interface AdminInviteCode {
  id: number
  code: string
  partner_id?: number | null
  plan_key: string
  material_mode: string
  allowed_libraries?: string[]
  status: string
}

export interface StickmanWorkflowMaterialLibrary {
  key: string
  name: string
  description?: string
  is_active?: boolean
  is_visible?: boolean
  sort_order?: number
  base_path?: string
  material_json_path?: string
  image_url?: string | null
  image_count?: number
  material_count?: number
  source?: string
}

export interface StickmanWorkflowMaterialGeneration {
  id: number
  library_key: string
  library_name: string
  target_count: number
  status: string
  progress: number
  message?: string | null
  error?: string | null
  sample_images: string[]
  manifest_path?: string | null
}

export const adminApi = {
  getUsers: (params?: { skip?: number; limit?: number; search?: string }) =>
    api.get<{ users: User[]; total: number }>('/admin/users', { params }),

  getUserCount: () => api.get<{ total: number; active: number }>('/admin/users/count'),

  getUser: (id: number) => api.get<User>(`/admin/users/${id}`),

  getUserDetail: (id: number) => api.get<User>(`/admin/users/${id}/detail`),

  getUserStats: (id: number) => api.get<UserStats>(`/admin/users/${id}/stats`),

  updateUser: (id: number, data: { is_active?: boolean; is_admin?: boolean; frontend_version?: 'legacy' | 'v2' }) =>
    api.put<User>(`/admin/users/${id}`, data),

  batchUpdateFrontendVersion: (userIds: number[], frontendVersion: 'legacy' | 'v2') =>
    api.post<{ message: string; updated_count: number; skipped_admins: number }>(`/admin/users/frontend-version/batch`, {
      user_ids: userIds,
      frontend_version: frontendVersion,
    }),

  updateUserModulePermissions: (id: number, modulePermissions: Record<string, any>) =>
    api.put<{ message: string; module_permissions: Record<string, any> }>(`/admin/users/${id}/module-permissions`, modulePermissions),

  batchUpdateUserModulePermissions: (userIds: number[], modulePermissions: Record<string, any>) =>
    api.post<{ message: string }>(`/admin/users/module-permissions/batch`, { user_ids: userIds, module_permissions: modulePermissions }),

  deleteUser: (id: number) => api.delete(`/admin/users/${id}`),

  toggleUserActive: (id: number) =>
    api.post<{ message: string; is_active: boolean }>(`/admin/users/${id}/toggle-active`),

  getAuditLogs: (params?: { skip?: number; limit?: number; user_id?: number; action?: string }) =>
    api.get<AuditLog[]>('/admin/audit-logs', { params }),

  getSystemStats: () => api.get<SystemStats>('/admin/stats'),

  getInvitationCodes: () => api.get<InvitationCode[]>('/admin/invitation-codes'),

  generateInvitationCodes: (count: number = 1, daysValid?: number) =>
    api.get<{ codes: InvitationCode[] }>('/auth/invitation-codes/generate', { 
      params: { count, days_valid: daysValid } 
    }),

  resetPassword: (userId: number, newPassword: string) =>
    api.post(`/admin/users/${userId}/reset-password`, { password: newPassword }),

  approveUser: (userId: number) =>
    api.post<{ message: string }>(`/admin/users/${userId}/approve`),

  rejectUser: (userId: number) =>
    api.post<{ message: string }>(`/admin/users/${userId}/reject`),

  extendUser: (userId: number, days: number = 30) =>
    api.post<{ message: string; expires_at: string }>(`/admin/users/${userId}/extend`, null, { params: { days } }),

  setVideoLimit: (userId: number, limit: number) =>
    api.post<{ message: string; daily_video_limit: number; module_permissions: Record<string, any> }>(`/admin/users/${userId}/set-video-limit`, null, { params: { limit } }),

  batchSetVisualLimit: (userIds: number[], dailyLimit: number) =>
    api.post<{ message: string; updated_count: number; skipped_admins: number; daily_limit: number }>(`/admin/users/visual-limit/batch`, {
      user_ids: userIds,
      daily_limit: dailyLimit,
    }),

  getStatisticsOverview: (period: string = 'day') =>
    api.get<{
      conversations_count: number
      api_calls_count: number
      videos_count: number
      projects_count: number
      active_users: number
    }>('/admin/statistics/overview', { params: { period } }),

  getStatisticsTrend: (period: string = 'day') =>
    api.get<{
      date: string
      conversations_count: number
      api_calls_count: number
      videos_count: number
      projects_count: number
    }[]>('/admin/statistics/trend', { params: { period } }),

  getTokenUsage: (period: 'day' | 'week' | 'month' = 'day') =>
    api.get<TokenUsageResponse>('/admin/token-usage', { params: { period } }),

  getModuleStats: () => api.get<ModuleStatsResponse>('/admin/module-stats'),

  getPartners: () => api.get<AdminPartner[]>('/admin/partners'),

  createPartner: (data: { user_id: number; display_name: string; commission_rate_bps: number }) =>
    api.post<AdminPartner>('/admin/partners', data),

  getReferrals: (partnerId?: number) =>
    api.get<AdminReferral[]>('/admin/referrals', { params: partnerId ? { partner_id: partnerId } : undefined }),

  getCommissions: (partnerId?: number) =>
    api.get<AdminCommission[]>('/admin/commissions', { params: partnerId ? { partner_id: partnerId } : undefined }),

  createInviteCode: (data: {
    partner_id?: number
    plan_key: string
    material_mode: string
    quota_limit: number
    quota_period: string
    max_video_seconds: number
    max_uses: number
    allowed_libraries?: string[]
  }) => api.post<AdminInviteCode>('/admin/invite-codes', data),

  getStickmanWorkflowMaterialLibraries: () =>
    api.get<{ libraries: StickmanWorkflowMaterialLibrary[] }>('/admin/stickman-workflow/material-libraries'),

  saveStickmanWorkflowMaterialLibraries: (libraries: StickmanWorkflowMaterialLibrary[]) =>
    api.post<{ libraries: StickmanWorkflowMaterialLibrary[] }>('/admin/stickman-workflow/material-libraries', { libraries }),

  uploadStickmanWorkflowMaterialLibraryPackage: (library: StickmanWorkflowMaterialLibrary, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('name', library.name || library.key)
    formData.append('description', library.description || '')
    formData.append('sort_order', String(library.sort_order || 100))
    formData.append('is_active', String(library.is_active !== false))
    formData.append('is_visible', String(library.is_visible !== false))
    return api.post<{
      message: string
      library?: StickmanWorkflowMaterialLibrary
      libraries?: StickmanWorkflowMaterialLibrary[]
      image_url?: string | null
      image_count: number
      material_count: number
    }>(`/admin/stickman-workflow/material-libraries/${library.key}/package`, formData)
  },

  createStickmanWorkflowMaterialSamples: (data: { libraryKey: string; libraryName: string; targetCount: number; referenceImage: File }) => {
    const formData = new FormData()
    formData.append('library_key', data.libraryKey)
    formData.append('library_name', data.libraryName)
    formData.append('target_count', String(data.targetCount))
    formData.append('reference_image', data.referenceImage)
    return api.post<StickmanWorkflowMaterialGeneration>('/admin/stickman-workflow/material-libraries/generations/samples', formData)
  },

  getStickmanWorkflowMaterialGeneration: (generationId: number) =>
    api.get<StickmanWorkflowMaterialGeneration>(`/admin/stickman-workflow/material-libraries/generations/${generationId}`),

  getStickmanWorkflowMaterialGenerationAsset: (assetUrl: string) =>
    api.get<Blob>(assetUrl, { responseType: 'blob' }),

  confirmStickmanWorkflowMaterialGeneration: (generationId: number) =>
    api.post<StickmanWorkflowMaterialGeneration>(`/admin/stickman-workflow/material-libraries/generations/${generationId}/confirm`),

  regenerateStickmanWorkflowMaterialSamples: (generationId: number) =>
    api.post<StickmanWorkflowMaterialGeneration>(`/admin/stickman-workflow/material-libraries/generations/${generationId}/regenerate-samples`),
}

export default api
