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
  isAuthenticated: () => boolean
  login: (token: string, user: User) => void
  logout: () => void
  setUser: (user: User) => void
  updateActivity: () => void
  checkExpiration: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      lastActivity: Date.now(),
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
    }),
    {
      name: 'auth-storage',
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
