import axios, { AxiosError } from 'axios'
import { useAuthStore } from '@/stores/authStore'

const MAX_RETRIES = 3
const RETRY_DELAY = 1000

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
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
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
    }
    return Promise.reject(error)
  }
)

export async function fetchWithRetry<T>(
  request: () => Promise<{ data: T }>,
  retries = MAX_RETRIES
): Promise<T> {
  let lastError: Error | null = null
  
  for (let i = 0; i < retries; i++) {
    try {
      const response = await request()
      return response.data
    } catch (error: any) {
      lastError = error
      
      if (error.response?.status === 401) {
        throw error
      }
      
      if (i < retries - 1) {
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (i + 1)))
      }
    }
  }
  
  throw lastError || new Error('请求失败')
}

export default api
