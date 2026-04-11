import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  Alert,
  Button,
  Card,
  Divider,
  Empty,
  Input,
  Popconfirm,
  Progress,
  Segmented,
  Space,
  Steps,
  Tag,
  Typography,
  message,
} from 'antd'
import {
  CheckOutlined,
  CopyOutlined,
  DeleteOutlined,
  EditOutlined,
  FileImageOutlined,
  PlusOutlined,
  ReloadOutlined,
  RocketOutlined,
  SaveOutlined,
} from '@ant-design/icons'
import { resolveBackendUrl } from '@/services/api'
import { Article, articleApi } from '@/services/article'
import { copyRichHtml } from '@/utils/copyRichHtml'
import CategorySelector from './components/CategorySelector'
import PhonePreview from './components/PhonePreview'

const { TextArea } = Input
const { Title, Text } = Typography

type Mode = 'quick' | 'pro'

type OutlineSection = {
  id: string
  text: string
}

type ContentBlock = {
  id: string
  text: string
}

const steps = [
  { title: '主题设定' },
  { title: '大纲确认' },
  { title: '正文精修' },
  { title: '配图管理' },
  { title: '排版导出' },
]

function uid(prefix: string) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`
}

function outlineToSections(outline: string): OutlineSection[] {
  const lines = outline
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
  return lines.map((text) => ({ id: uid('outline'), text }))
}

function sectionsToOutline(sections: OutlineSection[]) {
  return sections.map((item) => item.text.trim()).filter(Boolean).join('\n')
}

function contentToBlocks(content: string): ContentBlock[] {
  const parts = content
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .filter(Boolean)
  return parts.map((text) => ({ id: uid('block'), text }))
}

function blocksToContent(blocks: ContentBlock[]) {
  return blocks.map((item) => item.text.trim()).filter(Boolean).join('\n\n')
}

function resolveAssetUrl(url?: string | null) {
  return resolveBackendUrl(url)
}

function buildPublishableHtml(html?: string | null) {
  if (!html) return ''
  return html.replace(/src="(\/api\/[^\"]+)"/g, (_m, path) => `src="${resolveBackendUrl(path)}"`)
}

function buildDefaultAnchors(imageCount: number, paragraphCount: number) {
  if (imageCount <= 0) return {}
  if (paragraphCount <= 1) return Object.fromEntries(Array.from({ length: imageCount }, (_, i) => [i + 1, 1]))
  const anchors: Record<number, number> = {}
  for (let index = 1; index <= imageCount; index += 1) {
    const anchor = Math.round((index * paragraphCount) / (imageCount + 1))
    anchors[index] = Math.max(1, Math.min(paragraphCount, anchor))
  }
  return anchors
}

function buildPreviewHtml(title: string, content: string, images: any[]) {
  const paragraphs = content.split(/\n\s*\n/).map((item) => item.trim()).filter(Boolean)
  const parts = [`<section style="padding:20px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">`]
  parts.push(`<h1 style="font-size:24px;font-weight:bold;color:#333;margin-bottom:20px;text-align:center;">${title || '公众号文章'}</h1>`)
  const cover = images?.find((img) => img.type === 'cover')
  if (cover?.url) parts.push(`<p style="text-align:center;margin-bottom:20px;"><img src="${resolveAssetUrl(cover.url)}" style="max-width:100%;height:auto;border-radius:8px;" /></p>`)
  const contentImages = images?.filter((img) => img.type !== 'cover') || []
  const defaultAnchors = buildDefaultAnchors(contentImages.length, paragraphs.length || 1)
  paragraphs.forEach((para, index) => {
    parts.push(`<p style="font-size:16px;line-height:1.8;color:#333;margin-bottom:15px;">${para}</p>`)
    contentImages.filter((img, imgIndex) => Number(img.anchor_paragraph ?? defaultAnchors[imgIndex + 1]) === index + 1).forEach((img) => {
      parts.push(`<p style="text-align:center;margin:20px 0;"><img src="${resolveAssetUrl(img.url)}" style="max-width:100%;height:auto;border-radius:8px;" /></p>`)
    })
  })
  parts.push('</section>')
  return parts.join('\n')
}

export default function ArticleStudio() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [booting, setBooting] = useState(true)
  const [activeStep, setActiveStep] = useState(0)
  const [mode, setMode] = useState<Mode>('pro')
  const [article, setArticle] = useState<Article | null>(null)
  const [topic, setTopic] = useState('')
  const [category, setCategory] = useState('生活')
  const [title, setTitle] = useState('')
  const [outlineRequirement, setOutlineRequirement] = useState('')
  const [contentRequirement, setContentRequirement] = useState('')
  const [outlineSections, setOutlineSections] = useState<OutlineSection[]>([])
  const [contentBlocks, setContentBlocks] = useState<ContentBlock[]>([])
  const [workingMessage, setWorkingMessage] = useState('')
  const [quickProgress, setQuickProgress] = useState(0)
  const [rewriteRequirement, setRewriteRequirement] = useState('')

  const outline = useMemo(() => sectionsToOutline(outlineSections), [outlineSections])
  const content = useMemo(() => blocksToContent(contentBlocks), [contentBlocks])

  const qualityChecks = useMemo(() => {
    const issues: string[] = []
    const imageCount = article?.images?.length || 0
    if (!title.trim()) issues.push('标题未确认')
    if (outlineSections.length < 3) issues.push('大纲层次较少，建议至少 3 个小节')
    if (content.replace(/\s/g, '').length < 800) issues.push('正文字数偏少，建议 800 字以上')
    if (imageCount === 0) issues.push('还没有配图')
    if (!article?.content_html) issues.push('尚未生成公众号 HTML')
    return {
      titleLength: title.trim().length,
      wordCount: content.replace(/\s/g, '').length,
      imageCount,
      htmlReady: !!article?.content_html,
      issues,
    }
  }, [article?.content_html, article?.images, content, outlineSections.length, title])
  const previewHtml = useMemo(() => buildPreviewHtml(title, content, article?.images || []), [article?.images, content, title])
  const contentParagraphs = useMemo(() => content.split(/\n\s*\n/).map((item) => item.trim()).filter(Boolean), [content])

  const syncFromArticle = (data: Article) => {
    setArticle(data)
    setTopic(data.topic || '')
    setCategory(data.category || '生活')
    setTitle(data.title || '')
    setOutlineSections(outlineToSections(data.outline || ''))
    setContentBlocks(contentToBlocks(data.content_text || ''))

    if (data.content_html) setActiveStep(4)
    else if (data.images?.length) setActiveStep(3)
    else if (data.content_text) setActiveStep(2)
    else if (data.outline) setActiveStep(1)
    else setActiveStep(0)
  }

  const loadArticle = async (articleId: number) => {
    const { data } = await articleApi.get(articleId)
    syncFromArticle(data)
  }

  useEffect(() => {
    const init = async () => {
      try {
        const topicParam = searchParams.get('topic')
        const categoryParam = searchParams.get('category')
        const modeParam = searchParams.get('mode')
        if (topicParam) setTopic(topicParam)
        if (categoryParam) setCategory(categoryParam)
        if (modeParam === 'quick' || modeParam === 'pro') setMode(modeParam)
        if (id) await loadArticle(Number(id))
      } catch {
        message.error('加载文章工作台失败')
      } finally {
        setBooting(false)
      }
    }
    init()
  }, [id, searchParams])

  const createArticleIfNeeded = async () => {
    if (article) return article
    if (!topic.trim()) throw new Error('请输入文章主题')
    const { data } = await articleApi.create({ topic: topic.trim(), category })
    syncFromArticle(data)
    return data
  }

  const saveDraft = async () => {
    if (!article) return
    setLoading(true)
    try {
      const { data } = await articleApi.update(article.id, {
        title,
        outline,
        content_text: content,
        category,
      })
      syncFromArticle(data)
      message.success('草稿已保存')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateOutline = async () => {
    setLoading(true)
    setWorkingMessage('正在生成大纲...')
    try {
      const current = await createArticleIfNeeded()
      const result = await articleApi.generateOutlineStream(current.id, outlineRequirement, undefined)
      setTitle(result.title)
      setOutlineSections(outlineToSections(result.outline))
      await loadArticle(current.id)
      setActiveStep(1)
      message.success('大纲生成成功')
    } catch (error: any) {
      message.error(error.message || error.response?.data?.detail || '大纲生成失败')
    } finally {
      setLoading(false)
      setWorkingMessage('')
    }
  }

  const handleGenerateContent = async () => {
    setLoading(true)
    setWorkingMessage('正在生成正文...')
    try {
      const current = await createArticleIfNeeded()
      if (outlineSections.length && !article?.outline) {
        await articleApi.update(current.id, { title, outline, category })
      } else if (outlineSections.length) {
        await articleApi.update(current.id, { title, outline })
      }
      const result = await articleApi.generateContentStream(current.id, contentRequirement, undefined)
      setContentBlocks(contentToBlocks(result.content))
      await loadArticle(current.id)
      setActiveStep(2)
      message.success('正文生成成功')
    } catch (error: any) {
      message.error(error.message || error.response?.data?.detail || '正文生成失败')
    } finally {
      setLoading(false)
      setWorkingMessage('')
    }
  }

  const handleGenerateImages = async () => {
    if (!article) {
      message.warning('请先生成正文')
      return
    }
    setLoading(true)
    setWorkingMessage('正在生成配图...')
    try {
      await articleApi.update(article.id, { title, outline, content_text: content })
      const { data } = await articleApi.generateImages(article.id)
      await loadArticle(article.id)
      setActiveStep(3)
      message.success(data.failed > 0 ? `已生成 ${data.success} 张，失败 ${data.failed} 张` : '配图生成成功')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '配图生成失败')
    } finally {
      setLoading(false)
      setWorkingMessage('')
    }
  }

  const handleGenerateHtml = async () => {
    if (!article) return
    setLoading(true)
    setWorkingMessage('正在生成公众号 HTML...')
    try {
      await articleApi.update(article.id, { title, outline, content_text: content })
      await articleApi.generateHtml(article.id)
      await loadArticle(article.id)
      setActiveStep(4)
      message.success('排版生成成功')
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'HTML 生成失败')
    } finally {
      setLoading(false)
      setWorkingMessage('')
    }
  }

  const handleQuickGenerate = async () => {
    setLoading(true)
    setQuickProgress(5)
    setWorkingMessage('正在一键生成公众号初稿...')
    try {
      const current = await createArticleIfNeeded()
      setQuickProgress(20)
      const outlineResult = await articleApi.generateOutlineStream(current.id, outlineRequirement, undefined)
      setTitle(outlineResult.title)
      setOutlineSections(outlineToSections(outlineResult.outline))
      setQuickProgress(45)
      const contentResult = await articleApi.generateContentStream(current.id, contentRequirement, undefined)
      setContentBlocks(contentToBlocks(contentResult.content))
      setQuickProgress(70)
      await articleApi.generateImages(current.id)
      setQuickProgress(88)
      await articleApi.generateHtml(current.id)
      await loadArticle(current.id)
      setQuickProgress(100)
      setActiveStep(4)
      message.success('公众号初稿已生成完成')
    } catch (error: any) {
      message.error(error.message || error.response?.data?.detail || '一键生成失败')
    } finally {
      setLoading(false)
      setWorkingMessage('')
    }
  }

  const handleCopyHtml = async () => {
    if (!article?.content_html) {
      message.warning('请先生成公众号 HTML')
      return
    }
    const publishableHtml = buildPublishableHtml(article.content_html)
    try {
      await copyRichHtml(publishableHtml)
      message.success('已复制图文内容，可直接粘贴到公众号编辑器')
    } catch {
      message.error('复制失败，请检查浏览器权限')
    }
  }

  const handleRegenerateImage = async (index: number) => {
    if (!article) return
    setLoading(true)
    try {
      await articleApi.regenerateImage(article.id, index)
      await loadArticle(article.id)
      message.success('图片已重生成')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '重生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteImage = async (index: number) => {
    if (!article) return
    setLoading(true)
    try {
      await articleApi.deleteImage(article.id, index)
      await loadArticle(article.id)
      message.success('图片已删除')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败')
    } finally {
      setLoading(false)
    }
  }

  const handleMoveImage = async (from: number, to: number) => {
    if (!article?.images) return
    const images = [...article.images]
    const [moved] = images.splice(from, 1)
    images.splice(to, 0, moved)
    setLoading(true)
    try {
      await articleApi.updateImages(article.id, images)
      await loadArticle(article.id)
      message.success('图片顺序已更新')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '调整失败')
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateImageAnchor = async (index: number, anchor: number) => {
    if (!article?.images) return
    const images = article.images.map((img, i) => i === index ? { ...img, anchor_paragraph: anchor, position: anchor } : img)
    setArticle({ ...article, images })
    setLoading(true)
    try {
      await articleApi.updateImages(article.id, images)
      await loadArticle(article.id)
      message.success('图片插入位置已更新')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '更新位置失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRewriteOutlineSection = async (section: OutlineSection) => {
    if (!article) {
      message.warning('请先创建文章草稿')
      return
    }
    setLoading(true)
    try {
      await articleApi.update(article.id, { title, outline, category })
      const { data } = await articleApi.rewriteOutlineSection(article.id, {
        section_text: section.text,
        requirement: rewriteRequirement || undefined,
      })
      setOutlineSections((prev) => prev.map((item) => item.id === section.id ? { ...item, text: data.section_text } : item))
      message.success('该小节已重写')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '重写失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRewriteContentBlock = async (block: ContentBlock) => {
    if (!article) {
      message.warning('请先创建文章草稿')
      return
    }
    setLoading(true)
    try {
      await articleApi.update(article.id, { title, outline, content_text: content, category })
      const { data } = await articleApi.rewriteContentSection(article.id, {
        section_text: block.text,
        article_title: title,
        requirement: rewriteRequirement || undefined,
      })
      setContentBlocks((prev) => prev.map((item) => item.id === block.id ? { ...item, text: data.section_text } : item))
      message.success('该段内容已重写')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '重写失败')
    } finally {
      setLoading(false)
    }
  }

  const moveOutlineSection = (from: number, to: number) => {
    setOutlineSections((prev) => {
      const next = [...prev]
      const [moved] = next.splice(from, 1)
      next.splice(to, 0, moved)
      return next
    })
  }

  const addOutlineSection = () => setOutlineSections((prev) => [...prev, { id: uid('outline'), text: '' }])
  const addContentBlock = () => setContentBlocks((prev) => [...prev, { id: uid('block'), text: '' }])

  if (booting) {
    return <div className="flex items-center justify-center h-64"><Progress type="circle" percent={80} /></div>
  }

  return (
    <div style={{ padding: 24, maxWidth: 1480, margin: '0 auto' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card style={{ borderRadius: 24, background: 'linear-gradient(135deg, #173654 0%, #2a6d86 52%, #efb46a 100%)', color: '#fff' }}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
              <div>
                <Title level={3} style={{ margin: 0, color: '#fff' }}>公众号内容工作台</Title>
                <Text style={{ color: 'rgba(255,255,255,0.88)' }}>支持快速出稿，也支持大纲、正文、配图、排版的分步精修。</Text>
              </div>
              <Space wrap>
                <Segmented
                  value={mode}
                  onChange={(value) => setMode(value as Mode)}
                  options={[
                    { label: '快速模式', value: 'quick' },
                    { label: '专业模式', value: 'pro' },
                  ]}
                />
                {article && <Tag color="blue">文章 ID {article.id}</Tag>}
                <Button onClick={() => navigate('/article/history')}>历史文章</Button>
              </Space>
            </div>
            <Steps current={activeStep} items={steps} />
            {workingMessage && <Alert type="info" message={workingMessage} showIcon />}
            {loading && mode === 'quick' && quickProgress > 0 ? <Progress percent={quickProgress} /> : null}
          </Space>
        </Card>

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) 380px', gap: 24, alignItems: 'start' }}>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Card title="1. 主题设定" extra={activeStep > 0 ? <Tag color="green">已创建</Tag> : null} style={{ borderRadius: 20 }}>
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <CategorySelector value={category} onChange={setCategory} onTopicSelect={setTopic} />
                <TextArea value={topic} onChange={(e) => setTopic(e.target.value)} rows={4} placeholder="输入文章主题，比如：为什么成年人越忙越要阅读" />
                <Space wrap>
                  <Button type="primary" icon={<RocketOutlined />} onClick={handleQuickGenerate} loading={loading} disabled={!topic.trim()}>一键生成初稿</Button>
                  <Button onClick={createArticleIfNeeded} loading={loading} disabled={!topic.trim()}>创建文章草稿</Button>
                </Space>
                <div>
                  <Text type="secondary">局部重写风格</Text>
                  <Input value={rewriteRequirement} onChange={(e) => setRewriteRequirement(e.target.value)} placeholder="例如：更口语化、更有故事感、更适合转发" />
                </div>
              </Space>
            </Card>

            <Card title="2. 大纲确认" extra={<Space><Button icon={<PlusOutlined />} onClick={addOutlineSection}>新增小节</Button><Button icon={<SaveOutlined />} onClick={saveDraft} disabled={!article}>保存</Button></Space>} style={{ borderRadius: 20 }}>
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <TextArea value={outlineRequirement} onChange={(e) => setOutlineRequirement(e.target.value)} rows={2} placeholder="补充要求：比如更偏观点型、加入案例、强调实操" />
                <Space wrap>
                  <Button type="primary" icon={<ReloadOutlined />} onClick={handleGenerateOutline} loading={loading} disabled={!topic.trim()}>生成大纲</Button>
                  <Button onClick={() => setActiveStep(2)} disabled={!outlineSections.length}>进入正文</Button>
                </Space>
                {outlineSections.length ? outlineSections.map((section, index) => (
                  <Card key={section.id} size="small" title={`小节 ${index + 1}`} extra={<Space><Button size="small" icon={<ReloadOutlined />} onClick={() => handleRewriteOutlineSection(section)} loading={loading}>AI重写</Button><Button size="small" disabled={index === 0} onClick={() => moveOutlineSection(index, index - 1)}>上移</Button><Button size="small" disabled={index === outlineSections.length - 1} onClick={() => moveOutlineSection(index, index + 1)}>下移</Button><Popconfirm title="删除这个小节？" onConfirm={() => setOutlineSections((prev) => prev.filter((item) => item.id !== section.id))}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm></Space>}>
                    <Input.TextArea value={section.text} rows={2} onChange={(e) => setOutlineSections((prev) => prev.map((item) => item.id === section.id ? { ...item, text: e.target.value } : item))} placeholder="这一节想讲什么" />
                  </Card>
                )) : <Empty description="先生成大纲，或者手动新增小节" />}
              </Space>
            </Card>

            <Card title="3. 正文精修" extra={<Space><Button icon={<PlusOutlined />} onClick={addContentBlock}>新增段落</Button><Button icon={<SaveOutlined />} onClick={saveDraft} disabled={!article}>保存</Button></Space>} style={{ borderRadius: 20 }}>
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="文章标题" />
                <TextArea value={contentRequirement} onChange={(e) => setContentRequirement(e.target.value)} rows={2} placeholder="补充要求：比如更口语化、更有故事感、适合转发" />
                <Space wrap>
                  <Button type="primary" icon={<EditOutlined />} onClick={handleGenerateContent} loading={loading} disabled={!outlineSections.length}>生成正文</Button>
                  <Button onClick={() => setActiveStep(3)} disabled={!contentBlocks.length}>进入配图</Button>
                </Space>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  <Tag color={qualityChecks.wordCount >= 800 ? 'green' : 'orange'}>字数 {qualityChecks.wordCount}</Tag>
                  <Tag color={qualityChecks.titleLength >= 12 && qualityChecks.titleLength <= 28 ? 'green' : 'orange'}>标题 {qualityChecks.titleLength} 字</Tag>
                </div>
                {contentBlocks.length ? contentBlocks.map((block, index) => (
                  <Card key={block.id} size="small" title={`段落 ${index + 1}`} extra={<Space><Button size="small" icon={<ReloadOutlined />} onClick={() => handleRewriteContentBlock(block)} loading={loading}>AI重写</Button><Popconfirm title="删除这个段落？" onConfirm={() => setContentBlocks((prev) => prev.filter((item) => item.id !== block.id))}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm></Space>}>
                    <Input.TextArea value={block.text} rows={6} onChange={(e) => setContentBlocks((prev) => prev.map((item) => item.id === block.id ? { ...item, text: e.target.value } : item))} placeholder="正文段落" />
                  </Card>
                )) : <Empty description="先生成正文，或者手动新增段落" />}
              </Space>
            </Card>

            <Card title="4. 配图管理" extra={<Space><Button icon={<SaveOutlined />} onClick={saveDraft} disabled={!article}>保存</Button><Button onClick={() => setActiveStep(4)} disabled={!article?.images?.length}>进入排版</Button></Space>} style={{ borderRadius: 20 }}>
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Alert type="info" message="建议正文稳定后再生成配图。每张图都可以单独重生、删除和调整顺序。" showIcon />
                <Space wrap>
                  <Button type="primary" icon={<FileImageOutlined />} onClick={handleGenerateImages} loading={loading} disabled={!contentBlocks.length}>生成配图</Button>
                </Space>
                {article?.images?.length ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
                    {article.images.map((img, index) => (
                      <Card key={`${img.url}-${index}`} size="small" title={img.type === 'cover' ? '封面图' : `内容图 ${index + 1}`} extra={<Tag>{index + 1}</Tag>}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <img src={resolveAssetUrl(img.url)} alt={`article-${index}`} style={{ width: '100%', borderRadius: 10, border: '1px solid #eee' }} />
                          {img.type !== 'cover' && (
                            <select
                              value={Number(img.anchor_paragraph ?? Math.min(index, contentParagraphs.length || 1))}
                              onChange={(e) => handleUpdateImageAnchor(index, Number(e.target.value))}
                              style={{ width: '100%', padding: 8, borderRadius: 8, border: '1px solid #d9d9d9' }}
                            >
                              {contentParagraphs.map((_, pIndex) => (
                                <option key={pIndex + 1} value={pIndex + 1}>{`插入到第 ${pIndex + 1} 段后`}</option>
                              ))}
                            </select>
                          )}
                          <Text type="secondary" style={{ fontSize: 12 }}>存储位置：{img.storage === 'cos' ? 'COS 可发布地址' : '本地预览地址'}</Text>
                          <Space wrap>
                            <Button size="small" icon={<ReloadOutlined />} onClick={() => handleRegenerateImage(index)} loading={loading}>重生</Button>
                            <Button size="small" disabled={index === 0} onClick={() => handleMoveImage(index, index - 1)}>上移</Button>
                            <Button size="small" disabled={index === article.images!.length - 1} onClick={() => handleMoveImage(index, index + 1)}>下移</Button>
                            <Popconfirm title="删除这张图片？" onConfirm={() => handleDeleteImage(index)}><Button size="small" danger icon={<DeleteOutlined />}>删除</Button></Popconfirm>
                          </Space>
                        </Space>
                      </Card>
                    ))}
                  </div>
                ) : <Empty description="还没有配图，先生成正文后再出图" />}
              </Space>
            </Card>

            <Card title="5. 排版与导出" extra={<Button icon={<CopyOutlined />} type="primary" onClick={handleCopyHtml} disabled={!article?.content_html}>复制图文内容</Button>} style={{ borderRadius: 20 }}>
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Alert type={article?.content_html ? 'success' : 'warning'} message={article?.content_html ? '排版已准备好，可以复制到公众号编辑器' : '请先生成 HTML 再进行发布'} showIcon />
                <Space wrap>
                  <Button type="primary" icon={<CheckOutlined />} onClick={handleGenerateHtml} loading={loading} disabled={!contentBlocks.length}>生成公众号 HTML</Button>
                  {article && <Button onClick={() => navigate(`/article/${article.id}`)}>查看详情页</Button>}
                </Space>
              </Space>
            </Card>
          </Space>

          <Space direction="vertical" size="large" style={{ width: '100%', position: 'sticky', top: 16 }}>
            <Card title="质量检查" style={{ borderRadius: 20, border: '1px solid #d7e6ef', background: 'linear-gradient(180deg, #f8fcff 0%, #ffffff 100%)' }}>
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><Text type="secondary">标题长度</Text><Text>{qualityChecks.titleLength}</Text></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><Text type="secondary">正文字数</Text><Text>{qualityChecks.wordCount}</Text></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><Text type="secondary">配图数量</Text><Text>{qualityChecks.imageCount}</Text></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><Text type="secondary">HTML 状态</Text><Tag color={qualityChecks.htmlReady ? 'green' : 'orange'}>{qualityChecks.htmlReady ? '已生成' : '未生成'}</Tag></div>
                <Divider style={{ margin: '8px 0' }} />
                {qualityChecks.issues.length ? qualityChecks.issues.map((issue) => <Alert key={issue} type="warning" message={issue} />) : <Alert type="success" message="当前内容已具备较好的发布条件" />}
              </Space>
            </Card>

            <Card title="手机预览" bodyStyle={{ padding: 12 }} style={{ borderRadius: 20, border: '1px solid #d7e6ef', background: 'linear-gradient(180deg, #f8fcff 0%, #ffffff 100%)' }}>
              <div style={{ height: 680 }}>
                <PhonePreview article={article} htmlContent={previewHtml} />
              </div>
            </Card>
          </Space>
        </div>
      </Space>
    </div>
  )
}
