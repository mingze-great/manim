import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

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
  is_active: boolean
  is_admin: boolean
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
  article: ModuleStatsItem
}

export const adminApi = {
  getUsers: (params?: { skip?: number; limit?: number; search?: string }) =>
    api.get<{ users: User[]; total: number }>('/admin/users', { params }),

  getUserCount: () => api.get<{ total: number; active: number }>('/admin/users/count'),

  getUser: (id: number) => api.get<User>(`/admin/users/${id}`),

  getUserDetail: (id: number) => api.get<User>(`/admin/users/${id}/detail`),

  getUserStats: (id: number) => api.get<UserStats>(`/admin/users/${id}/stats`),

  updateUser: (id: number, data: { is_active?: boolean; is_admin?: boolean }) =>
    api.put<User>(`/admin/users/${id}`, data),

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
    api.post<{ message: string }>(`/admin/users/${userId}/set-video-limit`, null, { params: { limit } }),

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
}

export default api
