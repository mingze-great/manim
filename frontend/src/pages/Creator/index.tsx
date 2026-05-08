import { useEffect, useState } from 'react'
import { Alert, Button, Input, message, Divider, Card, Segmented, Select, Modal } from 'antd'
import { RocketOutlined, BulbOutlined, VideoCameraOutlined, HighlightOutlined, FileTextOutlined } from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { projectApi } from '@/services/project'
import { articleApi, Category as ArticleCategory } from '@/services/article'
import TopicCategorySelector from './components/TopicCategorySelector'
import TopicExamples from './components/TopicExamples'
import { VideoTopicCategory } from '@/services/videoTopic'
import './Creator.css'

const { TextArea } = Input

type ModuleType = 'manim' | 'math' | 'stickman' | 'article'

const CREATOR_UPDATE_NOTICE_KEY = 'creator_update_notice_20260428_v1'

export default function Creator() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const user = useAuthStore((state) => state.user)
  const [loading, setLoading] = useState(false)
  const [moduleType, setModuleType] = useState<ModuleType>('manim')
  const [selectedCategory, setSelectedCategory] = useState<VideoTopicCategory | null>(null)
  const [customTopic, setCustomTopic] = useState('')
  const [mathTopic, setMathTopic] = useState('')
  const [articleTopic, setArticleTopic] = useState('')
  const [articleCategory, setArticleCategory] = useState('生活')
  const [articleCategories, setArticleCategories] = useState<ArticleCategory[]>([])
  const [selectedArticleCategory, setSelectedArticleCategory] = useState<ArticleCategory | null>(null)
  const [updateNoticeVisible, setUpdateNoticeVisible] = useState(false)

  const permissions = user?.module_permissions || {}
  const stickmanEnabled = user?.is_admin || permissions.stickman?.enabled !== false
  const articleEnabled = user?.is_admin || permissions.article?.enabled !== false

  const handleCategorySelect = (category: VideoTopicCategory) => {
    setSelectedCategory(category)
  }

  const ensureArticleCategories = async () => {
    if (articleCategories.length) return articleCategories
    const { data } = await articleApi.getCategories()
    setArticleCategories(data)
    return data
  }

  const handleArticleModeEnter = async () => {
    try {
      await ensureArticleCategories()
    } catch {
      message.error('加载公众号主题方向失败')
    }
  }

  const handleCreateProject = async (payload: {
    title: string
    theme: string
    category?: string
    module_type: 'manim'
    storyboard_count?: number
  }) => {
    setLoading(true)
    try {
      const { data } = await projectApi.create(payload)
      message.success('创建成功')
      navigate(`/project/${data.id}/chat`)
    } catch (error: any) {
      const detail = error.response?.data?.detail || error.message || '创建失败'
      message.error(detail)
    } finally {
      setLoading(false)
    }
  }

  const handleTopicSelect = async (topic: string) => {
    await handleCreateProject({
      title: topic,
      theme: topic,
      category: selectedCategory?.name,
      module_type: 'manim',
      storyboard_count: 3,
    })
  }

  const handleMathCreate = async () => {
    if (!mathTopic.trim()) {
      message.warning('请输入数学主题')
      return
    }
    setLoading(true)
    try {
      const { data } = await projectApi.create({
        title: mathTopic.trim(),
        theme: mathTopic.trim(),
        category: 'math',
        module_type: 'manim',
        storyboard_count: 3,
      })
      message.success('创建成功')
      navigate(`/project/${data.id}/task`)
    } catch (error: any) {
      const detail = error.response?.data?.detail || error.message || '创建失败'
      message.error(detail)
    } finally {
      setLoading(false)
    }
  }

  const handleCustomCreate = async () => {
    if (!customTopic.trim()) {
      message.warning('请输入主题')
      return
    }
    await handleTopicSelect(customTopic)
  }

  const handleArticleTopicSelect = (topic: string) => {
    if (!articleEnabled) {
      message.warning('当前账号未开通公众号文章模块，请联系管理员开通')
      return
    }
    setArticleTopic(topic)
    navigate(`/article?topic=${encodeURIComponent(topic)}&category=${encodeURIComponent(articleCategory)}`)
  }

  useEffect(() => {
    const nextModule = searchParams.get('module')
    const nextVariant = searchParams.get('variant')
    if (nextModule === 'stickman') {
      navigate(`/creator/stickman/${nextVariant === 'v2' ? 'v2' : 'legacy'}`, { replace: true })
      return
    }
  }, [navigate, searchParams])

  useEffect(() => {
    try {
      if (window.localStorage.getItem(CREATOR_UPDATE_NOTICE_KEY) === 'read') {
        return
      }
    } catch {
      // Ignore local storage access failures and still show once.
    }
    setUpdateNoticeVisible(true)
  }, [])

  const handleMarkUpdateNoticeRead = () => {
    try {
      window.localStorage.setItem(CREATOR_UPDATE_NOTICE_KEY, 'read')
    } catch {
      // Ignore local storage access failures.
    }
    setUpdateNoticeVisible(false)
  }

  return (
    <div className="creator-page">
      <Modal
        title="新版功能上线"
        open={updateNoticeVisible}
        closable={false}
        maskClosable={false}
        footer={[
          <Button key="read" type="primary" onClick={handleMarkUpdateNoticeRead}>
            标记已读
          </Button>,
        ]}
      >
        <div style={{ lineHeight: 1.9 }}>
          <div>- 新增新版心理讲解类视频，创作流程更清晰</div>
          <div>- 新增数学可视化视频，支持更丰富的教学表达</div>
          <div>- 模板预览体验优化，查看效果更直观</div>
          <div>- 新增对话风格支持，生成内容更贴合你的表达习惯</div>
        </div>
      </Modal>

      <div className="creator-hero creator-hero-sunrise">
        <div className="hero-content">
          <h1 className="hero-title">
            <RocketOutlined className="mr-3" />
            内容创作助手
          </h1>
          <p className="hero-subtitle">
            在统一入口选择动画视频、视频讲解或公众号文章模块，再进入各自独立的创作流程
          </p>
        </div>
      </div>

      <div className="creator-container">
        <div className="module-switcher-wrap">
          <div className="module-switcher-head">
            <span className="module-switcher-label">开始创作</span>
            <Segmented
              value={moduleType}
              onChange={(value) => {
                const next = value as ModuleType
                if (next === 'stickman') {
                  navigate('/creator/stickman')
                  return
                }
                setModuleType(next)
                if (next === 'article') {
                  handleArticleModeEnter()
                }
              }}
              options={[
                { label: '思维可视化', value: 'manim' },
                { label: '数学可视化', value: 'math' },
                { label: '视频讲解', value: 'stickman' },
                { label: '公众号文章', value: 'article' },
              ]}
            />
          </div>

          <div className="module-card-grid">
            <Card className={`module-card ${moduleType === 'manim' ? 'active' : ''}`} onClick={() => setModuleType('manim')}>
              <div className="module-card-icon module-card-icon-blue">
                <HighlightOutlined />
              </div>
              <h3>思维可视化</h3>
              <p>多轮打磨文案，生成动画脚本，再进入渲染流程。</p>
            </Card>

            <Card className={`module-card ${moduleType === 'math' ? 'active' : ''}`} onClick={() => setModuleType('math')}>
              <div className="module-card-icon" style={{ color: '#0ea5e9' }}>
                <span style={{ fontSize: 24 }}>📐</span>
              </div>
              <h3>数学可视化</h3>
              <p>输入数学主题，选择模板，直接生成公式推演动画。</p>
            </Card>

            <Card className={`module-card ${moduleType === 'stickman' ? 'active' : ''} ${!stickmanEnabled ? 'module-card-disabled' : ''}`} onClick={() => navigate('/creator/stickman')}>
              <div className="module-card-icon module-card-icon-orange">
                <VideoCameraOutlined />
              </div>
              <h3>视频讲解</h3>
              <p>先进入版本选择页，再进入标准讲解或增强讲解创作流程。</p>
            </Card>

            <Card className={`module-card ${moduleType === 'article' ? 'active' : ''} ${!articleEnabled ? 'module-card-disabled' : ''}`} onClick={() => { setModuleType('article'); handleArticleModeEnter() }}>
              <div className="module-card-icon module-card-icon-green">
                <FileTextOutlined />
              </div>
              <h3>公众号文章</h3>
              <p>生成大纲、正文、配图与公众号 HTML，支持手机预览和复制。</p>
            </Card>
          </div>
        </div>

        {moduleType === 'manim' ? (
          selectedCategory ? (
            <div className="max-w-2xl mx-auto">
              <Button onClick={() => setSelectedCategory(null)} className="mb-4">
                返回选择方向
              </Button>
              <TopicExamples category={selectedCategory} onSelect={handleTopicSelect} />
            </div>
          ) : (
            <>
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-4">
                  <BulbOutlined className="text-xl text-indigo-500" />
                  <span className="text-lg font-medium">选择热门方向</span>
                </div>
                <TopicCategorySelector onSelect={handleCategorySelect} />
              </div>

              <Divider>或直接输入主题</Divider>

              <div className="visual-theme-wrap mx-auto">
                <TextArea
                  value={customTopic}
                  onChange={(e) => setCustomTopic(e.target.value)}
                  placeholder={`输入你的视频主题...

例如：
• 世界十大顶级思维：刻意练习、复利思维、终身学习...
• 勾股定理的证明过程
• 人生三件事：运动、阅读、赚钱`}
                  rows={4}
                  className="theme-input mb-3"
                />

                <Button
                  type="primary"
                  icon={<RocketOutlined />}
                  onClick={handleCustomCreate}
                  loading={loading}
                  size="large"
                  block
                  disabled={!customTopic.trim()}
                  className="btn-gradient"
                >
                  开始创作
                </Button>
              </div>

              <div className="usage-tips mt-6">
                <h3>
                  <BulbOutlined className="mr-2" />
                  使用提示
                </h3>
                <ul>
                  <li>选择热门方向，直接使用爆款主题示例</li>
                  <li>或输入主题，进入 AI 对话打磨流程</li>
                  <li>确认文案后再生成思维可视化脚本和动画视频</li>
                  <li>适合讲解类、思维类、演示类内容</li>
                </ul>
              </div>
            </>
          )
        ) : moduleType === 'math' ? (
          <div className="stickman-panel">
            <div className="stickman-panel-head">
              <h2>数学可视化模块</h2>
              <p>输入数学主题，选择模板风格，直接生成公式推演、定理证明或几何图解动画。</p>
            </div>

            <div className="stickman-form-grid">
              <div>
                <label className="stickman-label">数学主题</label>
                <TextArea
                  value={mathTopic}
                  onChange={(e) => setMathTopic(e.target.value)}
                  rows={5}
                  placeholder={`输入数学主题，例如：
• 梯度下降算法 (Gradient Descent)
• 欧拉公式 e^(iπ) + 1 = 0
• 泰勒展开 (Taylor Expansion)
• 勾股定理的几何证明
• 正弦函数的图像变换
• 柯西-施瓦茨不等式`}
                />
              </div>

              <div className="stickman-side-card">
                <div className="stickman-tips">
                  <p>支持公式推演、定理证明、几何图解等多种数学场景。</p>
                  <p>选择主题后将进入模板选择和脚本生成流程。</p>
                  <p>基于 Manim 动画引擎，充分发挥数学可视化优势。</p>
                </div>

                <Button
                  type="primary"
                  icon={<RocketOutlined />}
                  onClick={handleMathCreate}
                  loading={loading}
                  size="large"
                  block
                  disabled={!mathTopic.trim()}
                  className="btn-gradient"
                >
                  创建并生成动画
                </Button>
              </div>
            </div>
          </div>
        ) : moduleType === 'stickman' ? (
          <div className="stickman-panel">
            <div className="stickman-panel-head">
              <h2>视频讲解模块</h2>
              <p>视频讲解已经迁移为独立创建流，先选择版本，再进入对应的专属配置页。</p>
            </div>

            <Alert
              type="info"
              message="视频讲解配置已独立"
              description="为了避免选完版本后又回到首页配置，现在标准讲解和增强讲解都使用独立创建页。"
            />

            <div className="mt-6 flex gap-3 flex-wrap">
              <Button type="primary" icon={<VideoCameraOutlined />} onClick={() => navigate('/creator/stickman')}>
                去选择讲解版本
              </Button>
              <Button onClick={() => setModuleType('manim')}>返回思维可视化</Button>
            </div>
          </div>
        ) : (
          <div className="stickman-panel">
            <div className="stickman-panel-head">
              <h2>公众号文章模块</h2>
              <p>支持热门主题、AI 选题、轻量版和专业版工作台。</p>
            </div>

            {selectedArticleCategory ? (
              <div className="max-w-2xl mx-auto">
                <Button onClick={() => setSelectedArticleCategory(null)} className="mb-4">
                  返回选择方向
                </Button>
                <TopicExamples category={selectedArticleCategory} onSelect={handleArticleTopicSelect} generateTopics={articleApi.generateTopics} titlePrefix="热门主题" />
                <div className="mt-6 stickman-form-grid">
                  <div>
                    <label className="stickman-label">文章主题</label>
                    <TextArea value={articleTopic} onChange={(e) => setArticleTopic(e.target.value)} rows={5} placeholder={`例如：
• 为什么成年人越忙越要阅读
• 一个普通人如何建立长期主义
• 父母如何高质量陪伴孩子成长`} />
                  </div>
                  <div className="stickman-side-card">
                    <label className="stickman-label">创作方向</label>
                    <div className="aspect-pill">{articleCategory}</div>
                    <div className="stickman-tips">
                      <p>适合公众号运营、自媒体图文和知识分享场景。</p>
                      <p>支持热门主题、AI 选题、轻量版和专业版。</p>
                    </div>
                    <Button type="primary" icon={<FileTextOutlined />} onClick={() => {
                      if (!articleEnabled) {
                        message.warning('当前账号未开通公众号文章模块，请联系管理员开通')
                        return
                      }
                      navigate(`/article?topic=${encodeURIComponent(articleTopic.trim())}&category=${encodeURIComponent(articleCategory)}`)
                    }} size="large" block disabled={!articleTopic.trim()} className="btn-gradient">
                      进入公众号创作
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
            <>
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-4">
                  <BulbOutlined className="text-xl text-indigo-500" />
                  <span className="text-lg font-medium">选择热门方向</span>
                </div>
                <Button onClick={handleArticleModeEnter} className="mb-3">加载公众号方向</Button>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {articleCategories.map((cat) => (
                    <div key={cat.name} className="category-card p-4 rounded-lg border-2 border-gray-200 cursor-pointer hover:border-indigo-500 hover:shadow-md transition-all" onClick={() => { setArticleCategory(cat.name); setSelectedArticleCategory(cat) }}>
                      <div className="text-3xl text-center mb-2">{cat.icon}</div>
                      <div className="text-sm font-medium text-center">{cat.name}</div>
                    </div>
                  ))}
                </div>
              </div>

              <Divider>或直接输入主题</Divider>

              <div className="stickman-form-grid">
                <div>
                  <label className="stickman-label">文章主题</label>
                  <TextArea
                    value={articleTopic}
                    onChange={(e) => setArticleTopic(e.target.value)}
                    rows={5}
                    placeholder={`例如：
• 为什么成年人越忙越要阅读
• 一个普通人如何建立长期主义
• 父母如何高质量陪伴孩子成长`}
                  />
                </div>

                <div className="stickman-side-card">
                  <label className="stickman-label">创作方向</label>
                  <Select value={articleCategory} onChange={setArticleCategory} options={articleCategories.map((cat) => ({ label: cat.name, value: cat.name }))} style={{ width: '100%' }} />

                  <div className="stickman-tips">
                    <p>适合公众号运营、自媒体图文和知识分享场景。</p>
                    <p>进入后可选择轻量版或专业版。</p>
                    <p>同样支持热门主题与 AI 选题。</p>
                  </div>

                  <Button type="primary" icon={<FileTextOutlined />} onClick={() => {
                    if (!articleEnabled) {
                      message.warning('当前账号未开通公众号文章模块，请联系管理员开通')
                      return
                    }
                    navigate(`/article?topic=${encodeURIComponent(articleTopic.trim())}&category=${encodeURIComponent(articleCategory)}`)
                  }} size="large" block disabled={!articleTopic.trim()} className="btn-gradient">
                    进入公众号创作
                  </Button>
                </div>
              </div>
            </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
