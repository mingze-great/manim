import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, message } from 'antd'
import { UserOutlined, LockOutlined, PhoneOutlined, RocketOutlined, SyncOutlined } from '@ant-design/icons'
import { authApi } from '@/services/auth'
import { motion } from 'framer-motion'

export default function Register() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const generateUsername = () => `创作者${Math.random().toString(36).slice(2, 8)}`

  const onFinish = async (values: { username?: string; phone: string; password: string }) => {
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
              加入思维可视化平台
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
              initialValue={generateUsername()}
            >
              <Input 
                prefix={<UserOutlined className="text-gray-400" />} 
                placeholder="用户名（可修改）"
                className="rounded-lg"
                addonAfter={
                  <Button
                    type="link"
                    size="small"
                    icon={<SyncOutlined />}
                    onClick={() => form.setFieldValue('username', generateUsername())}
                  >
                    随机
                  </Button>
                }
              />
            </Form.Item>
            <Form.Item
              name="phone"
              rules={[
                { required: true, message: '请输入手机号' },
                { pattern: /^1\d{10}$/, message: '请输入有效的11位手机号' },
              ]}
            >
              <Input 
                prefix={<PhoneOutlined className="text-gray-400" />} 
                placeholder="手机号"
                className="rounded-lg"
              />
            </Form.Item>
            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 8, message: '密码至少8位' },
                { pattern: /^(?=.*[A-Za-z])(?=.*\d).+$/, message: '密码必须包含字母和数字' },
              ]}
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
            <p className="text-xs mb-2">注册后需管理员审核才能使用</p>
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
