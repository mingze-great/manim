import { Card, Typography, Button, Steps } from 'antd'
import { 
  PlayCircleOutlined, MessageOutlined, VideoCameraOutlined, DownloadOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title, Paragraph } = Typography

export default function Docs() {
  const navigate = useNavigate()

  const steps = [
    {
      title: '输入主题',
      description: '在首页输入你想要制作的视频主题',
      icon: <PlayCircleOutlined />,
    },
    {
      title: '智能生成内容',
      description: '根据你的主题生成内容要点和动态描述',
      icon: <MessageOutlined />,
    },
    {
      title: '审核调整',
      description: '查看生成的内容，有需要可以调整修改',
      icon: <VideoCameraOutlined />,
    },
    {
      title: '生成视频',
      description: '满意后点击生成视频，下载到本地',
      icon: <DownloadOutlined />,
    },
  ]

  const tips = [
    '主题越详细，生成的内容越准确',
    '可以多次调整内容直到满意',
    '视频生成后可随时重新生成',
    '注意：最多保存3个作品，请及时下载',
  ]

  return (
    <div className="docs-page" style={{ padding: '40px 20px', maxWidth: '900px', margin: '0 auto' }}>
      <Title level={2} style={{ textAlign: 'center', marginBottom: '40px' }}>
        操作指南
      </Title>

      <Card style={{ marginBottom: '24px' }}>
        <Title level={4}>使用流程</Title>
        <Paragraph type="secondary" style={{ marginBottom: '24px' }}>
          只需4步，即可完成你的视频创作
        </Paragraph>
        <Steps current={4} items={steps} direction="vertical" />
        <Button 
          type="primary" 
          size="large" 
          icon={<PlayCircleOutlined />}
          onClick={() => navigate('/creator')}
          style={{ marginTop: '24px' }}
        >
          开始创作
        </Button>
      </Card>

      <Card style={{ marginBottom: '24px' }}>
        <Title level={4}>使用提示</Title>
        <ul style={{ paddingLeft: '20px' }}>
          {tips.map((tip, i) => (
            <li key={i} style={{ marginBottom: '8px', color: '#666' }}>
              {tip}
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <Title level={4}>注意事项</Title>
        <ul style={{ paddingLeft: '20px' }}>
          <li style={{ marginBottom: '8px', color: '#666' }}>
            免费用户最多保存3个作品，生成视频后请及时下载到本地
          </li>
          <li style={{ marginBottom: '8px', color: '#666' }}>
            账号有使用期限，过期后请联系管理员续费
          </li>
          <li style={{ marginBottom: '8px', color: '#666' }}>
            10分钟无操作会自动退出登录
          </li>
        </ul>
      </Card>
    </div>
  )
}
