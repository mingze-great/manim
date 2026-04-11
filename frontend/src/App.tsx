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
import { useState, useEffect } from 'react'
import { startStatusCheck } from './stores/authStore'

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

  useEffect(() => {
    if (!_hasHydrated) return
    
    const validateUser = async () => {
      if (token) {
        try {
          const { data } = await authApi.me(token)
          login(token, data)
        } catch (error) {
          logout()
        }
      }
      setValidating(false)
    }
    validateUser()
  }, [_hasHydrated, token])

  useEffect(() => {
    if (!token || !_hasHydrated) return
    
    const cleanup = startStatusCheck(() => {
      logout()
      window.location.href = '/login'
    })
    
    return cleanup
  }, [token, _hasHydrated, logout])

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
