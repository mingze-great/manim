import { Card, Button, message } from 'antd'
import { VideoCameraOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import './Creator/Creator.css'

const variantCards = [
  {
    value: 'legacy',
    title: '标准讲解',
    description: '保留稳定直接的视频讲解流程，适合延续当前使用习惯。',
  },
  {
    value: 'v2',
    title: '增强讲解',
    description: '进入增强版视频讲解流程，后续新增优化与能力都会优先落在这里。',
  },
  {
    value: 'explainer',
    title: '讲解型视频',
    description: '使用独立讲解型视频工作流，围绕分镜文案生成场景图、字幕、配音和成片。',
  },
]

export default function StickmanModuleEntry() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const permissions = user?.module_permissions || {}
  const explainerEnabled = user?.is_admin || permissions.explainer?.enabled !== false

  const handleEnter = (value: string) => {
    if (value === 'explainer') {
      if (!explainerEnabled) {
        message.warning('当前账号未开通讲解型视频模块，请联系管理员开通')
        return
      }
      navigate('/creator/explainer')
      return
    }
    navigate(`/creator/stickman/${value}`)
  }

  return (
    <div className="creator-page">
      <div className="creator-hero creator-hero-sunrise">
        <div className="hero-content">
          <h1 className="hero-title">
            <VideoCameraOutlined className="mr-3" />
            视频讲解模块选择
          </h1>
          <p className="hero-subtitle">选择标准讲解、增强讲解或讲解型视频，进入各自独立工作流。</p>
        </div>
      </div>

      <div className="creator-container">
        <div className="flex gap-3 flex-wrap mb-6">
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/creator')}>返回创作首页</Button>
        </div>

        <div className="module-card-grid">
          {variantCards.map((item) => (
            <Card key={item.value} hoverable onClick={() => handleEnter(item.value)} className={`module-card ${item.value === 'explainer' && !explainerEnabled ? 'module-card-disabled' : ''}`}>
              <div className="space-y-4">
                <div className="module-card-icon module-card-icon-orange">
                  <VideoCameraOutlined />
                </div>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.description}</p>
                </div>
                <Button type="primary" block className="btn-gradient-warm" disabled={item.value === 'explainer' && !explainerEnabled} onClick={(event) => {
                  event.stopPropagation()
                  handleEnter(item.value)
                }}>
                  进入{item.title}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
