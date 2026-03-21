import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, message } from 'antd'
import { UserOutlined, LockOutlined, RocketOutlined } from '@ant-design/icons'
import { authApi } from '@/services/auth'
import { useAuthStore } from '@/stores/authStore'
import { motion } from 'framer-motion'

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      const { data: loginData } = await authApi.login(values)
      const { data: userData } = await authApi.me()
      
      // 检查账号状态（管理员跳过审批检查）
      if (userData.is_expired) {
        message.error('账号已过期，请联系管理员续费')
        return
      }
      if (!userData.is_approved && !userData.is_admin) {
        message.error('账号正在等待审核，请联系管理员')
        return
      }
      
      login(loginData.access_token, { 
        id: userData.id, 
        username: userData.username, 
        email: userData.email, 
        is_admin: userData.is_admin,
        is_approved: userData.is_approved,
        expires_at: userData.expires_at
      })
      message.success('登录成功')
      if (userData.is_admin) {
        navigate('/admin')
      } else {
        navigate('/')
      }
    } catch (error: any) {
      const detail = error.response?.data?.detail
      if (detail === '账号已过期，请联系续费') {
        message.error('账号已过期，请联系管理员续费')
      } else if (detail === '账号正在等待审核，请联系管理员') {
        message.error('账号正在等待审核，请联系管理员')
      } else {
        message.error(detail || '登录失败')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      {/* 背景几何图形 */}
      <div className="auth-background-shapes">
        <div className="auth-shape auth-shape-1" />
        <div className="auth-shape auth-shape-2" />
        <div className="auth-shape auth-shape-3" />
      </div>

      {/* 登录卡片 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md px-4"
      >
        <div className="glass-card p-8">
          {/* Logo 和标题 */}
          <div className="text-center mb-8">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
              className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-[#0066FF] to-[#00CCFF] mb-4"
            >
              <RocketOutlined className="text-3xl text-white" />
            </motion.div>
            <h1 className="text-2xl font-bold text-gray-800 dark:text-white mb-2">
              AI视频 视频平台
            </h1>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              智能生成精彩动画视频
            </p>
          </div>

          {/* 登录表单 */}
          <Form
            onFinish={onFinish}
            layout="vertical"
            size="large"
            className="input-glow"
          >
            <Form.Item
              name="username"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input 
                prefix={<UserOutlined className="text-gray-400" />} 
                placeholder="用户名"
                className="rounded-lg"
              />
            </Form.Item>
            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password 
                prefix={<LockOutlined className="text-gray-400" />} 
                placeholder="密码"
                className="rounded-lg"
              />
            </Form.Item>
            <Form.Item className="mb-4">
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                className="btn-gradient h-12 text-base font-medium rounded-lg"
              >
                登 录
              </Button>
            </Form.Item>
          </Form>

          {/* 注册链接 */}
          <div className="text-center text-gray-500 dark:text-gray-400">
            还没有账号？{' '}
            <Link 
              to="/register" 
              className="text-[#0066FF] hover:text-[#00CCFF] font-medium transition-colors"
            >
              立即注册
            </Link>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
