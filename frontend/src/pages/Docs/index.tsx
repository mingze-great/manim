import { Card, Typography, Button, Steps, Divider, Alert } from 'antd'
import { 
  PlayCircleOutlined, MessageOutlined, DownloadOutlined,
  CodeOutlined, ToolOutlined, BulbOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title, Paragraph, Text } = Typography

export default function Docs() {
  const navigate = useNavigate()

  const steps = [
    {
      title: '第一步：输入主题',
      description: '在首页输入你想要制作的视频主题，例如"世界公认十大顶级思维"',
      icon: <PlayCircleOutlined />,
    },
    {
      title: '第二步：AI 生成内容',
      description: '系统会自动生成视频内容要点，包含文字描述和动态效果说明',
      icon: <MessageOutlined />,
    },
    {
      title: '第三步：生成代码',
      description: '点击下方"生成代码"按钮，AI 会根据内容生成 Manim 动画代码',
      icon: <CodeOutlined />,
    },
    {
      title: '第四步：渲染视频',
      description: '点击"开始渲染"按钮，等待视频生成完成，下载到本地',
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
        使用教程
      </Title>

      <Card style={{ marginBottom: '24px' }}>
        <Title level={4}>快速开始</Title>
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
        <Title level={4}><ToolOutlined /> 代码模板选择</Title>
        <Alert 
          type="info" 
          showIcon
          style={{ marginBottom: '16px' }}
          message="不同模板适合不同类型的视频，选择合适的模板可以提高成功率"
        />
        <ul style={{ paddingLeft: '20px' }}>
          <li style={{ marginBottom: '12px', color: '#666' }}>
            <strong>治愈系多维动态引擎（推荐）</strong>
            <br />
            <Text type="secondary">默认模板，适合大多数思维可视化、情绪治愈类视频，稳定性高</Text>
          </li>
          <li style={{ marginBottom: '12px', color: '#666' }}>
            <strong>高定专属模板（千人千面版）</strong>
            <br />
            <Text type="secondary">效果更精美，但容易出错。如果修复2-3次仍失败，建议切换到默认模板</Text>
          </li>
          <li style={{ marginBottom: '12px', color: '#666' }}>
            <strong>数学可视化模板</strong>
            <br />
            <Text type="secondary">专门用于数学、物理概念的可视化，如傅里叶变换、欧拉公式等</Text>
          </li>
        </ul>
      </Card>

      <Card style={{ marginBottom: '24px' }}>
        <Title level={4}><BulbOutlined /> 生成模型选择</Title>
        <Alert 
          type="warning" 
          showIcon
          style={{ marginBottom: '16px' }}
          message="推荐使用 glm-5 进行代码生成，成功率更高"
        />
        <ul style={{ paddingLeft: '20px' }}>
          <li style={{ marginBottom: '12px', color: '#666' }}>
            <strong>glm-5（推荐用于代码生成）</strong>
            <br />
            <Text type="secondary">代码生成质量高，Manim 语法准确，出错率低</Text>
          </li>
          <li style={{ marginBottom: '12px', color: '#666' }}>
            <strong>deepseek-v3.2</strong>
            <br />
            <Text type="secondary">综合能力强，创意性好，但代码可能需要更多修复</Text>
          </li>
        </ul>
        <Divider />
        <Paragraph type="secondary">
          <strong>建议：</strong>如果使用 deepseek-v3.2 生成的代码多次修复失败，可以切换到 glm-5 重新生成
        </Paragraph>
      </Card>

      <Card style={{ marginBottom: '24px' }}>
        <Title level={4}>渲染失败怎么办？</Title>
        <Paragraph type="secondary" style={{ marginBottom: '12px' }}>
          渲染失败时，系统会显示错误信息，你可以：
        </Paragraph>
        <ol style={{ paddingLeft: '20px' }}>
          <li style={{ marginBottom: '8px', color: '#666' }}>
            <strong>点击"自动修复"</strong>：系统会自动分析错误并修复代码（推荐）
          </li>
          <li style={{ marginBottom: '8px', color: '#666' }}>
            <strong>切换模型重新生成</strong>：如果自动修复多次失败，切换到 glm-5 重新生成代码
          </li>
          <li style={{ marginBottom: '8px', color: '#666' }}>
            <strong>切换模板重新生成</strong>：高定模板容易出错，可切换到默认模板
          </li>
        </ol>
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
