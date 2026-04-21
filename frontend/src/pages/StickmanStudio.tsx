import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Col, Input, Row, Select, Space, Spin, Steps, Tabs, Tag, Upload, message, Progress } from 'antd'
import { EditOutlined, PlayCircleOutlined, PictureOutlined, RocketOutlined, UploadOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons'
import { motion, AnimatePresence } from 'framer-motion'
import { Project, projectApi, StickmanVoiceOption } from '@/services/project'
import { useAuthStore } from '@/stores/authStore'

type Storyboard = {
  scene_id: number
  scene_title?: string
  scene_description: string
  narration: string
  camera_type?: string
  character_action?: string
  layout_hint?: string
  visual_focus?: string
  keywords?: string[]
  duration_range?: string
}

type ImageAsset = {
  image_url?: string
  image_path?: string
  prompt?: string
  used_fallback?: boolean
  image_source?: 'model' | 'fallback'
  model_used?: string | null
  error_summary?: string | null
}

function resolveAssetUrl(url?: string | null) {
  if (!url) return ''
  if (url.startsWith('http')) return url
  if (url.startsWith('data:')) return url
  const base = import.meta.env.VITE_API_BASE_URL || ''
  return `${base}${url}`
}

function resolveStyleReferenceUrl(path?: string | null) {
  if (!path) return ''
  if (path.startsWith('http')) return path
  const fileName = path.split(/[/\\]/).pop()
  if (!fileName) return ''
  const base = import.meta.env.VITE_API_BASE_URL || ''
  return `${base}/api/style-reference-images/${fileName}`
}

function StoryboardPreview({ 
  storyboards, 
  imageAssets, 
  currentIndex, 
  onPrev, 
  onNext 
}: { 
  storyboards: Storyboard[]
  imageAssets: ImageAsset[]
  currentIndex: number
  onPrev: () => void
  onNext: () => void
}) {
  const scene = storyboards[currentIndex]
  const asset = imageAssets[currentIndex]
  const imageUrl = asset?.image_url ? resolveAssetUrl(asset.image_url) : null
  const [imageError, setImageError] = useState(false)
  
  if (!scene) return null
  
  return (
    <div className="relative w-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl overflow-hidden" style={{ minHeight: 400 }}>
      <AnimatePresence mode="wait">
        <motion.div
          key={currentIndex}
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -50 }}
          transition={{ duration: 0.3 }}
          className="absolute inset-0 flex items-center justify-center p-6"
        >
          {imageUrl && !imageError ? (
            <img 
              src={imageUrl} 
              alt={scene.scene_title || `场景 ${currentIndex + 1}`}
              className="max-w-full max-h-[350px] object-contain rounded-xl shadow-2xl"
              onError={() => {
                console.error('[StickmanStudio] Image load failed:', imageUrl)
                setImageError(true)
              }}
            />
          ) : (
            <div className="flex flex-col items-center justify-center text-gray-400">
              <PictureOutlined style={{ fontSize: 64, marginBottom: 16 }} />
              <span>{imageError ? '图片加载失败' : '未生成图片'}</span>
              {imageError && imageUrl && (
                <span className="text-xs mt-2 text-red-400 max-w-[300px] break-all">{imageUrl}</span>
              )}
            </div>
          )}
        </motion.div>
      </AnimatePresence>
      
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
        <div className="text-white">
          <h3 className="text-lg font-bold mb-1">{scene.scene_title || `第${currentIndex + 1}幕`}</h3>
          <p className="text-sm text-gray-300 line-clamp-2">{scene.narration}</p>
        </div>
      </div>
      
      <div className="absolute top-1/2 -translate-y-1/2 left-2">
        <Button 
          type="text" 
          icon={<LeftOutlined style={{ color: 'white', fontSize: 20 }} />}
          onClick={onPrev}
          disabled={currentIndex === 0}
          className="bg-black/30 hover:bg-black/50"
        />
      </div>
      
      <div className="absolute top-1/2 -translate-y-1/2 right-2">
        <Button 
          type="text" 
          icon={<RightOutlined style={{ color: 'white', fontSize: 20 }} />}
          onClick={onNext}
          disabled={currentIndex >= storyboards.length - 1}
          className="bg-black/30 hover:bg-black/50"
        />
      </div>
      
      <div className="absolute top-4 right-4 bg-black/50 px-3 py-1 rounded-full text-white text-sm">
        {currentIndex + 1} / {storyboards.length}
      </div>
    </div>
  )
}

