import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
}

export const authApi = {
  login: async (data: LoginRequest) => {
    const params = new URLSearchParams()
    params.append('username', data.username)
    params.append('password', data.password)
    const response = await axios.post(`${API_BASE}/auth/login`, params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    return response
  },
  register: (data: RegisterRequest) => axios.post(`${API_BASE}/auth/register`, data),
  me: () => {
    const stored = localStorage.getItem('auth-storage')
    let token = null
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        token = parsed.state?.token
      } catch (e) {}
    }
    return axios.get(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    })
  },
}
