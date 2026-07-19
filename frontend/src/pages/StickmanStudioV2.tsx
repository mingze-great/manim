import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Input, Progress, Select, Space, Spin, Steps, Tag, Upload, message } from 'antd'
import { PlayCircleOutlined, RocketOutlined, UploadOutlined } from '@ant-design/icons'
import { Project, projectApi, StickmanVoiceOption } from '@/services/project'
import { getAppBase, resolveBackendUrl } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'
import AudioRecorder from './Creator/components/AudioRecorder'
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
  subtitle_lines?: Array<{ text: string; english?: string; start?: number; end?: number }>
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
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({})
  const [project, setProject] = useState<Project | null>(null)
  const [storyboards, setStoryboards] = useState<Storyboard[]>([])
  const [imageAssets, setImageAssets] = useState<ImageAsset[]>([])
  const [finalScript, setFinalScript] = useState('')
  const [lastProcessedScript, setLastProcessedScript] = useState('')
  const [voiceLibrary, setVoiceLibrary] = useState<StickmanVoiceOption[]>([])
  const [previewAudioUrl, setPreviewAudioUrl] = useState<string | null>(null)
  const [localVoiceFile, setLocalVoiceFile] = useState<File | null>(null)
  const [backgroundPreviewUrl, setBackgroundPreviewUrl] = useState<string | null>(null)
  const [composeProgress, setComposeProgress] = useState(0)
  const [composeMessage, setComposeMessage] = useState('')
  const [isComposing, setIsComposing] = useState(false)
  const [activeComposeTaskId, setActiveComposeTaskId] = useState<number | null>(null)
  const composeAbortRef = useRef<AbortController | null>(null)
  const scriptSaveTimerRef = useRef<number | null>(null)
  const suppressScriptAutosaveRef = useRef(false)

  const parsedFlags = useMemo(() => {
    try {
      return JSON.parse(project?.generation_flags || '{}')
    } catch {
      return {}
    }
  }, [project?.generation_flags])
  const safeVoiceOptions = useMemo(
    () => (voiceLibrary || [])
      .map((item) => ({
        label: String(item?.label || item?.value || '').trim(),
        value: String(item?.value || '').trim(),
        provider: String(item?.provider || 'dashscope_cosyvoice').trim(),
        preview_url: typeof item?.preview_url === 'string' ? item.preview_url : undefined,
      }))
      .filter((item) => item.label && item.value),
    [voiceLibrary],
  )

  const normalizedCurrentScript = finalScript.trim()
  const normalizedProcessedScript = lastProcessedScript.trim()
  const normalizedStoryboardScript = storyboards
    .map((scene: Storyboard) => String((scene as any).scene_narration || scene.narration || '').trim())
    .filter(Boolean)
    .join('\n')
    .trim()
  const needsStoryboardSync = !!normalizedCurrentScript && normalizedStoryboardScript !== normalizedCurrentScript
  const canReprocessStoryboards = !!normalizedCurrentScript && (normalizedCurrentScript !== normalizedProcessedScript || needsStoryboardSync)
  const resolvedBackgroundPreviewUrl = backgroundPreviewUrl || resolveBackgroundUrl(project?.background_image_path)
  const hasUploadedBackground = Boolean(project?.background_image_path) && parsedFlags.background_image_source === 'upload'

  const applyProjectSnapshot = (data: Project) => {
    setProject(data)
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

  const loadProject = async () => {
    const { data } = await projectApi.get(Number(id))
    setProject(data)
    setFinalScript(data.final_script || '')
    setLastProcessedScript(data.final_script || '')
    applyProjectSnapshot(data)
  }

  const setLoadingFlag = (key: string, value: boolean) => {
    setActionLoading((prev) => ({ ...prev, [key]: value }))
  }

  const isLoadingAction = (key: string) => !!actionLoading[key]

  useEffect(() => {
    const run = async () => {
      try {
        const [projectRes, voiceRes] = await Promise.all([
          projectApi.get(Number(id)),
          projectApi.getStickmanVoiceLibrary(),
        ])
        const data = projectRes.data
        setVoiceLibrary(voiceRes.data.voices || [])
        setFinalScript(data.final_script || '')
        setLastProcessedScript(data.final_script || '')
        applyProjectSnapshot(data)
      } catch {
        message.error('加载分步创作页失败')
      } finally {
        setLoading(false)
      }
    }
    run()
  }, [id])

  useEffect(() => {
    if (!project?.id) return
    if (suppressScriptAutosaveRef.current) return
    if (finalScript === (project.final_script || '')) return
    if (scriptSaveTimerRef.current) {
      window.clearTimeout(scriptSaveTimerRef.current)
    }
    scriptSaveTimerRef.current = window.setTimeout(async () => {
      try {
        const { data } = await projectApi.update(project.id, { final_script: finalScript } as Partial<Project>)
        setProject((prev) => prev ? { ...prev, final_script: data.final_script } : prev)
      } catch {
        // Ignore background autosave failures and let explicit actions retry.
      }
    }, 700)
    return () => {
      if (scriptSaveTimerRef.current) {
        window.clearTimeout(scriptSaveTimerRef.current)
        scriptSaveTimerRef.current = null
      }
    }
  }, [finalScript, project?.final_script, project?.id])

  const handleGenerateScript = async () => {
    setLoadingFlag('generateScript', true)
    try {
      const { data } = await projectApi.generateStickmanScript(Number(id))
      applyProjectSnapshot(data)
      setFinalScript(data.final_script || '')
      setLastProcessedScript(data.final_script || '')
      message.success('脚本和分镜已生成')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '生成脚本失败')
    } finally {
      setLoadingFlag('generateScript', false)
    }
  }

  const handleProcessStoryboards = async () => {
    if (!finalScript.trim()) {
      message.warning('请先准备文案内容')
      return
    }
    setLoadingFlag('processStoryboards', true)
    try {
      suppressScriptAutosaveRef.current = true
      if (scriptSaveTimerRef.current) {
        window.clearTimeout(scriptSaveTimerRef.current)
        scriptSaveTimerRef.current = null
      }
      await projectApi.useCustomScript(Number(id), finalScript, false)
      await projectApi.generateStickmanScript(Number(id))
      const refreshed = await projectApi.get(Number(id))
      const refreshedProject = refreshed.data
      const refreshedStoryboards = JSON.parse(refreshedProject.storyboard_json || '[]')
      const processedScript = refreshedStoryboards
        .map((scene: Storyboard) => String((scene as any).scene_narration || scene.narration || '').trim())
        .filter(Boolean)
        .join('\n')
      applyProjectSnapshot(refreshedProject)
      setProject((prev) => prev ? { ...prev, ...refreshedProject, final_script: processedScript } as Project : refreshedProject)
      setFinalScript(processedScript || refreshedProject.final_script || '')
      setLastProcessedScript(processedScript || refreshedProject.final_script || '')
      message.success('文案分镜处理完成')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '文案分镜处理失败')
    } finally {
      window.setTimeout(() => {
        suppressScriptAutosaveRef.current = false
      }, 0)
      setLoadingFlag('processStoryboards', false)
    }
  }

  const handleSaveStoryboards = async () => {
    setLoadingFlag('saveStoryboards', true)
    try {
      if (!storyboards.length) {
        const { data } = await projectApi.useCustomScript(Number(id), finalScript, false)
        setProject((prev) => prev ? { ...prev, final_script: data.final_script } as Project : prev)
        setFinalScript(data.final_script || '')
        setLastProcessedScript('')
        message.success('文案已保存')
        return
      }
      const { data } = await projectApi.updateStickmanStoryboards(Number(id), { storyboards, final_script: finalScript })
      applyProjectSnapshot(data)
      message.success('分镜已保存')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存分镜失败')
    } finally {
      setLoadingFlag('saveStoryboards', false)
    }
  }

  const handleGenerateEnglishSubtitles = async () => {
    setLoadingFlag('generateEnglishSubtitles', true)
    try {
      const { data } = await projectApi.generateStickmanEnglishSubtitles(Number(id))
      applyProjectSnapshot(data)
      message.success('英文字幕已生成')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '英文字幕生成失败')
    } finally {
      setLoadingFlag('generateEnglishSubtitles', false)
    }
  }

  const syncLatestScriptForOutput = async () => {
    if (!finalScript.trim() || !canReprocessStoryboards) {
      return { storyboards, imageAssets }
    }
    setLoadingFlag('syncLatestScript', true)
    try {
      suppressScriptAutosaveRef.current = true
      if (scriptSaveTimerRef.current) {
        window.clearTimeout(scriptSaveTimerRef.current)
        scriptSaveTimerRef.current = null
      }
      const nextLines = finalScript
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean)

      if (storyboards.length && nextLines.length === storyboards.length) {
        const syncedStoryboards = storyboards.map((scene, index) => {
          const text = nextLines[index] || ''
          return {
            ...scene,
            narration: text,
            scene_narration: text,
            subtitle_lines: [{ text }],
          }
        })
        const { data } = await projectApi.updateStickmanStoryboards(Number(id), {
          storyboards: syncedStoryboards,
          final_script: finalScript,
        })
        const nextImageAssets = JSON.parse(data.image_assets_json || '[]')
        const syncedScript = nextLines.join('\n')
        applyProjectSnapshot(data)
        setProject((prev) => prev ? { ...prev, ...data, final_script: syncedScript } as Project : data)
        setFinalScript(syncedScript)
        setLastProcessedScript(syncedScript)
        return { storyboards: syncedStoryboards, imageAssets: nextImageAssets }
      }

      await projectApi.useCustomScript(Number(id), finalScript, false)
      const { data } = await projectApi.generateStickmanScript(Number(id))
      const nextStoryboards = JSON.parse(data.storyboard_json || '[]')
      const nextImageAssets = JSON.parse(data.image_assets_json || '[]')
      const refreshed = await projectApi.get(Number(id))
      const refreshedProject = refreshed.data
      const refreshedStoryboards = JSON.parse(refreshedProject.storyboard_json || '[]')
      const syncedScript = refreshedStoryboards
        .map((scene: Storyboard) => String((scene as any).scene_narration || scene.narration || '').trim())
        .filter(Boolean)
        .join('\n')
      applyProjectSnapshot(refreshedProject)
      setProject((prev) => prev ? { ...prev, ...refreshedProject, final_script: syncedScript } as Project : refreshedProject)
      setFinalScript(syncedScript || refreshedProject.final_script || finalScript)
      setLastProcessedScript(syncedScript || refreshedProject.final_script || finalScript)
      return { storyboards: nextStoryboards, imageAssets: nextImageAssets }
    } finally {
      window.setTimeout(() => {
        suppressScriptAutosaveRef.current = false
      }, 0)
      setLoadingFlag('syncLatestScript', false)
    }
  }

  const handleGenerateImages = async (silent = false) => {
    if (!silent) setLoadingFlag('generateImages', true)
    try {
      await syncLatestScriptForOutput()
      const { data } = await projectApi.generateStickmanImages(Number(id))
      applyProjectSnapshot(data)
      if (!silent) message.success('整条视频画面已生成')
      return true
    } catch (error: any) {
      if (!silent) message.error(error.response?.data?.detail || '生成整条视频画面失败')
      return false
    } finally {
      if (!silent) setLoadingFlag('generateImages', false)
    }
  }

  const handleUploadBackgroundImage = async (file: File) => {
    setLoadingFlag('uploadBackgroundImage', true)
    try {
      const nextPreviewUrl = URL.createObjectURL(file)
      if (backgroundPreviewUrl) {
        URL.revokeObjectURL(backgroundPreviewUrl)
      }
      setBackgroundPreviewUrl(nextPreviewUrl)
      const { data } = await projectApi.uploadBackgroundImage(Number(id), file)
      applyProjectSnapshot(data)
      message.success('背景图已上传，旧场景图已失效，后续会按这张新背景重生成')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传背景图失败')
    } finally {
      setLoadingFlag('uploadBackgroundImage', false)
    }
    return false
  }

  const ensureDefaultVisualSettings = async () => {
    if (!project) return
    const nextFlags = { ...parsedFlags }
    let changed = false
    for (const key of ['background_template_key', 'background_template_name', 'scene_style_library_key', 'scene_style_library_name', 'scene_style_library']) {
      if (key in nextFlags) {
        delete nextFlags[key]
        changed = true
      }
    }
    if (!changed) return
    const { data } = await projectApi.update(project.id, { generation_flags: JSON.stringify(nextFlags) } as Partial<Project>)
    applyProjectSnapshot(data)
  }

  const handleComposeVideo = async () => {
    if (!hasUploadedBackground) {
      message.warning('请先上传背景图，再合成最终视频')
      return
    }
    setLoadingFlag('composeVideo', true)
    setIsComposing(true)
    setComposeProgress(1)
    setComposeMessage('正在准备最终视频...')
    setActiveComposeTaskId(null)
    try {
      await ensureDefaultVisualSettings()
      if (project?.id) {
        await projectApi.update(project.id, {
          tts_voice: project.tts_voice,
          tts_provider: project.tts_provider,
          tts_rate: project.tts_rate,
        } as Partial<Project>)
      }
      const syncedStoryboards = await syncLatestScriptForOutput()
      const effectiveStoryboards = syncedStoryboards.storyboards.length ? syncedStoryboards.storyboards : storyboards
      const effectiveImageAssets = syncedStoryboards.imageAssets.length ? syncedStoryboards.imageAssets : imageAssets
      if (!effectiveStoryboards.length) {
        throw new Error('请先处理文案分镜')
      }
      if (!effectiveImageAssets.length) {
        setComposeProgress(8)
        setComposeMessage('正在准备整条视频画面...')
        const imageReady = await handleGenerateImages(true)
        if (!imageReady) {
          throw new Error('整条视频画面生成失败，请先处理后再合成')
        }
      }
      const token = useAuthStore.getState().token || ''
      composeAbortRef.current = new AbortController()
      const response = await fetch(projectApi.generateStickmanComposeStream(Number(id)), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        signal: composeAbortRef.current.signal,
      })
      if (!response.ok) throw new Error('启动视频合成失败')
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) throw new Error('无法读取合成响应')
      let buffer = ''
      let succeeded = false
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const parsed = JSON.parse(line.slice(6))
          if (parsed.type === 'task' && parsed.task_id) {
            setActiveComposeTaskId(parsed.task_id)
          }
          if (parsed.type === 'progress') {
            setComposeProgress(parsed.progress || 0)
            setComposeMessage(parsed.content || '合成中')
          }
          if (parsed.type === 'success') {
            succeeded = true
            setComposeProgress(98)
            setComposeMessage('正在刷新最终视频...')
          }
          if (parsed.type === 'error') {
            throw new Error(parsed.content || '合成失败')
          }
        }
      }
      await loadProject()
      if (succeeded) {
        setComposeProgress(100)
        setComposeMessage('视频合成完成')
        message.success('视频已合成完成')
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        setComposeMessage('已终止当前合成')
        return
      }
      message.error(error.message || '视频合成失败')
      setComposeMessage(error.message || '视频合成失败')
    } finally {
      composeAbortRef.current = null
      setLoadingFlag('composeVideo', false)
      setIsComposing(false)
      setActiveComposeTaskId(null)
    }
  }

  const handleCancelCompose = async () => {
    if (activeComposeTaskId) {
      try {
        await projectApi.cancelTask(activeComposeTaskId)
      } catch {
        // ignore cancel race
      }
    }
    composeAbortRef.current?.abort()
    setComposeMessage('已终止当前合成')
    setIsComposing(false)
    setLoadingFlag('composeVideo', false)
    message.success('已终止当前合成')
  }

  const handlePreviewVoice = () => {
    const selectedVoice = safeVoiceOptions.find((item) => item.value === project?.tts_voice)
    if (!selectedVoice?.preview_url) {
      message.warning('当前音色还没有可用试听样本')
      return
    }
    setPreviewAudioUrl(resolveBackendUrl(selectedVoice.preview_url))
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

  const updateLocalVoiceFile = (file: File | null) => {
    setLocalVoiceFile(file)
    setPreviewAudioUrl((prev) => {
      if (prev && prev.startsWith('blob:')) URL.revokeObjectURL(prev)
      return file ? URL.createObjectURL(file) : null
    })
  }

  const handleUploadVoiceReference = async (file: File, source: 'upload' | 'record') => {
    if (!project) return false
    setLoadingFlag('uploadVoiceReference', true)
    try {
      updateLocalVoiceFile(file)
      const { data } = await projectApi.uploadVoiceReference(project.id, file, source)
      setProject(data)
      message.success(source === 'record' ? '录音已保存，后续会直接使用你的声音' : '音频已上传，后续会直接使用你的声音')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传音频失败')
    } finally {
      setLoadingFlag('uploadVoiceReference', false)
    }
    return false
  }

  useEffect(() => {
    return () => {
      if (previewAudioUrl && previewAudioUrl.startsWith('blob:')) {
        URL.revokeObjectURL(previewAudioUrl)
      }
      if (backgroundPreviewUrl) {
        URL.revokeObjectURL(backgroundPreviewUrl)
      }
      composeAbortRef.current?.abort()
    }
  }, [backgroundPreviewUrl, previewAudioUrl])

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Spin size="large" /></div>
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
            <Alert type="success" message="增强讲解工作台" description="AI 生成文案会直接带出分镜；自己输入文案时，第二步只做分段拆分，不会改写原文。" />
      <Card
        title={project?.title || '视频讲解分步创作'}
        extra={<Space><Button onClick={() => navigate(`/project/${id}/task`)}>去任务页</Button></Space>}
      >
        <div className="workflow-shell">
          <div className="workflow-main">
            <Alert type="info" message="只需要按这 5 步操作" description="1. 生成或粘贴文案  2. 处理文案分镜  3. 上传背景图  4. 配音  5. 合成最终视频。" />
            <Steps current={5} items={[{ title: '文案' }, { title: '文案分镜' }, { title: '背景图' }, { title: '配音' }, { title: '合成视频' }]} />

            <Card size="small" title="第一步：生成文案或直接使用你的文案">
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Alert type="info" message="你可以完全使用自己的文案" description="如果你已经有完整文案，直接在下方编辑框里粘贴并保存即可；如果还没有，再点“生成文案”。AI 生成文案会直接完成分镜。" />
                <Space>
                  <Button type="primary" icon={<RocketOutlined />} onClick={handleGenerateScript} loading={isLoadingAction('generateScript')}>生成文案</Button>
                  <Button onClick={handleSaveStoryboards} loading={isLoadingAction('saveStoryboards')}>保存当前文案</Button>
                </Space>
                <Input.TextArea rows={8} value={finalScript} onChange={(e) => setFinalScript(e.target.value)} placeholder="完整脚本文案。你可以完全替换成自己的文案。" />
              </Space>
            </Card>

            <Card size="small" title="第二步：处理文案分镜">
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {canReprocessStoryboards ? (
                  <>
                    <Alert type="info" message="这一步只做分段拆分" description="你输入的原文会被原样保留，只按长度和停顿拆成更适合分镜与字幕的短段，处理后会直接回写到上方文案区。" />
                    <Space wrap>
                      <Button type="primary" onClick={handleProcessStoryboards} loading={isLoadingAction('processStoryboards')} disabled={!finalScript.trim()}>处理当前文案</Button>
                      <Button onClick={handleGenerateEnglishSubtitles} loading={isLoadingAction('generateEnglishSubtitles')} disabled={!storyboards.length}>生成英文字幕（可选）</Button>
                      <Tag color={storyboards.length ? 'green' : 'default'}>{storyboards.length ? `已生成 ${storyboards.length} 幕分镜` : '尚未生成分镜'}</Tag>
                    </Space>
                  </>
                ) : (
                  <>
                    <Alert type="success" message="当前文案与分镜已一致" description="如果文案区内容没有变化，可以直接继续后面的开头图和背景步骤；只要文案和当前分镜不一致，系统会再次要求重建分镜。" />
                    <Space wrap>
                      <Tag color="green">已可直接进入下一步</Tag>
                      <Button onClick={handleGenerateEnglishSubtitles} loading={isLoadingAction('generateEnglishSubtitles')} disabled={!storyboards.length}>生成英文字幕（可选）</Button>
                    </Space>
                  </>
                )}
              </Space>
            </Card>

            <Card size="small" title="第三步：上传背景图">
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Alert type="warning" message="这一步必须上传背景图" description="当前版本先不支持在这里选择背景模板。请先上传你要使用的背景图，后续整条视频会按这张背景来生成。" />
                {resolvedBackgroundPreviewUrl ? (
                  <Space direction="vertical" style={{ width: '100%' }} size="small">
                    <div>当前项目背景</div>
                    <img src={resolvedBackgroundPreviewUrl} alt="background-reference" style={{ width: '100%', borderRadius: 12, border: '1px solid #eee', maxWidth: 560 }} />
                  </Space>
                ) : (
                  <div className="workflow-preview-box">当前还没有上传背景图。请先上传一张背景图，才能继续后面的生成。</div>
                )}
                <Upload beforeUpload={handleUploadBackgroundImage} showUploadList={false} accept=".png,.jpg,.jpeg,.webp">
                  <Button type="primary" icon={<UploadOutlined />} loading={isLoadingAction('uploadBackgroundImage')}>上传背景图</Button>
                </Upload>
                {hasUploadedBackground ? <Tag color="green">背景图已上传</Tag> : <Tag color="red">未上传背景图</Tag>}
              </Space>
            </Card>

            <Card size="small" title="第四步：配音设置">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Alert type="info" message="先确定最终配音" description="这里统一设置配音方式。你可以用 AI 配音，也可以直接上传音频或现场录音。" />
                <Select
                  value={project?.voice_source || 'ai'}
                  onChange={(value) => handleUpdateVoiceConfig({ voice_source: value as Project['voice_source'] })}
                  options={[
                    { label: 'AI 配音', value: 'ai' },
                    { label: '直接录音', value: 'record' },
                    { label: '上传音频文件', value: 'upload' },
                  ]}
                  style={{ width: '100%' }}
                />
                {(project?.voice_source || 'ai') === 'ai' ? (
                  <>
                    <Select
                      value={project?.tts_voice}
                      onChange={(value) => {
                        const selectedVoice = safeVoiceOptions.find((item) => item.value === value)
                        handleUpdateVoiceConfig({ tts_voice: value, tts_provider: selectedVoice?.provider || 'dashscope_cosyvoice' })
                      }}
                      options={safeVoiceOptions}
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
                  </>
                ) : null}
                {project?.voice_source === 'record' ? (
                  <div style={{ marginTop: 8 }}>
                    <AudioRecorder value={localVoiceFile} onChange={(file) => {
                      if (file) void handleUploadVoiceReference(file, 'record')
                      else updateLocalVoiceFile(null)
                    }} />
                  </div>
                ) : null}
                {project?.voice_source === 'upload' ? (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Upload beforeUpload={(file) => handleUploadVoiceReference(file, 'upload')} showUploadList={false} accept=".mp3,.wav,.m4a,.aac,.ogg,.webm">
                      <Button icon={<UploadOutlined />} loading={isLoadingAction('uploadVoiceReference')}>上传音频文件</Button>
                    </Upload>
                    {localVoiceFile ? <div>{localVoiceFile.name}</div> : null}
                    {previewAudioUrl ? <audio controls src={previewAudioUrl} /> : null}
                  </Space>
                ) : null}
              </Space>
            </Card>

            <Card size="small" title="第五步：合成最终视频">
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Alert type="success" message="最后一步会直接输出成片" description="如果前面还没有准备整条视频画面，系统会先自动完成画面准备，再继续合成最终视频。" />
                <Space wrap>
                  <Button type="primary" onClick={handleComposeVideo} loading={isLoadingAction('composeVideo')} disabled={!storyboards.length}>合成最终视频</Button>
                  {isComposing && <Button danger onClick={handleCancelCompose}>终止当前合成</Button>}
                </Space>
                {!!composeProgress && <Progress percent={composeProgress} status={isComposing ? 'active' : composeProgress >= 100 ? 'success' : 'normal'} format={(percent) => `${percent || 0}%`} />}
                {!!composeMessage && <div>{composeMessage}</div>}
                {project?.video_url && <video src={resolveBackendUrl(project.video_url)} controls className="workflow-video-preview" />}
              </Space>
            </Card>
          </div>

        </div>
      </Card>
    </div>
  )
}
