import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import AuthLayout from './components/Layout/AuthLayout'
import MainLayout from './components/Layout/MainLayout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import ProjectChat from './pages/ProjectChat'
import ProjectTask from './pages/ProjectTask'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore()
  return token ? <>{children}</> : <Navigate to="/login" />
}

function App() {
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>
      
      <Route element={<PrivateRoute><MainLayout /></PrivateRoute>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/project/:id/chat" element={<ProjectChat />} />
        <Route path="/project/:id/task" element={<ProjectTask />} />
      </Route>
    </Routes>
  )
}

export default App
