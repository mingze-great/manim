import { Alert, Button, Card, Col, Collapse, Divider, Row, Steps, Tag, Typography } from 'antd'
import {
  BulbOutlined,
  FileTextOutlined,
  HighlightOutlined,
  PlayCircleOutlined,
  SafetyOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title, Paragraph } = Typography

export default function Docs() {
  const navigate = useNavigate()

  const visualSteps = [
    { title: '进入开始创作', description: '在开始创作里选择思维可视化模块。普通用户默认开放此模块。' },
    { title: '选择主题', description: '可以选择热门方向、热门主题，也可以直接输入自己的主题。' },
    { title: '对话打磨', description: '进入对话页后补充要求，系统会流式输出文案内容。' },
    { title: '生成脚本', description: '确认后生成思维可视化脚本。' },
    { title: '渲染视频', description: '在任务页查看进度并下载最终视频。' },
  ]

  const stickmanSteps = [
    { title: '进入开始创作', description: '在开始创作里切换到火柴人视频模块。未开通时仍可浏览，但创建时会提示未开通。' },
    { title: '选择主题与音色', description: '支持热门主题、AI 选题、音色选择、语速选择、录音或上传音频。' },
    { title: '一键或分步', description: '可选择一键生成，也可进入分步创作：脚本、图片、配音、合成。' },
    { title: '试听与参考图', description: '支持试听音色，也可上传风格参考图增强图片一致性。' },
    { title: '合成视频', description: '在任务页或分步页直接合成视频并查看结果。' },
  ]

  const articleSteps = [
    { title: '进入开始创作', description: '在开始创作里切换到公众号文章模块。未开通时可浏览入口，但进入创作时会提示权限。' },
    { title: '选择轻量版或专业版', description: '轻量版适合快速出稿，专业版适合大纲、正文、配图、排版精修。' },
    { title: '生成文案', description: '支持 AI 草稿、自己写文案、段落编辑和局部 AI 重写。' },
    { title: '生成并调整配图', description: '图片与正文段落位置绑定，支持重生、调整插图位置、手机预览。' },
    { title: '排版与复制', description: '生成排版后，直接复制图文内容到公众号编辑器，而不是复制源码。' },
  ]

  return (
    <div style={{ padding: '32px 20px', maxWidth: 1180, margin: '0 auto' }}>
      <div style={{ padding: 28, borderRadius: 24, background: 'linear-gradient(135deg, #123555 0%, #2a6b84 50%, #efb26c 100%)', color: '#fff', marginBottom: 24 }}>
        <Title level={2} style={{ color: '#fff', marginBottom: 8 }}>使用教程</Title>
        <Paragraph style={{ color: 'rgba(255,255,255,0.88)', marginBottom: 0 }}>
          这是一套统一的内容创作平台，支持思维可视化、火柴人视频和公众号文章三个模块。以下教程按模块拆分，帮助普通用户和管理员快速上手。
        </Paragraph>
      </div>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
        message="默认权限说明"
        description="普通用户默认只开放思维可视化模块。火柴人视频与公众号文章需要管理员在后台按用户单独或批量开通。管理员账号三模块默认无限制。"
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={8}>
          <Card style={{ borderRadius: 20, border: '1px solid #d7e6ef', background: 'linear-gradient(180deg, #f7fbfd 0%, #ffffff 100%)' }}>
            <HighlightOutlined style={{ fontSize: 28, color: '#2563eb' }} />
            <Title level={4} style={{ marginTop: 12 }}>思维可视化</Title>
            <Paragraph type="secondary">适合知识讲解、公式推导、思维模型拆解。先对话，再生成脚本和视频。</Paragraph>
            <Steps direction="vertical" size="small" current={5} items={visualSteps} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card style={{ borderRadius: 20, border: '1px solid #f3d5a8', background: 'linear-gradient(180deg, #fff9ef 0%, #ffffff 100%)' }}>
            <VideoCameraOutlined style={{ fontSize: 28, color: '#d97706' }} />
            <Title level={4} style={{ marginTop: 12 }}>火柴人视频</Title>
            <Paragraph type="secondary">适合口播讲解、观点表达和人物叙事。支持多音色、参考风格图、分步创作。</Paragraph>
            <Steps direction="vertical" size="small" current={5} items={stickmanSteps} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card style={{ borderRadius: 20, border: '1px solid #ddd6fe', background: 'linear-gradient(180deg, #fbfaff 0%, #ffffff 100%)' }}>
            <FileTextOutlined style={{ fontSize: 28, color: '#7c3aed' }} />
            <Title level={4} style={{ marginTop: 12 }}>公众号文章</Title>
            <Paragraph type="secondary">适合公众号运营和图文创作，支持轻量版快速出稿和专业版精修工作台。</Paragraph>
            <Steps direction="vertical" size="small" current={5} items={articleSteps} />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginBottom: 24, borderRadius: 20 }}>
        <Title level={4}><BulbOutlined /> 平台入口说明</Title>
        <ul style={{ paddingLeft: 20, color: '#4b5563', lineHeight: 1.8 }}>
          <li>左侧 <Tag color="blue">开始创作</Tag> 是所有创作模块的统一入口。</li>
          <li>左侧 <Tag color="blue">我的作品</Tag> 统一查看思维可视化、火柴人视频、公众号文章历史作品。</li>
          <li>左侧不再单独放“公众号文章”，避免与开始创作重复。</li>
        </ul>
      </Card>

      <Card style={{ marginBottom: 24, borderRadius: 20 }}>
        <Title level={4}><SafetyOutlined /> 管理员怎么用</Title>
        <Collapse
          items={[
            {
              key: '1',
              label: '用户权限与次数设置',
              children: <div style={{ color: '#4b5563', lineHeight: 1.8 }}>后台支持为每个用户设置三模块开关和每日使用次数，也支持批量设置。管理员默认无限制，批量设置会自动跳过管理员。</div>,
            },
            {
              key: '2',
              label: '权限模板',
              children: <div style={{ color: '#4b5563', lineHeight: 1.8 }}>支持“仅公众号”“仅视频”“三模块全开”“体验版”“企业版”等模板，方便快速下发权限。</div>,
            },
            {
              key: '3',
              label: '模块看板',
              children: <div style={{ color: '#4b5563', lineHeight: 1.8 }}>可查看思维可视化、火柴人视频、公众号文章三个模块的累计、今日、成功数、失败数和成功率。</div>,
            },
          ]}
        />
      </Card>

      <Card style={{ marginBottom: 24, borderRadius: 20 }}>
        <Title level={4}><PlayCircleOutlined /> 常见问题</Title>
        <ul style={{ paddingLeft: 20, color: '#4b5563', lineHeight: 1.8 }}>
          <li>如果火柴人或公众号入口显示可浏览但创建时提示未开通，这是正常的权限拦截行为。</li>
          <li>思维可视化模块始终可用，不受其他模块权限影响。</li>
          <li>公众号文章配图后，请先在手机预览中确认图文顺序，再复制图文内容到公众号编辑器。</li>
          <li>如果火柴人视频音色没有变化，建议先在试听入口确认音色，再重新生成视频。</li>
        </ul>
      </Card>

      <Divider />

      <div style={{ textAlign: 'center' }}>
        <Button type="primary" size="large" onClick={() => navigate('/creator')}>进入开始创作</Button>
      </div>
    </div>
  )
}
