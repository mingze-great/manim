import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Input, Select, Space, Spin, Steps, Tag, Upload, message } from 'antd'
import { PlayCircleOutlined, PictureOutlined, RocketOutlined, UploadOutlined } from '@ant-design/icons'
import { Project, projectApi, StickmanVoiceOption } from '@/services/project'
import { getAppBase, resolveBackendUrl } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'
import './Creator/Creator.css'

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
  opening_template_key?: string
  background_prompt?: string
  foreground_subjects?: Array<{ key: string; kind: string; label: string }>
  foreground_events?: Array<{ target: string; animation: string; start: number; duration: number; x_ratio?: number; y_ratio?: number }>
  subtitle_lines?: Array<{ text: string; start?: number; end?: number }>
  scene_style_profile?: string
}

type ImageAsset = {
  image_url?: string
  image_path?: string
  scene_image_url?: string
  scene_image_path?: string
  prompt?: string
  used_fallback?: boolean
  image_source?: 'model' | 'fallback'
  model_used?: string | null
  model_requested?: string | null
  scene_image_source?: 'material_library' | 'model' | 'fallback'
  scene_image_model_used?: string | null
  error_summary?: string | null
}

function resolveAssetUrl(url?: string | null) {
  if (!url) return ''
  if (url.startsWith('http')) return url
  const base = getAppBase()
  return `${base}${url}`
}

function resolvePreferredPreviewUrl(asset?: ImageAsset | null) {
  return resolveAssetUrl(asset?.scene_image_url || asset?.image_url || '')
}

