import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeMode = 'light' | 'dark'

interface ThemeState {
  mode: ThemeMode
  toggleTheme: () => void
  setTheme: (mode: ThemeMode) => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      mode: 'light',
      toggleTheme: () => set((state) => {
        const newMode = state.mode === 'light' ? 'dark' : 'light'
        return { mode: newMode }
      }),
      setTheme: (mode) => set({ mode }),
    }),
    {
      name: 'theme-storage',
    }
  )
)

// Ant Design 亮色主题配置
export const lightTheme = {
  token: {
    colorPrimary: '#0066FF',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#0066FF',
    borderRadius: 8,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  components: {
    Button: {
      controlHeight: 40,
      paddingContentHorizontal: 20,
    },
    Card: {
      borderRadiusLG: 12,
    },
    Input: {
      controlHeight: 44,
      borderRadius: 8,
    },
  },
}

// Ant Design 暗色主题配置
export const darkTheme = {
  token: {
    colorPrimary: '#00CCFF',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#00CCFF',
    borderRadius: 8,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    colorBgContainer: '#1f1f1f',
    colorBgElevated: '#2a2a2a',
    colorBgLayout: '#141414',
    colorText: '#e8e8e8',
    colorTextSecondary: '#a6a6a6',
    colorBorder: '#424242',
    colorBorderSecondary: '#303030',
  },
  components: {
    Button: {
      controlHeight: 40,
      paddingContentHorizontal: 20,
    },
    Card: {
      borderRadiusLG: 12,
      colorBgContainer: '#1f1f1f',
    },
    Input: {
      controlHeight: 44,
      borderRadius: 8,
      colorBgContainer: '#1f1f1f',
    },
  },
}
