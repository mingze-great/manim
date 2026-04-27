import { Card, Button, message } from 'antd'
import { VideoCameraOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

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
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/creator')}>返回创作首页</Button>
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center gap-2 text-orange-500 text-lg font-medium">
          <VideoCameraOutlined />
          <span>视频讲解模块选择</span>
        </div>
        <h1 className="text-3xl font-bold">选择视频讲解版本</h1>
        <p className="text-gray-500">先选择模块，再进入对应的视频讲解流程。标准讲解、增强讲解和讲解型视频会长期并存。</p>
      </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {variantCards.map((item) => (
          <Card key={item.value} hoverable onClick={() => handleEnter(item.value)} className={item.value === 'explainer' && !explainerEnabled ? 'opacity-60' : ''}>
            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-semibold mb-2">{item.title}</h2>
                <p className="text-gray-500 mb-0">{item.description}</p>
              </div>
              <Button type="primary" block disabled={item.value === 'explainer' && !explainerEnabled} onClick={(event) => {
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
  )
}
