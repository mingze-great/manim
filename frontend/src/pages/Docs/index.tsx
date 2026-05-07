import type { CSSProperties } from 'react'
import { Alert, Button, Card, Col, Divider, Row, Space, Steps, Typography } from 'antd'
import {
  BookOutlined,
  FileTextOutlined,
  HighlightOutlined,
  HistoryOutlined,
  PlayCircleOutlined,
  RocketOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title, Paragraph, Text } = Typography

const screenshotStyle: CSSProperties = {
  width: '100%',
  borderRadius: 18,
  border: '1px solid #d7e6ef',
  boxShadow: '0 12px 28px rgba(15, 23, 42, 0.08)',
  background: '#fff',
}

const sectionCardStyle: CSSProperties = {
  borderRadius: 20,
  border: '1px solid #d7e6ef',
}

const visualFlow = [
  '进入“开始创作”，选择“思维可视化”。',
  '输入主题，进入对话页和 AI 一起打磨文案。',
  '确认后进入任务页，生成脚本、渲染并下载视频。',
]

const stickmanFlow = [
  '进入“视频讲解”，再选择标准讲解或增强讲解。',
  '先生成脚本与分镜，再在详情页校正文案、镜头和图片。',
  '确认后合成视频，在任务页或详情页预览成片。',
]

const explainerFlow = [
  '进入“视频讲解”里的“讲解型视频”。',
  '粘贴完整文案，系统自动拆成 3-10 幕并估算时长。',
  '在分步工作台统一调整分镜、风格、图片和合成结果。',
]

const articleFlow = [
  '进入“公众号文章”模块，选择轻量版或工作台。',
  '生成正文、段落配图和排版。',
  '在手机预览确认效果后，再复制到公众号编辑器。',
]

const quickLinks = [
  {
    title: '开始前必读',
    description: '第一次使用系统前，先理解整体入口和推荐流程。',
    icon: <BookOutlined style={{ fontSize: 26, color: '#1d4ed8' }} />,
  },
  {
    title: '思维可视化',
    description: '适合知识讲解、模型拆解、课程短视频。',
    icon: <HighlightOutlined style={{ fontSize: 26, color: '#2563eb' }} />,
  },
  {
    title: '视频讲解',
    description: '适合口播讲解、观点表达、人物叙事。',
    icon: <VideoCameraOutlined style={{ fontSize: 26, color: '#d97706' }} />,
  },
  {
    title: '公众号文章',
    description: '适合图文运营、长文内容生产和排版。',
    icon: <FileTextOutlined style={{ fontSize: 26, color: '#7c3aed' }} />,
  },
]

const commonTips = [
  '第一次使用时，建议先完整跑通 1 条内容，再开始追求更复杂的风格和更长的文案。',
  '如果你要做视频，请先把“脚本/分镜/预览图”确认好，再正式生成全部图片和最终视频。',
  '如果你要做公众号文章，请先在平台内完成手机预览，再复制到公众号后台。',
  '“我的作品”会统一存放不同模块的结果，建议按主题定期整理和删除旧项目。',
]

