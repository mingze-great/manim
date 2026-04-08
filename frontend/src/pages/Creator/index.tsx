import { useState } from 'react'
import { Button, Input, message, Divider } from 'antd'
import { RocketOutlined, BulbOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { projectApi } from '@/services/project'
import TopicCategorySelector from './components/TopicCategorySelector'
import TopicExamples from './components/TopicExamples'
import { VideoTopicCategory } from '@/services/videoTopic'
import './Creator.css'

const { TextArea } = Input

export default function Creator() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<VideoTopicCategory | null>(null)
  const [customTopic, setCustomTopic] = useState('')

  const handleCategorySelect = (category: VideoTopicCategory) => {
    setSelectedCategory(category)
  }

  const handleTopicSelect = async (topic: string) => {
    setLoading(true)
    try {
      const { data } = await projectApi.create({ 
        title: `视频创作-${topic}`,
        theme: topic,
        category: selectedCategory?.name
      })
      message.success('创建成功，进入对话')
      navigate(`/project/${data.id}/chat`)
    } catch (error: any) {
      const detail = error.response?.data?.detail || error.message || '创建失败'
      message.error(detail)
    } finally {
      setLoading(false)
    }
  }

  const handleCustomCreate = async () => {
    if (!customTopic.trim()) {
      message.warning('请输入主题')
      return
    }
    await handleTopicSelect(customTopic)
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
            选择热门方向或输入主题，智能生成精彩的动画视频
          </p>
        </div>
      </div>

      <div className="creator-container">
        {selectedCategory ? (
          <div className="max-w-2xl mx-auto">
            <Button 
              onClick={() => setSelectedCategory(null)} 
              className="mb-4"
            >
              返回选择方向
            </Button>
            <TopicExamples 
              category={selectedCategory}
              onSelect={handleTopicSelect}
            />
          </div>
        ) : (
          <>
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-4">
                <BulbOutlined className="text-xl text-indigo-500" />
                <span className="text-lg font-medium">选择热门方向</span>
              </div>
              <TopicCategorySelector onSelect={handleCategorySelect} />
            </div>

            <Divider>或直接输入主题</Divider>

            <div className="max-w-xl mx-auto">
              <TextArea
                value={customTopic}
                onChange={(e) => setCustomTopic(e.target.value)}
                placeholder={`输入你的视频主题...

例如：
• 世界十大顶级思维：刻意练习、复利思维、终身学习...
• 勾股定理的证明过程
• 人生三件事：运动、阅读、赚钱`}
                rows={4}
                className="theme-input mb-3"
              />

              <Button 
                type="primary" 
                icon={<RocketOutlined />}
                onClick={handleCustomCreate}
                loading={loading}
                size="large"
                block
                disabled={!customTopic.trim()}
                className="btn-gradient"
              >
                开始创作
              </Button>
            </div>

            <div className="usage-tips mt-6">
              <h3>
                <BulbOutlined className="mr-2" />
                使用提示
              </h3>
              <ul>
                <li>选择热门方向，直接使用爆款主题示例</li>
                <li>或让AI生成更多相关主题</li>
                <li>智能助手会自动规划每个要点的内容和动态效果</li>
                <li>你可以审核调整内容，直到满意</li>
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  )
}