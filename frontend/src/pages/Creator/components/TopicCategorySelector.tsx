import { useState, useEffect } from 'react'
import { videoTopicApi, VideoTopicCategory } from '@/services/videoTopic'

interface Props {
  onSelect: (category: VideoTopicCategory) => void
}

export default function TopicCategorySelector({ onSelect }: Props) {
  const [categories, setCategories] = useState<VideoTopicCategory[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadCategories()
  }, [])

  const loadCategories = async () => {
    try {
      const { data } = await videoTopicApi.getCategories()
      setCategories(data)
    } catch (error) {
      console.error('Failed to load categories:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-4">加载中...</div>
  }

  return (
    <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
      {categories.map(cat => (
        <div 
          key={cat.id}
          className="category-card p-4 rounded-lg border-2 border-gray-200 cursor-pointer hover:border-indigo-500 hover:shadow-md transition-all"
          onClick={() => onSelect(cat)}
        >
          <div className="text-3xl text-center mb-2">{cat.icon}</div>
          <div className="text-sm font-medium text-center">{cat.name}</div>
          {cat.description && (
            <div className="text-xs text-gray-500 text-center mt-1">{cat.description}</div>
          )}
        </div>
      ))}
    </div>
  )
}