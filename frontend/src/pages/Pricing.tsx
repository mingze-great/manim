import { Card, Typography, Button, Tag } from 'antd'
import { CheckOutlined, RocketOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

export default function Pricing() {
  const features = [
    'AI 内容生成',
    '视频渲染服务',
    '最多3个项目保存',
    '项目下载到本地',
  ]

  return (
    <div style={{ padding: '60px 20px', maxWidth: '800px', margin: '0 auto' }}>
      <Title level={2} style={{ textAlign: 'center', marginBottom: '40px' }}>
        套餐服务
      </Title>

      <Card 
        style={{ maxWidth: '400px', margin: '0 auto', textAlign: 'center' }}
        className="shadow-lg"
      >
        <div style={{ marginBottom: '16px' }}>
          <Tag color="red" style={{ fontSize: '14px', padding: '4px 12px' }}>
            限时优惠
          </Tag>
        </div>

        <Title level={3}>月套餐</Title>

        <div style={{ margin: '24px 0' }}>
          <Text delete style={{ fontSize: '20px', color: '#999', marginRight: '12px' }}>
            ¥199
          </Text>
          <Title level={2} style={{ color: '#f5222d', margin: 0, display: 'inline' }}>
            ¥149
          </Title>
          <Text type="secondary"> / 月</Text>
        </div>

        <Text type="secondary" style={{ display: 'block', marginBottom: '24px' }}>
          前30位用户专享价
        </Text>

        <ul style={{ textAlign: 'left', paddingLeft: '24px', marginBottom: '24px' }}>
          {features.map((f, i) => (
            <li key={i} style={{ marginBottom: '8px', color: '#666' }}>
              <CheckOutlined style={{ color: '#52c41a', marginRight: '8px' }} />
              {f}
            </li>
          ))}
        </ul>

        <Button 
          type="primary" 
          size="large" 
          icon={<RocketOutlined />}
          block
          className="btn-gradient"
          onClick={() => {
            alert('请联系管理员开通套餐')
          }}
        >
          联系管理员开通
        </Button>
      </Card>

      <div style={{ marginTop: '40px', textAlign: 'center' }}>
        <Text type="secondary">
          更多问题请联系管理员咨询
        </Text>
      </div>
    </div>
  )
}
