import axios from 'axios'
import { getApiBase } from './api'

const API_BASE = getApiBase()

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  phone: string
  password: string
  referral_code?: string
  referralCode?: string
  invite_code?: string
  inviteCode?: string
}

export interface ChangePasswordRequest {
  old_password: string
  new_password: string
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
  me: (token: string) => {
    return axios.get(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    })
  },
  changePassword: (data: ChangePasswordRequest, token: string) => {
    return axios.post(`${API_BASE}/auth/change-password`, data, {
      headers: { Authorization: `Bearer ${token}` }
    })
  },
}
