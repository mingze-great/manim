import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: number
  username: string
  email: string
  is_admin?: boolean
  is_approved?: boolean
  expires_at?: string | null
  is_expired?: boolean
  can_use?: boolean
}

interface AuthState {
  token: string | null
  user: User | null
  lastActivity: number
  _hasHydrated: boolean
  isAuthenticated: () => boolean
  login: (token: string, user: User) => void
  logout: () => void
  setUser: (user: User) => void
  updateActivity: () => void
  checkExpiration: () => boolean
  setHasHydrated: (state: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      lastActivity: Date.now(),
      _hasHydrated: false,
      isAuthenticated: () => !!get().token,
      login: (token, user) => set({ token, user, lastActivity: Date.now() }),
      logout: () => set({ token: null, user: null, lastActivity: Date.now() }),
      setUser: (user) => set({ user }),
      updateActivity: () => set({ lastActivity: Date.now() }),
      checkExpiration: () => {
        const { user } = get()
        if (user?.is_expired) {
          get().logout()
          return false
        }
        return true
      },
      setHasHydrated: (state: boolean) => set({ _hasHydrated: state }),
    }),
    {
      name: 'auth-storage',
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      }
    }
  )
)

const INACTIVITY_TIMEOUT = 10 * 60 * 1000

export const startInactivityCheck = (onLogout: () => void) => {
  let timeoutId: ReturnType<typeof setTimeout>
  
  const resetTimer = () => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => {
      const { lastActivity, token } = useAuthStore.getState()
      if (token && Date.now() - lastActivity > INACTIVITY_TIMEOUT) {
        onLogout()
      } else if (token) {
        resetTimer()
      }
    }, INACTIVITY_TIMEOUT)
  }
  
  const events = ['mousedown', 'keydown', 'scroll', 'touchstart']
  events.forEach(event => {
    window.addEventListener(event, () => {
      useAuthStore.getState().updateActivity()
      resetTimer()
    })
  })
  
  resetTimer()
}

const STATUS_CHECK_INTERVAL = 30 * 1000

export const startStatusCheck = (onForceLogout: () => void) => {
  let intervalId: ReturnType<typeof setInterval>
  
  const checkStatus = async () => {
    const { token, user } = useAuthStore.getState()
    if (!token || !user) return
    
    try {
      const response = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (response.status === 401) {
        clearInterval(intervalId)
        onForceLogout()
      }
    } catch (error) {
      // 网络错误不处理，继续检查
    }
  }
  
  intervalId = setInterval(checkStatus, STATUS_CHECK_INTERVAL)
  
  return () => clearInterval(intervalId)
}
