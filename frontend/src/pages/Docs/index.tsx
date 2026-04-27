import { Alert, Button, Card, Col, Collapse, Divider, Row, Steps, Tag, Typography } from 'antd'
import type { CSSProperties } from 'react'
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

const screenshotStyle: CSSProperties = {
  width: '100%',
  borderRadius: 18,
  border: '1px solid #d7e6ef',
  boxShadow: '0 12px 28px rgba(15, 23, 42, 0.08)',
  background: '#fff',
}

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
    { title: '进入开始创作', description: '在开始创作里切换到视频讲解模块。未开通时仍可浏览，但创建时会提示未开通。' },
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

  const beginnerGuide = [
    {
      title: '第一步：进入开始创作',
      description: '登录后，左侧菜单点击“开始创作”。这里是整个平台的统一入口，不需要分别记住不同模块地址。',
      image: '/help/creator-overview.svg',
    },
    {
      title: '第二步：进入视频讲解大类',
      description: '如果你想做口播/讲解类视频，先进入“视频讲解”，再在下一级页面选择标准讲解、增强讲解或讲解型视频。',
      image: '/help/stickman-entry.svg',
    },
    {
      title: '第三步：填写讲解型视频内容',
      description: '把完整文案直接粘贴进创作台。系统会自动按文案节奏拆分分镜，分镜数量支持 3-10，时长也会根据文案和配音自动控制。',
      image: '/help/explainer-creator.svg',
    },
    {
      title: '第四步：管理员上传模板示例视频',
      description: '管理员进入后台模板管理，可以为模板上传示例 MP4，方便普通用户直接预览效果。',
      image: '/help/admin-template-upload.svg',
    },
  ]

  return (
    <div style={{ padding: '32px 20px', maxWidth: 1180, margin: '0 auto' }}>
      <div style={{ padding: 28, borderRadius: 24, background: 'linear-gradient(135deg, #123555 0%, #2a6b84 50%, #efb26c 100%)', color: '#fff', marginBottom: 24 }}>
        <Title level={2} style={{ color: '#fff', marginBottom: 8 }}>使用教程</Title>
        <Paragraph style={{ color: 'rgba(255,255,255,0.88)', marginBottom: 0 }}>
          这是一套统一的内容创作平台，支持思维可视化、视频讲解和公众号文章三个模块。以下教程按模块拆分，帮助普通用户和管理员快速上手。
        </Paragraph>
      </div>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
        message="默认权限说明"
        description="普通用户默认只开放思维可视化模块。视频讲解与公众号文章需要管理员在后台按用户单独或批量开通。管理员账号三模块默认无限制。"
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
            <Title level={4} style={{ marginTop: 12 }}>视频讲解</Title>
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
          <li>左侧 <Tag color="blue">我的作品</Tag> 统一查看思维可视化、视频讲解、公众号文章历史作品。</li>
          <li>左侧不再单独放“公众号文章”，避免与开始创作重复。</li>
        </ul>
      </Card>

      <Card style={{ marginBottom: 24, borderRadius: 20 }}>
        <Title level={4}>零基础完整教程</Title>
        <Paragraph type="secondary" style={{ marginBottom: 20 }}>
          如果你第一次使用平台，可以直接按下面 4 步走。每一步都配了页面截图，先照着做，再慢慢熟悉高级功能。
        </Paragraph>
        {beginnerGuide.map((item, index) => (
          <div key={item.title} style={{ marginBottom: index === beginnerGuide.length - 1 ? 0 : 28 }}>
            <Title level={5} style={{ marginBottom: 8 }}>{index + 1}. {item.title}</Title>
            <Paragraph style={{ color: '#4b5563', lineHeight: 1.8 }}>{item.description}</Paragraph>
            <img src={item.image} alt={item.title} style={screenshotStyle} />
          </div>
        ))}
      </Card>

      <Card style={{ marginBottom: 24, borderRadius: 20 }}>
        <Title level={4}>讲解型视频推荐操作顺序</Title>
        <Steps
          direction="vertical"
          size="small"
          current={6}
          items={[
            { title: '先输入原始文案或主题', description: '不需要先压缩到很短，先把你的内容说明白。' },
            { title: '选择分镜数量', description: '新手建议先用 4-6 幕，便于快速检查结构。' },
            { title: '先生成开头与分镜', description: '先看前 3 秒钩子够不够强，再决定是否继续。' },
            { title: '再生成图片', description: '如果画面方向不对，先改分镜文字，不要急着反复重生。' },
            { title: '最后合成视频', description: '检查字幕、旁白、节奏是否一致。' },
            { title: '满意后再批量复用', description: '等你跑通一次，再开始追求更复杂的风格和效率。' },
          ]}
        />
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
                children: <div style={{ color: '#4b5563', lineHeight: 1.8 }}>可查看思维可视化、视频讲解、公众号文章三个模块的累计、今日、成功数、失败数和成功率。</div>,
            },
            {
              key: '4',
              label: '模板示例视频怎么上传',
              children: <div style={{ color: '#4b5563', lineHeight: 1.8 }}>进入“管理后台” - “视频风格模板管理”，在模板卡片上点击“上传示例视频”，选择一个 MP4 文件即可。上传成功后，模板卡片会出现“预览示例”按钮，普通用户也能直接预览效果。</div>,
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
          <li>如果视频讲解音色没有变化，建议先在试听入口确认音色，再重新生成视频。</li>
          <li>如果管理员上传模板示例视频失败，先确认文件格式是 MP4，且当前账号确实是管理员。</li>
        </ul>
      </Card>

      <Divider />

      <div style={{ textAlign: 'center' }}>
        <Button type="primary" size="large" onClick={() => navigate('/creator')}>进入开始创作</Button>
      </div>
    </div>
  )
}
