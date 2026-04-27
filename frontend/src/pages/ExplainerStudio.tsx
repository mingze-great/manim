import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Input, InputNumber, Select, Space, Spin, Tag, Upload, message } from 'antd'
import { ArrowLeftOutlined, PlayCircleOutlined, ReloadOutlined, RocketOutlined, UploadOutlined } from '@ant-design/icons'
import { Project, projectApi } from '@/services/project'
import { getAppBase } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'
import './Creator/Creator.css'

type Storyboard = Record<string, any>
type ImageAsset = Record<string, any>

function resolveAssetUrl(url?: string | null) {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `${getAppBase()}${url}`
}

export default function ExplainerStudio() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [project, setProject] = useState<Project | null>(null)
  const [storyboards, setStoryboards] = useState<Storyboard[]>([])
  const [imageAssets, setImageAssets] = useState<ImageAsset[]>([])
  const [title, setTitle] = useState('')
  const [finalScript, setFinalScript] = useState('')
  const [styleNotes, setStyleNotes] = useState('')
  const [composeProgress, setComposeProgress] = useState(0)
  const [composeMessage, setComposeMessage] = useState('')

  const flags = useMemo(() => {
    try {
      return JSON.parse(project?.generation_flags || '{}')
    } catch {
      return {}
    }
  }, [project?.generation_flags])

  const loadProject = async () => {
    const { data } = await projectApi.get(Number(id))
    setProject(data)
    setTitle(data.title || '')
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
        await loadProject()
      } catch {
        message.error('加载讲解型视频工作台失败')
      } finally {
        setLoading(false)
      }
    }
    run()
  }, [id])

  const updateScene = (index: number, patch: Partial<Storyboard>) => {
    setStoryboards((prev) => prev.map((item, i) => i === index ? { ...item, ...patch } : item))
  }

  const handleGenerateStoryboard = async () => {
    setSaving(true)
    try {
      const { data } = await projectApi.generateExplainerStoryboard(Number(id), {
        opening_hook_mode: flags.opening_hook_mode || 'hook_question',
        visual_style_key: flags.visual_style_key || 'deep_blue_emotional',
      })
      setProject(data)
      setTitle(data.title || '')
      setFinalScript(data.final_script || '')
      setStoryboards(JSON.parse(data.storyboard_json || '[]'))
      message.success('开头与分镜已生成')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成分镜失败')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveStoryboard = async () => {
    setSaving(true)
    try {
      const { data } = await projectApi.updateExplainerStoryboard(Number(id), {
        title,
        final_script: finalScript,
        storyboards,
      })
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
      const { data } = await projectApi.generateExplainerImages(Number(id))
      setProject(data)
      setStoryboards(JSON.parse(data.storyboard_json || '[]'))
      setImageAssets(JSON.parse(data.image_assets_json || '[]'))
      message.success('讲解型分镜图已生成')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成图片失败')
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

  const handleRegenerateImage = async (index: number) => {
    setSaving(true)
    try {
      const { data } = await projectApi.regenerateExplainerImage(Number(id), index, { prompt: storyboards[index]?.visual_prompt })
      setProject(data)
      setStoryboards(JSON.parse(data.storyboard_json || '[]'))
      setImageAssets(JSON.parse(data.image_assets_json || '[]'))
      message.success(`第 ${index + 1} 张图片已重生`)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '重生图片失败')
    } finally {
      setSaving(false)
    }
  }

  const handleCompose = async () => {
    setSaving(true)
    setComposeProgress(1)
    setComposeMessage('正在启动讲解型视频合成...')
    try {
      const token = useAuthStore.getState().token || ''
      const response = await fetch(projectApi.generateExplainerComposeStream(Number(id)), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!response.ok) throw new Error('启动合成失败')
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
            message.success('讲解型视频已合成完成')
          }
          if (parsed.type === 'error') throw new Error(parsed.content || '合成失败')
        }
      }
      await loadProject()
    } catch (error: any) {
      message.error(error.message || '讲解型视频合成失败')
      setComposeMessage(error.message || '讲解型视频合成失败')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="flex items-center justify-center h-64"><Spin size="large" /></div>

  return (
    <div className="creator-page">
      <div className="creator-hero creator-hero-sunrise">
        <div className="hero-content">
          <h1 className="hero-title">讲解型视频分步工作台</h1>
          <p className="hero-subtitle">先把开头和节奏调顺，再生成图片，最后合成并复看前 3 秒效果。</p>
        </div>
      </div>

      <div className="creator-container space-y-6">
        <div className="flex gap-3 flex-wrap">
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/creator/stickman')}>返回视频讲解</Button>
          <Button onClick={() => navigate(`/project/${id}/task`)}>去任务页</Button>
        </div>

        <Alert type="success" message="讲解型视频分步工作台" description="风格、节奏和分镜都在这里统一调整，页面样式也与系统创作台保持一致。" />
        <Card className="stickman-panel" bordered={false} title={project?.title || '讲解型视频工作台'} extra={<Tag color="blue">抖音爆款导向</Tag>}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Card size="small" title="基础设置">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="视频标题 / 开头标题" />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <Select value={flags.opening_hook_mode || 'hook_question'} onChange={async (value) => {
                  const next = { ...flags, opening_hook_mode: value }
                  const { data } = await projectApi.update(Number(id), { generation_flags: JSON.stringify(next) } as any)
                  setProject(data)
                }} options={[{ label: '反问钩子', value: 'hook_question' }, { label: '数字爆点', value: 'big_number' }]} />
                <Select value={flags.visual_style_key || 'deep_blue_emotional'} onChange={async (value) => {
                  const next = { ...flags, visual_style_key: value }
                  const { data } = await projectApi.update(Number(id), { generation_flags: JSON.stringify(next) } as any)
                  setProject(data)
                }} options={[{ label: '深蓝情绪线稿', value: 'deep_blue_emotional' }, { label: '观点冷峻线稿', value: 'opinion_editorial' }, { label: '治愈成长线稿', value: 'growth_soft_glow' }]} />
                <InputNumber disabled value={Number(flags.target_duration || 0)} addonAfter="秒" style={{ width: '100%' }} />
              </div>
              <Button type="primary" icon={<RocketOutlined />} onClick={handleGenerateStoryboard} loading={saving}>生成开头与分镜</Button>
            </Space>
          </Card>

          <Card size="small" title="完整旁白脚本">
            <Input.TextArea rows={8} value={finalScript} onChange={(e) => setFinalScript(e.target.value)} placeholder="完整旁白脚本" />
          </Card>

          <Card size="small" title="风格与背景控制">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert type="info" message="这里是后续回归优化的主要抓手" description="如果前 3 秒停留感不够、画面不统一或情绪不对，可以通过风格参考图和背景图继续迭代。" />
              <Input.TextArea rows={3} value={styleNotes} onChange={(e) => setStyleNotes(e.target.value)} placeholder="补充风格说明，例如：深蓝底、白线稿、局部金色高亮、情绪化构图、字幕安全区固定" />
              <Space wrap>
                <Upload beforeUpload={handleUploadStyleReference} showUploadList={false} accept=".png,.jpg,.jpeg,.webp">
                  <Button icon={<UploadOutlined />} loading={saving}>上传风格参考图</Button>
                </Upload>
                <Upload beforeUpload={handleUploadBackgroundImage} showUploadList={false} accept=".png,.jpg,.jpeg,.webp">
                  <Button icon={<UploadOutlined />} loading={saving}>上传背景图</Button>
                </Upload>
              </Space>
            </Space>
          </Card>

          <Card size="small" title="分镜列表">
            <Space direction="vertical" style={{ width: '100%' }}>
              {storyboards.map((scene, index) => (
                <Card key={index} size="small" title={<Space><span>{scene.scene_title || `第${index + 1}幕`}</span><Tag color={scene.beat_type === 'hook' ? 'red' : scene.beat_type === 'payoff' ? 'green' : 'blue'}>{scene.beat_type || 'expand'}</Tag></Space>} extra={<Button size="small" icon={<ReloadOutlined />} onClick={() => handleRegenerateImage(index)} loading={saving}>重生单图</Button>}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Input value={scene.scene_title} onChange={(e) => updateScene(index, { scene_title: e.target.value })} placeholder="镜头标题" />
                    <Input value={scene.subtitle_text} onChange={(e) => updateScene(index, { subtitle_text: e.target.value })} placeholder="字幕短句" />
                    <Input.TextArea rows={3} value={scene.narration_text} onChange={(e) => updateScene(index, { narration_text: e.target.value })} placeholder="配音文案" />
                    <Input.TextArea rows={3} value={scene.visual_description} onChange={(e) => updateScene(index, { visual_description: e.target.value })} placeholder="画面描述" />
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                      <Input value={scene.punch_phrase} onChange={(e) => updateScene(index, { punch_phrase: e.target.value })} placeholder="击中句" />
                      <Select value={scene.camera_motion || 'slow_zoom_in'} onChange={(value) => updateScene(index, { camera_motion: value })} options={[{ label: '慢推近', value: 'slow_zoom_in' }, { label: '慢拉远', value: 'slow_zoom_out' }, { label: '平移左', value: 'pan_left' }, { label: '平移右', value: 'pan_right' }, { label: '轻景深', value: 'parallax_light' }]} />
                      <Select value={scene.energy_level || 'medium'} onChange={(value) => updateScene(index, { energy_level: value })} options={[{ label: '高能量', value: 'high' }, { label: '中能量', value: 'medium' }, { label: '低能量', value: 'low' }]} />
                      <InputNumber min={2} max={6} step={0.5} value={Number(scene.duration || 3.5)} onChange={(value) => updateScene(index, { duration: Number(value) || 3.5 })} style={{ width: '100%' }} />
                    </div>
                    {!!scene.image_url && <img src={resolveAssetUrl(scene.image_url)} alt={`scene-${index + 1}`} style={{ width: 220, borderRadius: 12, border: '1px solid #eee' }} />}
                  </Space>
                </Card>
              ))}
            </Space>
          </Card>

          <Space wrap>
            <Button onClick={handleSaveStoryboard} loading={saving}>保存分镜</Button>
            <Button type="primary" onClick={handleGenerateImages} loading={saving} disabled={!storyboards.length}>生成全部图片</Button>
            <Button icon={<PlayCircleOutlined />} onClick={handleCompose} loading={saving} disabled={!imageAssets.length}>合成视频</Button>
          </Space>

          {!!composeMessage && <Alert type={composeProgress >= 100 ? 'success' : 'info'} message={composeMessage} description={`当前进度 ${composeProgress}%`} />}
          {!!project?.video_url && <video src={resolveAssetUrl(project.video_url)} controls className="w-full rounded-xl shadow-lg" style={{ maxHeight: '60vh' }}>您的浏览器不支持视频播放</video>}
        </Space>
        </Card>
      </div>
    </div>
  )
}
