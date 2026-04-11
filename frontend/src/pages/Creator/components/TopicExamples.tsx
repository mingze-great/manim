import { useMemo, useState } from 'react'
import { Button, Input, message } from 'antd'
import { BulbOutlined } from '@ant-design/icons'
import { videoTopicApi } from '@/services/videoTopic'

type TopicLikeCategory = {
  name: string
  icon: string
  example_topics: string[]
}

interface Props {
  category: TopicLikeCategory
  onSelect: (topic: string) => void
  generateTopics?: (category: string, keyword?: string) => Promise<{ data: { topics: string[] } }>
  titlePrefix?: string
}

export default function TopicExamples({ category, onSelect, generateTopics, titlePrefix = '热门主题' }: Props) {
  const [aiTopics, setAiTopics] = useState<string[]>([])
  const [generating, setGenerating] = useState(false)
  const [keyword, setKeyword] = useState('')

  const generator = useMemo(() => generateTopics || videoTopicApi.generateTopics, [generateTopics])

  const handleAiGenerate = async () => {
    setGenerating(true)
    try {
      const { data } = await generator(category.name, keyword)
      setAiTopics(data.topics)
    } catch (error) {
      message.error('生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const allTopics = [...category.example_topics, ...aiTopics]

  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <h3 className="text-lg font-medium mb-3 flex items-center gap-2">
        <span className="text-2xl">{category.icon}</span>
        {category.name} - {titlePrefix}
      </h3>

      <div className="mb-3">
        <Input 
          placeholder="输入关键词（可选），AI会生成相关主题"
          value={keyword}
          onChange={e => setKeyword(e.target.value)}
          className="mb-2"
        />
      </div>

      <div className="space-y-2 max-h-80 overflow-y-auto">
        {allTopics.map((topic, index) => (
          <div 
            key={index}
            className="p-3 rounded border border-gray-200 hover:border-indigo-500 hover:bg-indigo-50 cursor-pointer transition-all"
            onClick={() => onSelect(topic)}
          >
            {topic}
          </div>
        ))}

        <Button 
          icon={<BulbOutlined />}
          onClick={handleAiGenerate}
          loading={generating}
          block
          type="dashed"
        >
          AI生成更多主题
        </Button>
      </div>
    </div>
  )
}
