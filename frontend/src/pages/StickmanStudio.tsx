import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Col, Input, Row, Select, Space, Spin, Steps, Tabs, Tag, Upload, message } from 'antd'
import { EditOutlined, PlayCircleOutlined, PictureOutlined, RocketOutlined, UploadOutlined } from '@ant-design/icons'
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
  const base = import.meta.env.VITE_API_BASE_URL || ''
  return `${base}${url}`
}

function resolveStyleReferenceUrl(path?: string | null) {
  if (!path) return ''
  const fileName = path.split(/[/\\]/).pop()
  if (!fileName) return ''
  const base = import.meta.env.VITE_API_BASE_URL || ''
  return `${base}/api/style-reference-images/${fileName}`
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
          <Alert type="info" message="你现在处于分步创作模式" description="可以先生成脚本与分镜，再逐段调整，最后生成图片和视频。" />
          <Steps current={imageAssets.length ? 2 : storyboards.length ? 1 : 0} items={[{ title: '生成脚本' }, { title: '确认分镜' }, { title: '生成图片' }, { title: '去任务页合成' }]} />
          <Card size="small" title="参考风格图">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert type="info" message="上传一张参考图后，系统会把它当成主要风格来源；如果不上传，则继续使用默认火柴人风格。" />
              {project?.style_reference_image_path && (
                <img src={resolveStyleReferenceUrl(project.style_reference_image_path)} alt="style-reference" style={{ width: 240, borderRadius: 12, border: '1px solid #eee' }} />
              )}
              {project?.style_reference_profile && (
                <Alert type="success" message="已提取到参考图风格特征" description={project.style_reference_profile} />
              )}
              <Input.TextArea rows={3} value={styleNotes} onChange={(e) => setStyleNotes(e.target.value)} placeholder="可选：补充说明想保留的风格特点，例如极简线稿、暖色调、手绘感" />
              <Upload beforeUpload={handleUploadStyleReference} showUploadList={false} accept=".png,.jpg,.jpeg,.webp">
                <Button icon={<UploadOutlined />} loading={saving}>上传风格参考图</Button>
              </Upload>
            </Space>
          </Card>
          <Card size="small" title="风格预览图">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert type="info" message="先生成 1 张预览图确认风格，满意后再生成全部分镜图，能明显降低图片成本。" />
              {previewImageAsset?.image_url ? (
                <img src={resolveAssetUrl(previewImageAsset.image_url)} alt="preview-scene" style={{ width: '100%', maxWidth: 420, borderRadius: 12, border: '1px solid #eee' }} />
              ) : (
                <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fafafa', borderRadius: 12 }}>尚未生成风格预览图</div>
              )}
              <Space wrap>
                <Button type="primary" onClick={() => handleGeneratePreviewImage(false)} loading={saving} disabled={!storyboards.length}>生成预览图</Button>
                <Button onClick={() => handleGeneratePreviewImage(true)} loading={saving} disabled={!previewImageAsset || (!useAuthStore.getState().user?.is_admin && (project?.preview_regen_count || 0) >= 1)}>重生预览图</Button>
                {!!previewImageAsset && <Tag color="green">预览图已生成</Tag>}
                {!useAuthStore.getState().user?.is_admin && <Tag color="orange">普通用户仅可重生 1 次预览图</Tag>}
              </Space>
              {previewImageAsset?.error_summary && <Alert type="warning" message={previewImageAsset.error_summary} />}
            </Space>
          </Card>
          <Card size="small" title="视频合成">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Card size="small" title="配音设置">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Select
                    value={project?.tts_voice}
                    onChange={(value) => handleUpdateVoiceConfig({ tts_voice: value, tts_provider: 'dashscope_cosyvoice' })}
                    options={voiceLibrary}
                    style={{ width: '100%' }}
                  />
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
                  <Space>
                    <Button icon={<PlayCircleOutlined />} onClick={handlePreviewVoice}>试听当前音色</Button>
                    {previewAudioUrl && <audio controls src={previewAudioUrl} />}
                  </Space>
                </Space>
              </Card>
              <Button type="primary" onClick={handleComposeVideo} loading={saving} disabled={!imageAssets.length}>直接合成视频</Button>
              {!!composeProgress && <div>合成进度：{composeProgress}% {composeMessage}</div>}
              {project?.video_url && <video src={project.video_url.startsWith('http') ? project.video_url : `${import.meta.env.VITE_API_BASE_URL || ''}${project.video_url}`} controls style={{ width: '100%', borderRadius: 12 }} />}
            </Space>
          </Card>

          <Tabs
            items={[
              {
                key: 'script',
                label: '脚本与分镜',
                children: (
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <Space>
                      <Button type="primary" icon={<RocketOutlined />} onClick={handleGenerateScript} loading={saving}>生成脚本和分镜</Button>
                      <Button onClick={handleSaveStoryboards} loading={saving}>保存修改</Button>
                    </Space>
                    <Input.TextArea rows={5} value={finalScript} onChange={(e) => setFinalScript(e.target.value)} placeholder="完整脚本文案" />
                    <Row gutter={[16, 16]}>
                      {storyboards.map((scene, index) => (
                        <Col span={12} key={scene.scene_id || index}>
                          <Card title={scene.scene_title || `第${index + 1}幕`} extra={<Tag>{scene.camera_type || '镜头未设定'}</Tag>}>
                            <Space direction="vertical" style={{ width: '100%' }}>
                              <Input value={scene.scene_title} onChange={(e) => updateScene(index, { scene_title: e.target.value })} placeholder="分镜标题" />
                              <Input.TextArea rows={3} value={scene.scene_description} onChange={(e) => updateScene(index, { scene_description: e.target.value })} placeholder="场景描述" />
                              <Input.TextArea rows={3} value={scene.narration} onChange={(e) => updateScene(index, { narration: e.target.value })} placeholder="旁白" />
                              <Input value={scene.camera_type} onChange={(e) => updateScene(index, { camera_type: e.target.value })} placeholder="镜头类型" />
                              <Input value={scene.character_action} onChange={(e) => updateScene(index, { character_action: e.target.value })} placeholder="人物动作" />
                              <Input value={scene.layout_hint} onChange={(e) => updateScene(index, { layout_hint: e.target.value })} placeholder="构图提示" />
                              <Select
                                value={scene.duration_range || '2-4'}
                                onChange={(value) => updateScene(index, { duration_range: value })}
                                options={[
                                  { label: '1-2 秒', value: '1-2' },
                                  { label: '2-4 秒', value: '2-4' },
                                  { label: '4-6 秒', value: '4-6' },
                                ]}
                                style={{ width: '100%' }}
                              />
                            </Space>
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  </Space>
                ),
              },
              {
                key: 'images',
                label: '图片控制',
                children: (
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <Space>
                      <Button type="primary" icon={<PictureOutlined />} onClick={handleGenerateImages} loading={saving} disabled={!storyboards.length || !previewImageAsset}>生成全部图片</Button>
                      <Button onClick={handleRegenerateFallbackImages} loading={saving} disabled={!imageAssets.some((asset) => asset?.used_fallback) || !useAuthStore.getState().user?.is_admin}>只重生降级图</Button>
                      <Tag color={parsedFlags.image_fallback_used ? 'orange' : 'green'}>
                        {parsedFlags.image_fallback_used ? '包含降级图片' : '真实图片生成'}
                      </Tag>
                      {!!parsedFlags.fallback_count && <Tag color="red">{parsedFlags.fallback_count} 张为降级图</Tag>}
                    </Space>
                    {parsedFlags.image_fallback_used && (
                      <Alert
                        type="warning"
                        message="当前开发环境图片模型并非全部真实生成"
                        description="检测到至少一张图走了降级占位图。通常是图片模型额度、权限或可用性问题导致。你仍可编辑 prompt 后单张重生。"
                      />
                    )}
                    <Row gutter={[16, 16]}>
                      {storyboards.map((scene, index) => {
                        const asset = imageAssets[index]
                        return (
                          <Col span={12} key={`image-${scene.scene_id || index}`}>
                             <Card title={scene.scene_title || `第${index + 1}幕`} extra={<Button size="small" icon={<EditOutlined />} onClick={() => handleRegenerateImage(index)} loading={saving} disabled={!useAuthStore.getState().user?.is_admin}>重生图片</Button>}>
                              <Space direction="vertical" style={{ width: '100%' }}>
                                {asset?.image_url ? <img src={resolveAssetUrl(asset.image_url)} alt={scene.scene_title || `scene-${index + 1}`} style={{ width: '100%', borderRadius: 12, border: '1px solid #eee' }} /> : <div style={{ height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fafafa', borderRadius: 12 }}>未生成图片</div>}
                                <Space wrap>
                                  <Tag color={asset?.used_fallback ? 'orange' : 'green'}>{asset?.used_fallback ? '降级占位图' : '真实模型图'}</Tag>
                                  {asset?.model_used && <Tag>{asset.model_used}</Tag>}
                                  {asset?.image_source && <Tag>{asset.image_source === 'model' ? '模型生成' : '占位降级'}</Tag>}
                                </Space>
                                <Input.TextArea rows={4} value={asset?.prompt || ''} onChange={(e) => setImageAssets((prev) => prev.map((item, i) => i === index ? { ...item, prompt: e.target.value } : item))} placeholder="图片提示词" />
                                {asset?.error_summary && <Alert type={asset?.used_fallback ? 'warning' : 'info'} message={asset.error_summary} />}
                              </Space>
                            </Card>
                          </Col>
                        )
                      })}
                    </Row>
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
