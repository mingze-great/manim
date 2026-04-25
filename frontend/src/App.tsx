import { Routes, Route, Navigate } from 'react-router-dom'
import { App as AntApp, Spin } from 'antd'
import { useAuthStore } from './stores/authStore'
import { authApi } from './services/auth'
import MainLayout from './components/Layout/MainLayout'
import AdminLayout from './components/Layout/AdminLayout'
import Landing from './pages/Landing'
import Creator from './pages/Creator'
import History from './pages/History'
import Profile from './pages/Profile'
import Docs from './pages/Docs'
import Login from './pages/Login'
import Register from './pages/Register'
import ProjectChat from './pages/ProjectChat'
import ProjectTask from './pages/ProjectTask'
import StickmanStudio from './pages/StickmanStudio'
import ArticleEntry from './pages/Article/Entry'
import ArticleQuick from './pages/Article/Quick'
import ArticleStudio from './pages/Article/Studio'
import ArticleHistory from './pages/Article/History'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminUsers from './pages/admin/AdminUsers'
import AdminLogs from './pages/admin/AdminLogs'
import AdminSettings from './pages/admin/AdminSettings'
import AdminTemplates from './pages/admin/AdminTemplates'
import AdminStatistics from './pages/admin/AdminStatistics'
import AdminTokenUsage from './pages/admin/AdminTokenUsage'
import AdminArticleCategories from './pages/admin/AdminArticleCategories'
import AdminModuleStats from './pages/admin/AdminModuleStats'
import AdminChatStyles from './pages/admin/AdminChatStyles'
import { useState, useEffect, useRef } from 'react'
import { buildLegacyEntryUrl } from './utils/authSync'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore()
  return token ? <>{children}</> : <Navigate to="/login" />
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, token } = useAuthStore()
  if (!token) return <Navigate to="/login" />
  if (!user?.is_admin) return <Navigate to="/" />
  return <>{children}</>
}

function AppContent() {
  const { token, login, logout, _hasHydrated } = useAuthStore()
  const [validating, setValidating] = useState(true)
  const LEGACY_APP_URL = (import.meta.env.VITE_LEGACY_APP_URL as string | undefined) || `${window.location.protocol}//${window.location.hostname}`
  const authRequestRef = useRef(0)
  const legacyEntryUrl = buildLegacyEntryUrl(LEGACY_APP_URL)

  useEffect(() => {
    if (!_hasHydrated) return
    
    const validateUser = async () => {
      if (token) {
        const currentToken = token
        const requestId = ++authRequestRef.current
        try {
          const { data } = await authApi.me(token)
          if (useAuthStore.getState().token !== currentToken || authRequestRef.current !== requestId) {
            return
          }
          login(token, data)

          if (!data.is_admin && (data.frontend_version || 'legacy') === 'legacy' && LEGACY_APP_URL) {
            window.location.href = legacyEntryUrl
            return
          }
        } catch (error) {
          if (useAuthStore.getState().token === currentToken && authRequestRef.current === requestId) {
            logout()
          }
        }
      }
      setValidating(false)
    }
    validateUser()
  }, [_hasHydrated, token])

  useEffect(() => {
    if (!token || !_hasHydrated) return

    const intervalId = setInterval(async () => {
      const currentToken = token
      try {
        const { data } = await authApi.me(token)
        if (useAuthStore.getState().token !== currentToken) {
          return
        }
        login(token, data)

        if (!data.is_admin && (data.frontend_version || 'legacy') === 'legacy' && LEGACY_APP_URL) {
          window.location.href = legacyEntryUrl
          return
        }
      } catch (error: any) {
        if (error?.response?.status === 401 && useAuthStore.getState().token === currentToken) {
          clearInterval(intervalId)
          logout()
          window.location.href = '/login'
        }
      }
    }, 30000)

    return () => clearInterval(intervalId)
  }, [token, _hasHydrated, logout, login, LEGACY_APP_URL, legacyEntryUrl])

  if (!_hasHydrated || (validating && token)) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/docs" element={<Docs />} />
      
      <Route element={<PrivateRoute><MainLayout /></PrivateRoute>}>
        <Route path="/creator" element={<Creator />} />
        <Route path="/project/:id/chat" element={<ProjectChat />} />
        <Route path="/project/:id/task" element={<ProjectTask />} />
        <Route path="/project/:id/stickman" element={<StickmanStudio />} />
        <Route path="/article" element={<ArticleEntry />} />
        <Route path="/article/quick" element={<ArticleQuick />} />
        <Route path="/article/studio" element={<ArticleStudio />} />
        <Route path="/article/:id" element={<ArticleStudio />} />
        <Route path="/article/history" element={<ArticleHistory />} />
        <Route path="/history" element={<History />} />
        <Route path="/profile" element={<Profile />} />
      </Route>

      <Route element={<AdminRoute><AdminLayout /></AdminRoute>}>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/users" element={<AdminUsers />} />
        <Route path="/admin/logs" element={<AdminLogs />} />
        <Route path="/admin/settings" element={<AdminSettings />} />
        <Route path="/admin/templates" element={<AdminTemplates />} />
        <Route path="/admin/chat-styles" element={<AdminChatStyles />} />
        <Route path="/admin/article-categories" element={<AdminArticleCategories />} />
        <Route path="/admin/module-stats" element={<AdminModuleStats />} />
        <Route path="/admin/statistics" element={<AdminStatistics />} />
        <Route path="/admin/token-usage" element={<AdminTokenUsage />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <AntApp>
      <AppContent />
    </AntApp>
  )
}
