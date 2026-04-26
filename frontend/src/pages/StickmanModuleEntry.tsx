import { Card, Button } from 'antd'
import { VideoCameraOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const variantCards = [
  {
    value: 'legacy',
    title: '经典版火柴人',
    description: '保持基线分支的原有火柴人创作流程，适合继续沿用已有制作习惯。',
  },
  {
    value: 'v2',
    title: '优化版火柴人',
    description: '进入新版火柴人工作流，后续新增优化与能力都落在这个模块。',
  },
]

export default function StickmanModuleEntry() {
  const navigate = useNavigate()

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/creator')}>返回创作首页</Button>
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center gap-2 text-orange-500 text-lg font-medium">
          <VideoCameraOutlined />
          <span>火柴人模块选择</span>
        </div>
        <h1 className="text-3xl font-bold">选择火柴人版本</h1>
        <p className="text-gray-500">先进入版本选择页，再进入对应的火柴人制作流程。经典版和优化版会长期并存。</p>
      </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {variantCards.map((item) => (
          <Card key={item.value} hoverable onClick={() => navigate(`/creator/stickman/${item.value}`)}>
            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-semibold mb-2">{item.title}</h2>
                <p className="text-gray-500 mb-0">{item.description}</p>
              </div>
              <Button type="primary" block onClick={(event) => {
                event.stopPropagation()
                navigate(`/creator/stickman/${item.value}`)
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
