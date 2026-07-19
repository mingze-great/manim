import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Alert, Button, Card, Drawer, Grid, Input, Progress, Select, Space, Steps, Typography, message } from 'antd'
import { CopyOutlined, FileImageOutlined, FileTextOutlined, RocketOutlined } from '@ant-design/icons'
import { resolveBackendUrl } from '@/services/api'
import { Article, articleApi } from '@/services/article'
import PhonePreview from './components/PhonePreview'
import { copyRichHtml } from '@/utils/copyRichHtml'

const { TextArea } = Input
const { Title, Text } = Typography

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

function buildPreviewHtml(title: string, content: string, images: NonNullable<Article['images']>) {
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

export default function ArticleQuick() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const screens = Grid.useBreakpoint()
  const isMobile = !screens.lg
  const [loading, setLoading] = useState(false)
  const [article, setArticle] = useState<Article | null>(null)
  const [topic, setTopic] = useState('')
  const [category, setCategory] = useState('生活')
  const [requirement, setRequirement] = useState('')
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [step, setStep] = useState(0)
  const [progress, setProgress] = useState(0)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [charCount, setCharCount] = useState(0)
  const [streamPhase, setStreamPhase] = useState<'idle' | 'outline' | 'content' | 'done'>('idle')

  useEffect(() => {
    const t = searchParams.get('topic')
    const c = searchParams.get('category')
    if (t) setTopic(t)
    if (c) setCategory(c)
  }, [searchParams])

  const previewHtml = useMemo(() => buildPreviewHtml(title, content, article?.images || []), [article?.images, content, title])
  const paragraphs = useMemo(() => content.split(/\n\s*\n/).map((item) => item.trim()).filter(Boolean), [content])

  const createDraft = async () => {
    if (!topic.trim()) {
      message.warning('请输入文章主题')
      return
    }
    setLoading(true)
    setProgress(5)
    setCharCount(0)
    setTitle('')
    setContent('')
    try {
      const { data: created } = await articleApi.create({ topic: topic.trim(), category })
      setArticle(created)
      setStep(1)
      setStreamPhase('outline')
      setProgress(20)
      const outlineResult = await articleApi.generateOutlineStream(created.id, requirement || undefined, (full, count) => {
        setTitle(full.split('\n')[0]?.replace(/^标题[:：]?/, '').replace(/^#+/, '').replace(/\*/g, '').trim() || '')
        setCharCount(count)
      })
      setStreamPhase('content')
      setProgress(50)
      setTitle((outlineResult.title || '').replace(/^#+/, '').replace(/\*/g, '').trim())
      const contentResult = await articleApi.generateContentStream(created.id, requirement || undefined, (full, count) => {
        setContent(full)
        setCharCount(count)
      })
      const { data } = await articleApi.get(created.id)
      setArticle(data)
      setContent(contentResult.content)
      setStep(1)
      setProgress(100)
      setStreamPhase('done')
      message.success('文案草稿已生成，可继续编辑')
    } catch (error: any) {
      setStreamPhase('idle')
      message.error(error.response?.data?.detail || error.message || '生成文案草稿失败')
    } finally {
      setLoading(false)
    }
  }

  const saveContent = async () => {
    if (!article) return
    setLoading(true)
    try {
      const { data } = await articleApi.update(article.id, { title, content_text: content, category })
      setArticle(data)
      message.success('文案已保存')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败')
    } finally {
      setLoading(false)
    }
  }

  const generateImages = async () => {
    if (!article) return
    setLoading(true)
    try {
      await articleApi.update(article.id, { title, content_text: content, category })
      await articleApi.generateImages(article.id)
      const { data } = await articleApi.get(article.id)
      setArticle(data)
      setStep(2)
      message.success('配图已生成，可调整插入位置')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '配图生成失败')
    } finally {
      setLoading(false)
    }
  }

  const updateImagePlacement = async (index: number, anchor: number) => {
    if (!article?.images) return
    const next = article.images.map((img, i) => i === index ? { ...img, anchor_paragraph: anchor, position: anchor } : img)
    setArticle({ ...article, images: next })
    try {
      await articleApi.updateImages(article.id, next)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '更新图片位置失败')
    }
  }

  const regenerateImage = async (index: number) => {
    if (!article) return
    setLoading(true)
    try {
      await articleApi.regenerateImage(article.id, index)
      const { data } = await articleApi.get(article.id)
      setArticle(data)
      message.success('图片已重生成')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '重生成失败')
    } finally {
      setLoading(false)
    }
  }

  const generateHtml = async () => {
    if (!article) return
    setLoading(true)
    try {
      await articleApi.update(article.id, { title, content_text: content, category })
      await articleApi.generateHtml(article.id)
      const { data } = await articleApi.get(article.id)
      setArticle(data)
      setStep(3)
      message.success('排版生成完成')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '排版生成失败')
    } finally {
      setLoading(false)
    }
  }

  const copyHtml = async () => {
    if (!article?.content_html) return message.warning('请先生成 HTML')
    const publishableHtml = buildPublishableHtml(article.content_html)
    try {
      await copyRichHtml(publishableHtml)
      message.success('已复制图文内容，可直接粘贴到公众号编辑器')
    } catch {
      message.error('复制失败，请检查浏览器权限')
    }
  }

  return (
    <div style={{ maxWidth: 1360, margin: '0 auto', padding: isMobile ? '12px 12px 88px' : 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card style={{ borderRadius: 24, background: 'linear-gradient(135deg, #163d5a 0%, #276d87 55%, #efb46a 100%)', color: '#fff', overflow: 'hidden' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
              <div>
                <Title level={3} style={{ margin: 0, color: '#fff' }}>公众号轻量版</Title>
                <Text style={{ color: 'rgba(255,255,255,0.88)' }}>先生成可编辑文案，再确认配图位置，最后手机预览和导出。</Text>
              </div>
              <Space>
                <Button onClick={() => navigate(`/article/studio${article ? `?topic=${encodeURIComponent(topic)}&category=${encodeURIComponent(category)}` : ''}`)}>进入专业版</Button>
              </Space>
            </div>
            <Steps current={step} items={[{ title: '文案草稿' }, { title: '文案确认' }, { title: '配图确认' }, { title: '排版导出' }]} />
            {loading && progress > 0 ? <Progress percent={progress} /> : null}
          </Space>
        </Card>

        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'minmax(0, 1.8fr) 380px', gap: 24 }}>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Card title="1. 生成文案草稿" style={{ borderRadius: 20, border: '1px solid #e6eef4' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Select value={category} onChange={setCategory} options={[
                  { label: '生活', value: '生活' }, { label: '职场', value: '职场' }, { label: '健康', value: '健康' }, { label: '育儿', value: '育儿' }, { label: '两性情感', value: '两性情感' }, { label: '体育', value: '体育' },
                ]} style={{ width: 220 }} />
                <TextArea value={topic} onChange={(e) => setTopic(e.target.value)} rows={3} placeholder="输入文章主题" />
                <TextArea value={requirement} onChange={(e) => setRequirement(e.target.value)} rows={2} placeholder="可选：补充风格要求，比如更口语化、更适合转发" />
                <Space wrap>
                  <Button type="primary" icon={<RocketOutlined />} onClick={createDraft} loading={loading}>生成文案草稿</Button>
                  <Button onClick={() => { if (!article) setStep(1) }}>我自己写文案</Button>
                  {isMobile && <Button onClick={() => setPreviewOpen(true)}>查看预览</Button>}
                </Space>
                {!!charCount && <Text type="secondary">实时输出字数：{charCount}</Text>}
                {streamPhase !== 'idle' && streamPhase !== 'done' && (
                  <Alert
                    type="info"
                    showIcon
                    message={streamPhase === 'outline' ? '正在生成标题与大纲...' : '正在生成正文内容...'}
                    description="文案会直接流式写入下方编辑区，你可以在生成完成后继续修改。"
                  />
                )}
              </Space>
            </Card>

            {step >= 1 && (
              <Card title="2. 文案确认" style={{ borderRadius: 20, border: '1px solid #e6eef4' }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Alert type="info" message="这里是给普通用户的轻量编辑区。你可以直接修改标题和正文，也可以粘贴你自己的完整文案。" showIcon />
                  <Input value={title} onChange={(e) => setTitle(e.target.value.replace(/^#+/, '').replace(/\*/g, ''))} placeholder="文章标题" />
                  <div className="text-sm text-gray-500">当前字数：{charCount || content.replace(/\s/g, '').length}</div>
                  <TextArea value={content} onChange={(e) => setContent(e.target.value)} rows={isMobile ? 10 : 16} placeholder="正文内容" />
                  <Space wrap>
                    <Button icon={<FileTextOutlined />} onClick={saveContent} loading={loading} disabled={!article}>保存文案</Button>
                    <Button type="primary" icon={<FileImageOutlined />} onClick={generateImages} loading={loading} disabled={!content.trim() || !article}>确认文案并生成配图</Button>
                    {isMobile && <Button onClick={() => setPreviewOpen(true)}>查看预览</Button>}
                  </Space>
                </Space>
              </Card>
            )}

            {step >= 2 && (
              <Card title="3. 配图确认" style={{ borderRadius: 20, border: '1px solid #e6eef4' }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Alert type="info" message="每张图片都可以调整插入位置，生成后右侧手机预览会同步变化。" showIcon />
                  <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
                    {article?.images?.map((img, index) => (
                      <Card key={`${img.url}-${index}`} size="small" title={img.type === 'cover' ? '封面图' : `内容图 ${index + 1}`} extra={<Button size="small" icon={<RocketOutlined />} onClick={() => regenerateImage(index)} loading={loading}>重生</Button>}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <img src={resolveAssetUrl(img.url)} alt={`img-${index}`} style={{ width: '100%', borderRadius: 10, border: '1px solid #eee' }} />
                          {img.type !== 'cover' && (
                            <Select
                              value={Number(img.anchor_paragraph ?? Math.min(index + 1, paragraphs.length || 1))}
                              onChange={(value) => updateImagePlacement(index, value)}
                              options={paragraphs.map((para, pIndex) => ({ label: `第 ${pIndex + 1} 段后：${para.slice(0, 14)}...`, value: pIndex + 1 }))}
                            />
                          )}
                          <Text type="secondary" style={{ fontSize: 12 }}>存储位置：{img.storage === 'cos' ? 'COS 可发布地址' : '本地预览地址'}</Text>
                          {img.related_text && <Text type="secondary" style={{ fontSize: 12 }}>对应文案：{img.related_text}</Text>}
                        </Space>
                      </Card>
                    ))}
                  </div>
                  <Space wrap>
                    <Button type="primary" icon={<CopyOutlined />} onClick={generateHtml} loading={loading} disabled={!article?.images?.length}>确认配图并生成预览</Button>
                    {isMobile && <Button onClick={() => setPreviewOpen(true)}>查看预览</Button>}
                  </Space>
                </Space>
              </Card>
            )}

            {step >= 3 && (
              <Card title="4. 排版导出" style={{ borderRadius: 20, border: '1px solid #e6eef4' }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Alert type="success" message="已经生成公众号排版，可以直接复制，也可以进入专业版继续精修。" showIcon />
                  <Space wrap>
                    <Button type="primary" icon={<CopyOutlined />} onClick={copyHtml}>复制图文内容</Button>
                    {article && <Button onClick={() => navigate(`/article/${article.id}`)}>进入专业版精修</Button>}
                    {isMobile && <Button onClick={() => setPreviewOpen(true)}>查看预览</Button>}
                  </Space>
                </Space>
              </Card>
            )}
          </Space>

          {!isMobile && (
            <Card title="手机预览" bodyStyle={{ padding: 12 }} style={{ borderRadius: 20, border: '1px solid #d7e6ef', background: 'linear-gradient(180deg, #f7fbfd 0%, #ffffff 100%)' }}>
              <div style={{ height: 720 }}>
                <PhonePreview article={article} htmlContent={previewHtml} />
              </div>
            </Card>
          )}
        </div>
        {isMobile && (
          <>
            <div style={{ position: 'fixed', left: 0, right: 0, bottom: 0, padding: '10px 12px', background: 'rgba(255,255,255,0.98)', borderTop: '1px solid #e5e7eb', zIndex: 1000 }}>
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Button onClick={() => setPreviewOpen(true)}>预览</Button>
                {step < 1 && <Button type="primary" onClick={createDraft} loading={loading}>生成草稿</Button>}
                {step === 1 && <Button type="primary" onClick={generateImages} loading={loading} disabled={!content.trim() || !article}>生成配图</Button>}
                {step === 2 && <Button type="primary" onClick={generateHtml} loading={loading} disabled={!article?.images?.length}>生成排版</Button>}
                {step >= 3 && <Button type="primary" onClick={copyHtml}>复制图文</Button>}
              </Space>
            </div>
            <Drawer title="手机预览" placement="bottom" height="85vh" open={previewOpen} onClose={() => setPreviewOpen(false)}>
              <div style={{ height: '100%' }}>
                <PhonePreview article={article} htmlContent={previewHtml} />
              </div>
            </Drawer>
          </>
        )}
      </Space>
    </div>
  )
}