export default function Docs() {
  const navigate = useNavigate()

  return (
    <div style={{ padding: '32px 20px', maxWidth: 1240, margin: '0 auto' }}>
      <div style={{ padding: 32, borderRadius: 28, background: 'linear-gradient(135deg, #123555 0%, #2a6b84 50%, #efb26c 100%)', color: '#fff', marginBottom: 24 }}>
        <Title level={2} style={{ color: '#fff', marginBottom: 8 }}>企业级使用手册</Title>
        <Paragraph style={{ color: 'rgba(255,255,255,0.9)', marginBottom: 0, fontSize: 16 }}>
          这是一份面向普通用户的完整系统教程，覆盖从进入系统、选择模块、生成内容，到复查结果和管理作品的全流程。你可以把它当成正式操作手册来用。
        </Paragraph>
      </div>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
        message="适用范围"
        description="本教程只讲普通用户如何使用整个系统，不涉及管理员后台、权限下发和系统配置。"
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {quickLinks.map((item) => (
          <Col xs={24} md={12} xl={6} key={item.title}>
            <Card style={{ ...sectionCardStyle, height: '100%' }}>
              {item.icon}
              <Title level={5} style={{ marginTop: 14 }}>{item.title}</Title>
              <Paragraph type="secondary" style={{ marginBottom: 0 }}>{item.description}</Paragraph>
            </Card>
          </Col>
        ))}
      </Row>

      <Card style={{ ...sectionCardStyle, marginBottom: 24 }}>
        <Title level={4}><RocketOutlined /> 一、开始前先理解系统结构</Title>
        <Paragraph style={{ color: '#4b5563', lineHeight: 1.9 }}>
          系统的核心逻辑是：先从统一入口进入，再按内容类型进入不同工作流。你不需要记住很多页面，只需要记住左侧的三个核心入口：
          <Text strong> 开始创作、我的作品、帮助中心</Text>。
        </Paragraph>
        <img src="/help/creator-overview.svg" alt="开始创作总览" style={screenshotStyle} />
        <Steps
          direction="vertical"
          size="small"
          current={4}
          style={{ marginTop: 20 }}
          items={[
            { title: '开始创作', description: '所有新项目都从这里进入。' },
            { title: '视频讲解是一个大类', description: '标准讲解、增强讲解、讲解型视频都收在这里。' },
            { title: '我的作品', description: '查看和回访所有历史项目。' },
            { title: '帮助中心', description: '忘记操作时，直接回到这里查看说明。' },
          ]}
        />
      </Card>

      <Card style={{ ...sectionCardStyle, marginBottom: 24 }}>
        <Title level={4}>二、推荐的统一操作顺序</Title>
        <Paragraph type="secondary">如果你是第一次使用，建议严格按这个顺序操作。</Paragraph>
        <Steps
          direction="vertical"
          current={6}
          items={[
            { title: '选择模块', description: '先判断你要做的是动画视频、讲解视频，还是公众号文章。' },
            { title: '先做一个短项目', description: '先用较短内容验证流程，不要一开始就用超长文案。' },
            { title: '先确认脚本和分镜', description: '脚本不顺时，后面的图片和成片都会跟着出问题。' },
            { title: '再确认画面', description: '先看预览图/分镜图，再决定是否继续。' },
            { title: '最后生成正式结果', description: '图片、视频、图文都建议在前面确认后再正式输出。' },
            { title: '回到我的作品统一管理', description: '下载、复看、复用都从这里进行。' },
          ]}
        />
      </Card>

      <Card style={{ ...sectionCardStyle, marginBottom: 24 }}>
        <Title level={4}><HighlightOutlined /> 三、思维可视化全流程</Title>
        <Paragraph style={{ color: '#4b5563', lineHeight: 1.9 }}>
          思维可视化适合做知识拆解、课程短视频、公式推导和结构化讲解。它的优势是 <Text strong>先对话打磨内容，再生成脚本和视频</Text>。
        </Paragraph>
        <img src="/help/workflow-visual-chat.svg" alt="思维可视化对话工作流" style={screenshotStyle} />
        <div style={{ marginTop: 18 }}>
          {visualFlow.map((item, index) => (
            <Paragraph key={item} style={{ marginBottom: 10, color: '#4b5563' }}>{index + 1}. {item}</Paragraph>
          ))}
        </div>
        <Alert type="success" showIcon message="建议" description="如果你不确定主题该怎么写，先输入一句最朴素的话，再让 AI 帮你改成更适合视频的表达。" />
      </Card>

      <Card style={{ ...sectionCardStyle, marginBottom: 24 }}>
        <Title level={4}><VideoCameraOutlined /> 四、视频讲解全流程</Title>
        <Paragraph style={{ color: '#4b5563', lineHeight: 1.9 }}>
          视频讲解是系统里最完整的视频工作流。你先进入“视频讲解”大类，再选择最适合你的子模块。
        </Paragraph>
        <img src="/help/stickman-entry.svg" alt="视频讲解模块选择" style={screenshotStyle} />
        <div style={{ marginTop: 18 }}>
          {stickmanFlow.map((item, index) => (
            <Paragraph key={item} style={{ marginBottom: 10, color: '#4b5563' }}>{index + 1}. {item}</Paragraph>
          ))}
        </div>
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card style={{ ...sectionCardStyle, height: '100%' }}>
              <Title level={5}>标准讲解</Title>
              <Paragraph type="secondary">适合追求稳定流程、快速出片、少做额外调试的用户。</Paragraph>
              <ul style={{ paddingLeft: 20, color: '#4b5563', lineHeight: 1.8 }}>
                <li>先生成脚本和分镜</li>
                <li>再确认预览图和全部图片</li>
                <li>最后合成视频</li>
              </ul>
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card style={{ ...sectionCardStyle, height: '100%' }}>
              <Title level={5}>增强讲解</Title>
              <Paragraph type="secondary">适合对视觉控制更高、希望有更多风格与包装选项的用户。</Paragraph>
              <ul style={{ paddingLeft: 20, color: '#4b5563', lineHeight: 1.8 }}>
                <li>支持更强的风格控制</li>
                <li>支持上传背景图和更多画面包装</li>
                <li>适合反复打磨成片效果</li>
              </ul>
            </Card>
          </Col>
        </Row>
        <img src="/help/workflow-stickman-studio.svg" alt="视频讲解详情页工作台" style={{ ...screenshotStyle, marginTop: 18 }} />
      </Card>

      <Card style={{ ...sectionCardStyle, marginBottom: 24 }}>
        <Title level={4}><PlayCircleOutlined /> 五、讲解型视频全流程</Title>
        <Paragraph style={{ color: '#4b5563', lineHeight: 1.9 }}>
          如果你已经有一段完整文案，或者你想做更强的“短视频口播讲解”结构，优先使用讲解型视频模块。它的重点是 <Text strong>按文案自动拆分分镜、自动估算时长、统一管理图片和配音</Text>。
        </Paragraph>
        <img src="/help/explainer-creator.svg" alt="讲解型视频创建页" style={screenshotStyle} />
        <div style={{ marginTop: 18 }}>
          {explainerFlow.map((item, index) => (
            <Paragraph key={item} style={{ marginBottom: 10, color: '#4b5563' }}>{index + 1}. {item}</Paragraph>
          ))}
        </div>
        <img src="/help/workflow-explainer-studio.svg" alt="讲解型视频详情页工作台" style={{ ...screenshotStyle, marginTop: 18 }} />
        <Alert type="warning" showIcon message="新手建议" description="第一次使用讲解型视频时，建议先选 4-6 幕。这样更容易快速检查开头效果、文案是否顺口，以及画面是否一致。" style={{ marginTop: 18 }} />
      </Card>

      <Card style={{ ...sectionCardStyle, marginBottom: 24 }}>
        <Title level={4}><FileTextOutlined /> 六、公众号文章全流程</Title>
        <Paragraph style={{ color: '#4b5563', lineHeight: 1.9 }}>
          公众号文章模块适合做长文、图文运营和私域内容沉淀。推荐做法是先完成正文，再做配图和排版，最后在手机预览中确认成稿效果。
        </Paragraph>
        <img src="/help/workflow-article-studio.svg" alt="公众号文章工作台" style={screenshotStyle} />
        <div style={{ marginTop: 18 }}>
          {articleFlow.map((item, index) => (
            <Paragraph key={item} style={{ marginBottom: 10, color: '#4b5563' }}>{index + 1}. {item}</Paragraph>
          ))}
        </div>
        <Alert type="info" showIcon message="重要提醒" description="排版完成后，请复制图文内容，而不是复制源码。复制前务必先在手机预览中检查图文顺序。" />
      </Card>

      <Card style={{ ...sectionCardStyle, marginBottom: 24 }}>
        <Title level={4}><HistoryOutlined /> 七、我的作品与日常管理</Title>
        <Paragraph style={{ color: '#4b5563', lineHeight: 1.9 }}>
          不管你做的是视频还是文章，最后都会进入“我的作品”。这里建议你把它当作企业内容资产库来管理。
        </Paragraph>
        <img src="/help/workflow-history.svg" alt="我的作品中心" style={screenshotStyle} />
        <ul style={{ paddingLeft: 20, color: '#4b5563', lineHeight: 1.8, marginTop: 16 }}>
          <li>完成后及时下载结果，避免项目太多难以管理。</li>
          <li>保留代表性项目，删除无效测试项目，保持工作区清爽。</li>
          <li>如果某个项目很接近你想要的效果，优先基于它继续修改，而不是重新开一个全新项目。</li>
        </ul>
      </Card>

      <Card style={{ ...sectionCardStyle, marginBottom: 24 }}>
        <Title level={4}>八、常见问题</Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {commonTips.map((item) => (
            <Alert key={item} type="info" showIcon message={item} />
          ))}
        </Space>
      </Card>

      <Divider />

      <div style={{ textAlign: 'center' }}>
        <Space wrap>
          <Button type="primary" size="large" onClick={() => navigate('/creator')}>进入开始创作</Button>
          <Button size="large" onClick={() => navigate('/history')}>查看我的作品</Button>
        </Space>
      </div>
    </div>
  )
}
