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
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminUsers from './pages/admin/AdminUsers'
import AdminLogs from './pages/admin/AdminLogs'
import AdminSettings from './pages/admin/AdminSettings'
import AdminTemplates from './pages/admin/AdminTemplates'
import AdminStatistics from './pages/admin/AdminStatistics'
import { useState, useEffect } from 'react'

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
  const { token, login, logout } = useAuthStore()
  const [validating, setValidating] = useState(true)

  useEffect(() => {
    const validateUser = async () => {
      if (token) {
        try {
          const { data } = await authApi.me()
          login(token, data)
        } catch (error) {
          logout()
        }
      }
      setValidating(false)
    }
    validateUser()
  }, [])

  if (validating && token) {
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
        <Route path="/history" element={<History />} />
        <Route path="/profile" element={<Profile />} />
      </Route>

      <Route element={<AdminRoute><AdminLayout /></AdminRoute>}>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/users" element={<AdminUsers />} />
        <Route path="/admin/logs" element={<AdminLogs />} />
        <Route path="/admin/settings" element={<AdminSettings />} />
        <Route path="/admin/templates" element={<AdminTemplates />} />
        <Route path="/admin/statistics" element={<AdminStatistics />} />
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