export default function StickmanStudio() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [project, setProject] = useState<Project | null>(null)
  const [storyboards, setStoryboards] = useState<Storyboard[]>([])
  const [imageAssets, setImageAssets] = useState<ImageAsset[]>([])
  const [finalScript, setFinalScript] = useState('')
  const [styleNotes, setStyleNotes] = useState('')
  const [voiceLibrary, setVoiceLibrary] = useState<StickmanVoiceOption[]>([])
  const [previewAudioUrl, setPreviewAudioUrl] = useState<string | null>(null)
  const [previewImageAsset, setPreviewImageAsset] = useState<ImageAsset | null>(null)
  const [composeProgress, setComposeProgress] = useState(0)
  const [composeMessage, setComposeMessage] = useState('')
  const [previewIndex, setPreviewIndex] = useState(0)
  const [activeTab, setActiveTab] = useState('script')

  const parsedFlags = useMemo(() => {
    try {
      return JSON.parse(project?.generation_flags || '{}')
    } catch {
      return {}
    }
  }, [project?.generation_flags])

  const loadProject = async () => {
    const { data } = await projectApi.get(Number(id))
    setProject(data)
    setFinalScript(data.final_script || '')
    setStyleNotes(data.style_reference_notes || '')
    try {
      setStoryboards(JSON.parse(data.storyboard_json || '[]'))
    } catch {
      setStoryboards([])
    }
    try {
      setImageAssets(JSON.parse(data.image_assets_json || '[]'))
    } catch {
      setImageAssets([])
    }
  }

  useEffect(() => {
    const run = async () => {
      try {
        const [projectRes, voiceRes] = await Promise.all([
          projectApi.get(Number(id)),
          projectApi.getStickmanVoiceLibrary(),
        ])
        const data = projectRes.data
        setVoiceLibrary(voiceRes.data.voices || [])
        setProject(data)
        setFinalScript(data.final_script || '')
        setStyleNotes(data.style_reference_notes || '')
        try {
          setStoryboards(JSON.parse(data.storyboard_json || '[]'))
        } catch {
          setStoryboards([])
        }
        try {
          setImageAssets(JSON.parse(data.image_assets_json || '[]'))
        } catch {
          setImageAssets([])
        }
        try {
          setPreviewImageAsset(data.preview_image_asset_json ? JSON.parse(data.preview_image_asset_json) : null)
        } catch {
          setPreviewImageAsset(null)
        }
      } catch {
        message.error('加载分步创作页失败')
      } finally {
        setLoading(false)
      }
    }
    run()
  }, [id])

  const updateScene = (index: number, patch: Partial<Storyboard>) => {
    setStoryboards((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)))
  }

  const handleGenerateScript = async () => {
    setSaving(true)
    try {
      const { data } = await projectApi.generateStickmanScript(Number(id))
      setProject(data)
      setFinalScript(data.final_script || '')
      setStoryboards(JSON.parse(data.storyboard_json || '[]'))
      message.success('脚本和分镜已生成')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成脚本失败')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveStoryboards = async () => {
    setSaving(true)
    try {
      const { data } = await projectApi.updateStickmanStoryboards(Number(id), { storyboards, final_script: finalScript })
      setProject(data)
      message.success('分镜已保存')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存分镜失败')
    } finally {
      setSaving(false)
    }
  }

  const handleGenerateImages = async () => {
    setSaving(true)
    try {
      const { data } = await projectApi.generateStickmanImages(Number(id))
      setProject(data)
      setImageAssets(JSON.parse(data.image_assets_json || '[]'))
      message.success('分镜图片已生成')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成图片失败')
    } finally {
      setSaving(false)
    }
  }

  const handleGeneratePreviewImage = async (regenerate = false) => {
    setSaving(true)
    try {
      const { data } = await projectApi.generateStickmanPreviewImage(Number(id), regenerate)
      setProject(data)
      setPreviewImageAsset(data.preview_image_asset_json ? JSON.parse(data.preview_image_asset_json) : null)
      message.success(regenerate ? '预览图已重生' : '预览图已生成')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成预览图失败')
    } finally {
      setSaving(false)
    }
  }

  const handleUploadStyleReference = async (file: File) => {
    setSaving(true)
    try {
      const { data } = await projectApi.uploadStyleReference(Number(id), file, styleNotes)
      setProject(data)
      setStyleNotes(data.style_reference_notes || '')
      message.success('风格参考图已上传')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传风格参考图失败')
    } finally {
      setSaving(false)
    }
    return false
  }

  const handleRegenerateImage = async (index: number) => {
    setSaving(true)
    try {
      const { data } = await projectApi.regenerateStickmanImage(Number(id), index, { prompt: imageAssets[index]?.prompt })
      setProject(data)
      setImageAssets(JSON.parse(data.image_assets_json || '[]'))
      message.success(`第 ${index + 1} 张图片已重生成`)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '重生成图片失败')
    } finally {
      setSaving(false)
    }
  }

  const handleRegenerateFallbackImages = async () => {
    const fallbackIndexes = imageAssets.map((asset, index) => asset?.used_fallback ? index : -1).filter((index) => index >= 0)
    if (!fallbackIndexes.length) {
      message.info('当前没有降级图需要重生')
      return
    }

    setSaving(true)
    try {
      for (const index of fallbackIndexes) {
        const { data } = await projectApi.regenerateStickmanImage(Number(id), index, { prompt: imageAssets[index]?.prompt })
        setProject(data)
        setImageAssets(JSON.parse(data.image_assets_json || '[]'))
      }
      message.success(`已重生 ${fallbackIndexes.length} 张降级图`)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '批量重生降级图失败')
    } finally {
      setSaving(false)
    }
  }

  const handleComposeVideo = async () => {
    setSaving(true)
    setComposeProgress(1)
    setComposeMessage('正在启动合成任务...')
    try {
      const token = useAuthStore.getState().token || ''
      const response = await fetch(projectApi.generateStickmanComposeStream(Number(id)), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!response.ok) throw new Error('启动视频合成失败')
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) throw new Error('无法读取合成响应')
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const parsed = JSON.parse(line.slice(6))
          if (parsed.type === 'progress') {
            setComposeProgress(parsed.progress || 0)
            setComposeMessage(parsed.content || '合成中')
          }
          if (parsed.type === 'success') {
            setComposeProgress(100)
            setComposeMessage(parsed.content || '合成完成')
            message.success('视频已合成完成')
          }
          if (parsed.type === 'error') {
            throw new Error(parsed.content || '合成失败')
          }
        }
      }
      await loadProject()
    } catch (error: any) {
      message.error(error.message || '视频合成失败')
      setComposeMessage(error.message || '视频合成失败')
    } finally {
      setSaving(false)
    }
  }

  const handlePreviewVoice = async () => {
    if (!project) return
    try {
      const { data } = await projectApi.previewStickmanVoice({
        text: '你好，这是当前火柴人视频的配音试听。',
        tts_provider: project.tts_provider,
        tts_voice: project.tts_voice,
        tts_rate: project.tts_rate,
      })
      const url = URL.createObjectURL(data as any)
      setPreviewAudioUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev)
        return url
      })
      message.success('试听音频已生成')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成试听失败')
    }
  }

  const getCurrentStep = () => {
    if (imageAssets.length > 0) return 3
    if (previewImageAsset) return 2
    if (storyboards.length > 0) return 1
    return 0
  }

  const handlePrevPreview = () => {
    setPreviewIndex((prev) => Math.max(0, prev - 1))
  }

  const handleNextPreview = () => {
    setPreviewIndex((prev) => Math.min(storyboards.length - 1, prev + 1))
  }

  const handleUpdateVoiceConfig = async (patch: Partial<Project>) => {
    if (!project) return
    const next = { ...project, ...patch }
    setProject(next)
    try {
      const { data } = await projectApi.update(project.id, patch)
      setProject(data)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '更新配音设置失败')
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Spin size="large" /></div>
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <Card
        title={project?.title || '火柴人分步创作'}
        extra={<Space><Tag color="gold">分步创作</Tag><Button onClick={() => navigate(`/project/${id}/task`)}>去任务页</Button></Space>}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Alert type="info" message="分步创作流程" description="按顺序完成：文案生成 → 风格设置 → 图片生成 → 视频合成" />
          
          <Steps 
            current={getCurrentStep()} 
            items={[
              { title: '文案生成', description: storyboards.length ? '已完成' : '待生成' },
              { title: '风格设置', description: previewImageAsset ? '已确认' : '待设置' },
              { title: '图片生成', description: imageAssets.length ? `${imageAssets.length}张已生成` : '待生成' },
              { title: '视频合成', description: project?.video_url ? '已完成' : '待合成' },
            ]} 
          />

          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'script',
                label: '文案生成',
                children: (
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <Alert type="info" message="第一步：生成文案和分镜文字描述" description="系统将根据主题生成完整脚本文案和分镜文字描述（场景标题、描述、旁白等）" />
                    <Space>
                      <Button type="primary" icon={<RocketOutlined />} onClick={handleGenerateScript} loading={saving}>
                        {storyboards.length ? '重新生成文案' : '生成文案和分镜'}
                      </Button>
                      {storyboards.length > 0 && (
                        <Button onClick={handleSaveStoryboards} loading={saving}>保存修改</Button>
                      )}
                    </Space>
                    
                    {storyboards.length > 0 && (
                      <>
                        <div className="font-medium text-gray-700">完整脚本文案</div>
                        <Input.TextArea rows={5} value={finalScript} onChange={(e) => setFinalScript(e.target.value)} placeholder="完整脚本文案" />
                        
                        <div className="font-medium text-gray-700 mt-4">分镜文字描述（可编辑）</div>
                        <Row gutter={[16, 16]}>
                          {storyboards.map((scene, index) => (
                            <Col span={12} key={scene.scene_id || index}>
                              <Card 
                                size="small"
                                title={scene.scene_title || `第${index + 1}幕`} 
                                extra={<Tag color="blue">{scene.duration_range || '2-4'}秒</Tag>}
                              >
                                <Space direction="vertical" style={{ width: '100%' }} size="small">
                                  <Input value={scene.scene_title} onChange={(e) => updateScene(index, { scene_title: e.target.value })} placeholder="分镜标题" />
                                  <Input.TextArea rows={2} value={scene.scene_description} onChange={(e) => updateScene(index, { scene_description: e.target.value })} placeholder="场景描述" />
                                  <Input.TextArea rows={2} value={scene.narration} onChange={(e) => updateScene(index, { narration: e.target.value })} placeholder="旁白文案" />
                                  <Row gutter={8}>
                                    <Col span={12}>
                                      <Input value={scene.camera_type} onChange={(e) => updateScene(index, { camera_type: e.target.value })} placeholder="镜头类型" size="small" />
                                    </Col>
                                    <Col span={12}>
                                      <Select
                                        value={scene.duration_range || '2-4'}
                                        onChange={(value) => updateScene(index, { duration_range: value })}
                                        options={[
                                          { label: '1-2秒', value: '1-2' },
                                          { label: '2-4秒', value: '2-4' },
                                          { label: '4-6秒', value: '4-6' },
                                        ]}
                                        size="small"
                                        style={{ width: '100%' }}
                                      />
                                    </Col>
                                  </Row>
                                </Space>
                              </Card>
                            </Col>
                          ))}
                        </Row>
                        
                        <div className="flex justify-end">
                          <Button type="primary" onClick={() => setActiveTab('style')}>
                            下一步：风格设置 →
                          </Button>
                        </div>
                      </>
                    )}
                  </Space>
                ),
              },
              {
                key: 'style',
                label: '风格设置',
                children: (
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <Alert type="info" message="第二步：设置图片风格" description="上传风格参考图（可选），生成预览图确认风格满意后再生成全部图片" />
                    
                    <Card size="small" title="风格参考图（可选）">
                      <Space direction="vertical" style={{ width: '100%' }}>
                        {project?.style_reference_image_path && (
                          <img src={resolveStyleReferenceUrl(project.style_reference_image_path)} alt="style-reference" style={{ width: 240, borderRadius: 12, border: '1px solid #eee' }} />
                        )}
                        {project?.style_reference_profile && (
                          <Alert type="success" message="已提取风格特征" description={project.style_reference_profile} />
                        )}
                        <Input.TextArea rows={2} value={styleNotes} onChange={(e) => setStyleNotes(e.target.value)} placeholder="风格说明：如极简线稿、暖色调、手绘感" />
                        <Upload beforeUpload={handleUploadStyleReference} showUploadList={false} accept=".png,.jpg,.jpeg,.webp">
                          <Button icon={<UploadOutlined />} loading={saving}>上传风格参考图</Button>
                        </Upload>
                      </Space>
                    </Card>
                    
                    <Card size="small" title="风格预览图">
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Alert type="warning" message="建议先生成预览图确认风格，满意后再生成全部图片，可节省成本" />
                        {previewImageAsset?.image_url ? (
                          <img src={resolveAssetUrl(previewImageAsset.image_url)} alt="preview" style={{ width: '100%', maxWidth: 420, borderRadius: 12 }} />
                        ) : (
                          <div className="h-48 flex items-center justify-center bg-gray-50 rounded-xl text-gray-400">
                            {storyboards.length ? '点击下方按钮生成预览图' : '请先生成文案'}
                          </div>
                        )}
                        <Space wrap>
                          <Button type="primary" onClick={() => handleGeneratePreviewImage(false)} loading={saving} disabled={!storyboards.length}>
                            生成预览图
                          </Button>
                          <Button onClick={() => handleGeneratePreviewImage(true)} loading={saving} disabled={!previewImageAsset}>
                            重新生成
                          </Button>
                          {previewImageAsset && <Tag color="green">预览图已生成</Tag>}
                        </Space>
                        {previewImageAsset?.error_summary && <Alert type="warning" message={previewImageAsset.error_summary} />}
                      </Space>
                    </Card>
                    
                    <div className="flex justify-between">
                      <Button onClick={() => setActiveTab('script')}>
                        ← 上一步：文案生成
                      </Button>
                      <Button type="primary" onClick={() => setActiveTab('images')} disabled={!previewImageAsset}>
                        下一步：图片生成 →
                      </Button>
                    </div>
                  </Space>
                ),
              },
              {
                key: 'images',
                label: '图片生成',
                children: (
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <Alert type="info" message="第三步：生成分镜图片" description="根据分镜文字描述生成对应图片，支持单张重生和提示词编辑" />
                    
                    <Space wrap>
                      <Button type="primary" icon={<PictureOutlined />} onClick={handleGenerateImages} loading={saving} disabled={!storyboards.length || !previewImageAsset}>
                        生成全部图片
                      </Button>
                      {imageAssets.some((asset) => asset?.used_fallback) && (
                        <Button onClick={handleRegenerateFallbackImages} loading={saving} disabled={!useAuthStore.getState().user?.is_admin}>
                          重生降级图
                        </Button>
                      )}
                      <Tag color={parsedFlags.image_fallback_used ? 'orange' : 'green'}>
                        {parsedFlags.image_fallback_used ? '包含降级图' : '真实图片'}
                      </Tag>
                    </Space>
                    
                    {imageAssets.length > 0 && (
                      <>
                        <div className="font-medium text-gray-700">图片预览（统一背景展示）</div>
                        <StoryboardPreview
                          storyboards={storyboards}
                          imageAssets={imageAssets}
                          currentIndex={previewIndex}
                          onPrev={handlePrevPreview}
                          onNext={handleNextPreview}
                        />
                        
                        <div className="font-medium text-gray-700 mt-4">单张图片编辑</div>
                        <Row gutter={[16, 16]}>
                          {storyboards.map((scene, index) => {
                            const asset = imageAssets[index]
                            return (
                              <Col span={8} key={`image-${scene.scene_id || index}`}>
                                <Card 
                                  size="small"
                                  hoverable
                                  className={previewIndex === index ? 'ring-2 ring-blue-500' : ''}
                                  onClick={() => setPreviewIndex(index)}
                                >
                                  {asset?.image_url ? (
                                    <img src={resolveAssetUrl(asset.image_url)} alt={scene.scene_title} className="w-full h-32 object-cover rounded" />
                                  ) : (
                                    <div className="h-32 flex items-center justify-center bg-gray-100 rounded text-gray-400">
                                      未生成
                                    </div>
                                  )}
                                  <div className="mt-2 text-sm font-medium truncate">{scene.scene_title || `第${index + 1}幕`}</div>
                                  <Space size={4} className="mt-1">
                                    <Tag color={asset?.used_fallback ? 'orange' : 'green'} style={{ fontSize: 10 }}>
                                      {asset?.used_fallback ? '降级' : '真实'}
                                    </Tag>
                                    <Button 
                                      size="small" 
                                      type="link" 
                                      icon={<EditOutlined />}
                                      onClick={(e) => { e.stopPropagation(); handleRegenerateImage(index) }}
                                      loading={saving}
                                    >
                                      重生
                                    </Button>
                                  </Space>
                                  <Input.TextArea 
                                    rows={2} 
                                    value={asset?.prompt || ''} 
                                    onChange={(e) => setImageAssets((prev) => prev.map((item, i) => i === index ? { ...item, prompt: e.target.value } : item))} 
                                    placeholder="图片提示词"
                                    size="small"
                                    className="mt-2"
                                    onClick={(e) => e.stopPropagation()}
                                  />
                                </Card>
                              </Col>
                            )
                          })}
                        </Row>
                      </>
                    )}
                    
                    <div className="flex justify-between">
                      <Button onClick={() => setActiveTab('style')}>
                        ← 上一步：风格设置
                      </Button>
                      <Button type="primary" onClick={() => setActiveTab('compose')} disabled={!imageAssets.length}>
                        下一步：视频合成 →
                      </Button>
                    </div>
                  </Space>
                ),
              },
              {
                key: 'compose',
                label: '视频合成',
                children: (
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <Alert type="info" message="第四步：合成视频" description="设置配音参数，合成最终视频" />
                    
                    <Card size="small" title="配音设置">
                      <Row gutter={16}>
                        <Col span={12}>
                          <div className="text-sm text-gray-500 mb-1">AI音色</div>
                          <Select
                            value={project?.tts_voice}
                            onChange={(value) => handleUpdateVoiceConfig({ tts_voice: value, tts_provider: 'dashscope_cosyvoice' })}
                            options={voiceLibrary}
                            style={{ width: '100%' }}
                          />
                        </Col>
                        <Col span={12}>
                          <div className="text-sm text-gray-500 mb-1">语速</div>
                          <Select
                            value={project?.tts_rate || '+0%'}
                            onChange={(value) => handleUpdateVoiceConfig({ tts_rate: value })}
                            options={[
                              { label: '偏慢', value: '-15%' },
                              { label: '标准', value: '+0%' },
                              { label: '偏快', value: '+15%' },
                            ]}
                            style={{ width: '100%' }}
                          />
                        </Col>
                      </Row>
                      <div className="mt-3">
                        <Button icon={<PlayCircleOutlined />} onClick={handlePreviewVoice}>试听音色</Button>
                        {previewAudioUrl && <audio controls src={previewAudioUrl} className="ml-2" />}
                      </div>
                    </Card>
                    
                    <Space>
                      <Button type="primary" size="large" onClick={handleComposeVideo} loading={saving} disabled={!imageAssets.length}>
                        合成视频
                      </Button>
                    </Space>
                    
                    {composeProgress > 0 && (
                      <Card size="small">
                        <div className="flex items-center gap-3">
                          <Progress percent={composeProgress} style={{ flex: 1 }} />
                          <span className="text-sm text-gray-500">{composeMessage}</span>
                        </div>
                      </Card>
                    )}
                    
                    {project?.video_url && (
                      <Card size="small" title="生成的视频">
                        <video 
                          src={project.video_url.startsWith('http') ? project.video_url : `${import.meta.env.VITE_API_BASE_URL || ''}${project.video_url}`} 
                          controls 
                          className="w-full rounded-xl" 
                        />
                      </Card>
                    )}
                    
                    <div className="flex justify-start">
                      <Button onClick={() => setActiveTab('images')}>
                        ← 上一步：图片生成
                      </Button>
                    </div>
                  </Space>
                ),
              },
            ]}
          />
        </Space>
      </Card>
    </div>
  )
}