function resolveBackgroundUrl(path?: string | null) {
  if (!path) return ''
  const fileName = path.split(/[/\\]/).pop()
  if (!fileName) return ''
  const base = getAppBase()
  return `${base}/api/background-images/${fileName}`
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

  const openingTemplate = String(parsedFlags.opening_template_key || 'hook_question')

  const loadProject = async () => {
    const { data } = await projectApi.get(Number(id))
    setProject(data)
    setFinalScript(data.final_script || '')
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

  const handleUploadOpeningImage = async (file: File) => {
    setSaving(true)
    try {
      const { data } = await projectApi.uploadStickmanOpeningImage(Number(id), file)
      setProject(data)
      setPreviewImageAsset(data.preview_image_asset_json ? JSON.parse(data.preview_image_asset_json) : null)
      message.success('开头图已上传，后续会直接作为第一幕使用')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传开头图失败')
    } finally {
      setSaving(false)
    }
    return false
  }

  const handleUploadBackgroundImage = async (file: File) => {
    setSaving(true)
    try {
      const { data } = await projectApi.uploadBackgroundImage(Number(id), file)
      setProject(data)
      message.success('背景图已上传')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传背景图失败')
    } finally {
      setSaving(false)
    }
    return false
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
        text: '你好，这是当前视频讲解项目的配音试听。',
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

  const handleUpdateGenerationFlags = async (patch: Record<string, any>) => {
    if (!project) return
    const nextFlags = { ...parsedFlags, ...patch }
    try {
      const { data } = await projectApi.update(project.id, { generation_flags: JSON.stringify(nextFlags) } as Partial<Project>)
      setProject(data)
      message.success('优化版模板设置已更新')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '更新模板设置失败')
    }
  }

  useEffect(() => {
    return () => {
      if (previewAudioUrl) {
        URL.revokeObjectURL(previewAudioUrl)
      }
    }
  }, [previewAudioUrl])

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Spin size="large" /></div>
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <Alert type="success" message="增强讲解工作台" description="按 4 步完成：生成文案、确定开头图、上传背景图、开始生成成片。" />
      <Card
        title={project?.title || '视频讲解分步创作'}
        extra={<Space><Tag color="gold">分步创作</Tag><Button onClick={() => navigate(`/project/${id}/task`)}>去任务页</Button></Space>}
      >
        <div className="workflow-shell">
          <div className="workflow-main">
            <Alert type="info" message="只需要按这 4 步操作" description="1. 生成或粘贴文案  2. 确定开头图  3. 上传背景图  4. 开始生成视频。" />
            <Steps current={4} items={[{ title: '文案' }, { title: '开头图' }, { title: '背景图' }, { title: '开始生成' }]} />

            <Card size="small" title="第一步：生成文案或直接使用你的文案">
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Alert type="info" message="你可以完全使用自己的文案" description="如果你已经有完整文案，直接在下方编辑框里修改并保存即可；如果还没有，再点“生成脚本和分镜”。" />
                <Space>
                  <Button type="primary" icon={<RocketOutlined />} onClick={handleGenerateScript} loading={saving}>生成文案</Button>
                  <Button onClick={handleSaveStoryboards} loading={saving}>保存当前文案</Button>
                </Space>
                <Input.TextArea rows={8} value={finalScript} onChange={(e) => setFinalScript(e.target.value)} placeholder="完整脚本文案。你可以完全替换成自己的文案。" />
              </Space>
            </Card>

            <Card size="small" title="第二步：确定开头图">
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Alert type="info" message="开头图的作用" description="视频开头就是先展示这 1 张图。你可以让系统生成，也可以自己上传一张图，后续会直接作为第一幕使用。" />
                {resolvePreferredPreviewUrl(previewImageAsset) ? (
                  <img src={resolvePreferredPreviewUrl(previewImageAsset)} alt="opening-preview" style={{ width: '100%', borderRadius: 12, border: '1px solid #eee', maxWidth: 560 }} />
                ) : (
                  <div className="workflow-preview-box">还没有开头图</div>
                )}
                <Space wrap>
                  <Button type="primary" onClick={() => handleGeneratePreviewImage(false)} loading={saving} disabled={!storyboards.length}>生成开头图</Button>
                  <Button onClick={() => handleGeneratePreviewImage(true)} loading={saving} disabled={!previewImageAsset}>重生开头图</Button>
                  <Upload beforeUpload={handleUploadOpeningImage} showUploadList={false} accept=".png,.jpg,.jpeg,.webp">
                    <Button icon={<UploadOutlined />} loading={saving}>上传开头图</Button>
                  </Upload>
                </Space>
                {previewImageAsset?.error_summary && <Alert type="success" message={previewImageAsset.error_summary} />}
              </Space>
            </Card>

            <Card size="small" title="第三步：上传背景图">
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Alert type="info" message="背景图的作用" description="背景图会贯穿整条视频，后续每一幕都会在这张底图上叠加讲解元素。开头图决定第一眼，背景图决定整条视频的整体氛围。" />
                {project?.background_image_path ? (
                  <img src={resolveBackgroundUrl(project.background_image_path)} alt="background-reference" style={{ width: '100%', borderRadius: 12, border: '1px solid #eee', maxWidth: 560 }} />
                ) : (
                  <div className="workflow-preview-box">当前还没有自定义背景图，将使用默认背景</div>
                )}
                <Upload beforeUpload={handleUploadBackgroundImage} showUploadList={false} accept=".png,.jpg,.jpeg,.webp">
                  <Button icon={<UploadOutlined />} loading={saving}>上传背景图</Button>
                </Upload>
              </Space>
            </Card>

            <Card size="small" title="第四步：开始生成">
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Alert type="success" message="默认风格说明" description="如果你不上传开头图，系统会自动生成默认风格的开头图。" />
                <Space wrap>
                  <Button type="primary" icon={<PictureOutlined />} onClick={handleGenerateImages} loading={saving} disabled={!storyboards.length}>开始生成图片</Button>
                  <Button type="primary" onClick={handleComposeVideo} loading={saving} disabled={!imageAssets.length}>开始生成视频</Button>
                </Space>
                {!!composeProgress && <div>当前进度：{composeProgress}% {composeMessage}</div>}
                {project?.video_url && <video src={resolveBackendUrl(project.video_url)} controls className="workflow-video-preview" />}
              </Space>
            </Card>
          </div>

          <div className="workflow-side">
          <Card size="small" title="当前设置摘要">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Tag color="gold">增强讲解</Tag>
              <Tag color="blue">16:9 横屏</Tag>
              <Alert type="info" message="开头钩子" description="这里只保留对用户真正有帮助的开头钩子选择。" />
              <Select
                value={openingTemplate}
                onChange={(value) => handleUpdateGenerationFlags({ opening_template_key: value })}
                options={[
                  { label: '反问钩子型', value: 'hook_question' },
                  { label: '爆点数字型', value: 'big_number' },
                ]}
                style={{ width: 260 }}
              />
              <Alert type="success" message="图片说明" description="开头图决定用户第一眼看到什么；背景图决定整条视频的整体氛围。" />
            </Space>
          </Card>
          <Card size="small" title="配音设置">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Select
                value={project?.tts_voice}
                onChange={(value) => {
                  const selectedVoice = voiceLibrary.find((item) => item.value === value)
                  handleUpdateVoiceConfig({ tts_voice: value, tts_provider: selectedVoice?.provider || 'dashscope_cosyvoice' })
                }}
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
          </div>
        </div>
      </Card>
    </div>
  )
}
