import { Routes, Route, Navigate } from 'react-router-dom'
import { App as AntApp } from 'antd'
import { useAuthStore } from './stores/authStore'
import MainLayout from './components/Layout/MainLayout'
import Landing from './pages/Landing'
import Creator from './pages/Creator'
import History from './pages/History'
import Pricing from './pages/Pricing'
import Profile from './pages/Profile'
import Login from './pages/Login'
import Register from './pages/Register'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore()
  return token ? <>{children}</> : <Navigate to="/login" />
}

export default function App() {
  return (
    <AntApp>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        
        <Route element={<PrivateRoute><MainLayout /></PrivateRoute>}>
          <Route path="/creator" element={<Creator />} />
          <Route path="/creator/:projectId" element={<Creator />} />
          <Route path="/history" element={<History />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
      </Routes>
    </AntApp>
  )
}
