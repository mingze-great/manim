import { useState, useEffect } from 'react'
import { Card, Button, Space, Typography, Tag, message } from 'antd'
import { articleApi, Category } from '@/services/article'

const { Text } = Typography

interface CategorySelectorProps {
  value?: string
  onChange?: (category: string) => void
}

export default function CategorySelector({ value, onChange }: CategorySelectorProps) {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadCategories()
  }, [])

  const loadCategories = async () => {
    setLoading(true)
    try {
      const { data } = await articleApi.getCategories()
      setCategories(data)
    } catch (error) {
      console.error('Failed to load categories:', error)
      message.error('加载创作方向失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ marginBottom: '16px' }}>
      <Text strong style={{ display: 'block', marginBottom: '12px' }}>
        选择创作方向：
      </Text>
      <Space wrap size="middle">
        {categories.map(cat => (
          <Button
            key={cat.name}
            type={value === cat.name ? 'primary' : 'default'}
            onClick={() => onChange?.(cat.name)}
            size="large"
            style={{ height: 'auto', padding: '8px 16px' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '18px' }}>{cat.icon}</span>
              <span>{cat.name}</span>
            </div>
          </Button>
        ))}
      </Space>
      
      {value && categories.find(c => c.name === value)?.example_topics && (
        <Card 
          size="small" 
          style={{ marginTop: '12px', background: '#fafafa' }}
          bodyStyle={{ padding: '12px' }}
        >
          <Text type="secondary" style={{ fontSize: '12px' }}>示例主题：</Text>
          <div style={{ marginTop: '8px' }}>
            {categories.find(c => c.name === value)?.example_topics.map((topic, idx) => (
              <Tag key={idx} style={{ marginBottom: '4px' }}>{topic}</Tag>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}