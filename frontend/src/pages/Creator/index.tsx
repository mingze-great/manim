import { useState } from 'react'
import { Card, Button, Input, message } from 'antd'
import { RocketOutlined, BulbOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { projectApi } from '@/services/project'
import './Creator.css'

const { TextArea } = Input

export default function Creator() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [theme, setTheme] = useState('')

  const handleQuickStart = async () => {
    if (!theme.trim()) {
      message.warning('请输入视频主题')
      return
    }

    setLoading(true)
    try {
      const { data: project } = await projectApi.create({ 
        title: `视频创作-${Date.now()}`,
        theme: theme 
      })
      
      navigate(`/project/${project.id}/chat`)
    } catch (error: any) {
      const detail = error.response?.data?.detail || error.message || '创建失败'
      message.error(detail)
      console.error('创建项目失败:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="creator-page">
      <div className="creator-hero">
        <div className="hero-content">
          <h1 className="hero-title">
            <RocketOutlined className="mr-3" />
            视频创作助手
          </h1>
          <p className="hero-subtitle">
            输入你的主题，智能生成精彩的动画视频
          </p>
        </div>
      </div>

      <div className="creator-container">
        <Card className="quick-create-card">
          <div className="quick-create-content">
            <div className="flex items-center gap-2 mb-4">
              <BulbOutlined className="text-xl text-indigo-500" />
              <span className="text-lg font-medium">开始创作</span>
            </div>
            
            <TextArea
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              placeholder={`输入你的视频主题...

例如：
• 世界十大顶级思维：刻意练习、复利思维、终身学习...
• 勾股定理的证明过程
• 人生三件事：运动、阅读、赚钱`}
              rows={6}
              className="theme-input mb-4"
            />

            <Button 
              type="primary" 
              icon={<RocketOutlined />}
              onClick={handleQuickStart}
              loading={loading}
              size="large"
              block
              className="btn-gradient"
            >
              开始创作
            </Button>

            <p className="text-gray-500 text-sm text-center mt-4">
              智能助手会根据你的主题生成内容，询问是否满意后可随时调整
            </p>
          </div>
        </Card>

        <div className="usage-tips">
          <h3>
            <BulbOutlined className="mr-2" />
            使用提示
          </h3>
          <ul>
            <li>直接输入你想要的视频主题内容</li>
            <li>智能助手会自动规划每个要点的内容和动态效果</li>
            <li>你可以审核调整内容，直到满意</li>
            <li>满意后自动生成脚本，一键生成视频</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
