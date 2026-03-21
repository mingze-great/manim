import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, message } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined, RocketOutlined } from '@ant-design/icons'
import { authApi } from '@/services/auth'
import { motion } from 'framer-motion'

export default function Register() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: { username: string; email: string; password: string }) => {
    setLoading(true)
    try {
      await authApi.register(values)
      message.success('注册成功，请等待管理员审核后登录')
      navigate('/login')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '注册失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-background-shapes">
        <div className="auth-shape auth-shape-1" />
        <div className="auth-shape auth-shape-2" />
        <div className="auth-shape auth-shape-3" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md px-4"
      >
        <div className="glass-card p-8">
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
              加入 AI视频 平台
            </h1>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              创建账号，开启动画创作之旅
            </p>
          </div>

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
              name="email"
              rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '请输入有效的邮箱地址' },
              ]}
            >
              <Input 
                prefix={<MailOutlined className="text-gray-400" />} 
                placeholder="邮箱"
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
                注 册
              </Button>
            </Form.Item>
          </Form>

          <div className="text-center text-gray-500 dark:text-gray-400">
            已有账号？{' '}
            <Link 
              to="/login" 
              className="text-[#0066FF] hover:text-[#00CCFF] font-medium transition-colors"
            >
              立即登录
            </Link>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
