import { Button, Card, Space, Typography } from 'antd'
import { RocketOutlined, ToolOutlined } from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'

const { Title, Text } = Typography

export default function ArticleEntry() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const topic = searchParams.get('topic') || ''
  const category = searchParams.get('category') || '生活'
  const query = `?topic=${encodeURIComponent(topic)}&category=${encodeURIComponent(category)}`

  return (
    <div style={{ maxWidth: 1120, margin: '0 auto', padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ padding: 28, borderRadius: 24, background: 'linear-gradient(135deg, #0f2e4f 0%, #1f5f7d 50%, #f1b86d 100%)', color: '#fff' }}>
          <Title level={2}>公众号文章创作</Title>
          <Text style={{ color: 'rgba(255,255,255,0.88)' }}>根据你的熟练度选择轻量版或专业版。轻量版适合快速出稿，专业版适合深度打磨文案、配图与排版。</Text>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
          <Card style={{ borderRadius: 20, border: '1px solid #f3d5a8', background: 'linear-gradient(180deg, #fff9ef 0%, #ffffff 100%)' }}>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <RocketOutlined style={{ fontSize: 30, color: '#d97706' }} />
              <Title level={4} style={{ margin: 0 }}>轻量版</Title>
              <Text type="secondary">先出文案草稿，再确认图片位置和手机预览。适合普通用户快速完成公众号内容。</Text>
              <Button type="primary" onClick={() => navigate(`/article/quick${query}`)}>进入轻量版</Button>
            </Space>
          </Card>
          <Card style={{ borderRadius: 20, border: '1px solid #d3e6ef', background: 'linear-gradient(180deg, #f8fcff 0%, #ffffff 100%)' }}>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <ToolOutlined style={{ fontSize: 30, color: '#2563eb' }} />
              <Title level={4} style={{ margin: 0 }}>专业版</Title>
              <Text type="secondary">适合运营和编辑，支持大纲、正文、配图、排版的分步精修与局部 AI 重写。</Text>
              <Button onClick={() => navigate(`/article/studio${query}`)}>进入专业版</Button>
            </Space>
          </Card>
        </div>
      </Space>
    </div>
  )
}
