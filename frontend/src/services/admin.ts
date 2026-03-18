import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth-token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth-token')
      localStorage.removeItem('auth-storage')
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
  created_at: string
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
}

export const adminApi = {
  getUsers: (params?: { skip?: number; limit?: number; search?: string }) =>
    api.get<{ users: User[]; total: number }>('/admin/users', { params }),

  getUserCount: () => api.get<{ total: number; active: number }>('/admin/users/count'),

  getUser: (id: number) => api.get<User>(`/admin/users/${id}`),

  getUserStats: (id: number) => api.get<UserStats>(`/admin/users/${id}/stats`),

  updateUser: (id: number, data: { is_active?: boolean; is_admin?: boolean }) =>
    api.put<User>(`/admin/users/${id}`, data),

  deleteUser: (id: number) => api.delete(`/admin/users/${id}`),

  toggleUserActive: (id: number) =>
    api.post<{ message: string; is_active: boolean }>(`/admin/users/${id}/toggle-active`),

  getAuditLogs: (params?: { skip?: number; limit?: number; user_id?: number; action?: string }) =>
    api.get<AuditLog[]>('/admin/audit-logs', { params }),

  getSystemStats: () => api.get<SystemStats>('/admin/stats'),
}

export default api
