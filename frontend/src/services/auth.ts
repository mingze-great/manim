import axios from 'axios'

const API_BASE = 'http://localhost:8000/api'

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
    // 保存token到localStorage
    localStorage.setItem('auth-token', response.data.access_token)
    return response
  },
  register: (data: RegisterRequest) => axios.post(`${API_BASE}/auth/register`, data),
  me: () => {
    const token = localStorage.getItem('auth-token')
    return axios.get(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    })
  },
}
