import { useState } from 'react'
import { Alert, Button, Card, Input, InputNumber, Select, message } from 'antd'
import { ArrowLeftOutlined, NotificationOutlined, RocketOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { projectApi } from '@/services/project'
import './Creator/Creator.css'

const { TextArea } = Input

export default function ExplainerCreator() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const [loading, setLoading] = useState(false)
  const [sourceText, setSourceText] = useState('')
  const [storyboardCount, setStoryboardCount] = useState(10)
  const [targetDuration, setTargetDuration] = useState(45)
  const [openingHookMode, setOpeningHookMode] = useState('hook_question')
  const [visualStyleKey, setVisualStyleKey] = useState('deep_blue_emotional')
  const [ttsVoice, setTtsVoice] = useState('longxiaochun_v2')
  const [ttsRate, setTtsRate] = useState('+0%')
  const [generationMode, setGenerationMode] = useState<'one_click' | 'step_by_step'>('step_by_step')

  const permissions = user?.module_permissions || {}
  const explainerEnabled = user?.is_admin || permissions.explainer?.enabled !== false

  const handleCreate = async () => {
    if (!explainerEnabled) {
      message.warning('当前账号未开通讲解型视频模块，请联系管理员开通')
      return
    }
    if (!sourceText.trim()) {
      message.warning('请输入主题或原始文案')
      return
    }
    setLoading(true)
    try {
      const baseTitle = sourceText.trim().split(/\r?\n/)[0].slice(0, 24) || '讲解型视频'
      const { data } = await projectApi.create({
        title: `讲解型视频-${baseTitle}`,
        theme: sourceText.trim(),
        module_type: 'explainer',
        storyboard_count: storyboardCount,
        aspect_ratio: '16:9',
        generation_mode: generationMode,
        voice_source: 'ai',
        tts_provider: 'dashscope_cosyvoice',
        tts_voice: ttsVoice,
        tts_rate: ttsRate,
      })
      await projectApi.update(data.id, {
        generation_flags: JSON.stringify({
          opening_hook_mode: openingHookMode,
          visual_style_key: visualStyleKey,
          target_duration: targetDuration,
          scene_count: storyboardCount,
          subtitle_mode: 'short_punch',
        }),
      } as any)
      message.success('讲解型视频项目已创建')
      navigate(generationMode === 'step_by_step' ? `/project/${data.id}/explainer` : `/project/${data.id}/task`)
    } catch (error: any) {
      message.error(error.response?.data?.detail || error.message || '创建失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="creator-page">
      <div className="creator-hero creator-hero-sunrise">
        <div className="hero-content">
          <h1 className="hero-title">
            <NotificationOutlined className="mr-3" />
            讲解型视频创作台
          </h1>
          <p className="hero-subtitle">围绕抖音爆款逻辑生成分镜、字幕、配音和轻运动讲解视频</p>
        </div>
      </div>

      <div className="creator-container">
        <div className="max-w-6xl mx-auto w-full space-y-6">
          <div className="flex gap-3 flex-wrap">
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/creator')}>返回创作首页</Button>
          </div>

          <Alert
            type="success"
            message="目标：抖音爆款讲解视频"
            description="系统会优先生成强钩子开头、短句字幕、快节奏分镜和更强的观点表达。"
          />

          <Card>
            <div className="stickman-form-grid">
              <div>
                <label className="stickman-label">主题或原始文案</label>
                <TextArea
                  value={sourceText}
                  onChange={(e) => setSourceText(e.target.value)}
                  rows={12}
                  placeholder={`输入一个主题，或直接粘贴一段原始文案，例如：
• 为什么越懂事的人，越容易委屈自己
• 你以为自己在休息，其实是在慢性消耗
• 如果一个人突然不联系你了，真相可能只有这3种`}
                />
              </div>

              <div className="stickman-side-card space-y-4">
                <div>
                  <label className="stickman-label">开头钩子</label>
                  <Select value={openingHookMode} onChange={setOpeningHookMode} style={{ width: '100%' }} options={[
                    { label: '反问钩子', value: 'hook_question' },
                    { label: '数字爆点', value: 'big_number' },
                  ]} />
                </div>

                <div>
                  <label className="stickman-label">视觉方向</label>
                  <Select value={visualStyleKey} onChange={setVisualStyleKey} style={{ width: '100%' }} options={[
                    { label: '深蓝情绪线稿', value: 'deep_blue_emotional' },
                    { label: '观点冷峻线稿', value: 'opinion_editorial' },
                    { label: '治愈成长线稿', value: 'growth_soft_glow' },
                  ]} />
                </div>

                <div>
                  <label className="stickman-label">分镜数量</label>
                  <InputNumber min={8} max={15} value={storyboardCount} onChange={(value) => setStoryboardCount(Number(value) || 10)} style={{ width: '100%' }} />
                </div>

                <div>
                  <label className="stickman-label">目标时长（秒）</label>
                  <InputNumber min={25} max={120} step={5} value={targetDuration} onChange={(value) => setTargetDuration(Number(value) || 45)} style={{ width: '100%' }} />
                </div>

                <div>
                  <label className="stickman-label">AI 音色</label>
                  <Select value={ttsVoice} onChange={setTtsVoice} style={{ width: '100%' }} options={[
                    { label: '知性女声', value: 'longxiaochun_v2' },
                    { label: '元气女声', value: 'longanhuan' },
                    { label: '稳重男声', value: 'longshuo_v3' },
                    { label: '阳光男声', value: 'longanyang' },
                  ]} />
                </div>

                <div>
                  <label className="stickman-label">语速</label>
                  <Select value={ttsRate} onChange={setTtsRate} style={{ width: '100%' }} options={[
                    { label: '偏慢', value: '-10%' },
                    { label: '标准', value: '+0%' },
                    { label: '偏快', value: '+15%' },
                  ]} />
                </div>

                <div>
                  <label className="stickman-label">工作流</label>
                  <Select value={generationMode} onChange={(value) => setGenerationMode(value)} style={{ width: '100%' }} options={[
                    { label: '分步创作', value: 'step_by_step' },
                    { label: '一键生成', value: 'one_click' },
                  ]} />
                </div>

                <div className="stickman-tips">
                  <p>前 3 秒会优先生成冲突、反问、数字或反常识钩子。</p>
                  <p>字幕优先走短句策略，减少“说明书腔”。</p>
                  <p>建议先用分步创作确认开头和分镜，再一键合成最终视频。</p>
                </div>

                <Button type="primary" icon={<RocketOutlined />} onClick={handleCreate} loading={loading} size="large" block className="btn-gradient">
                  开始制作讲解型视频
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
