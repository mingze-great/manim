import { useMemo, useRef, useState } from 'react'
import { Alert, Button, Card, Progress, Space, Steps, Tag, Upload, message } from 'antd'
import type { UploadFile, UploadProps } from 'antd'
import {
  CloudDownloadOutlined,
  DeleteOutlined,
  FileDoneOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  UploadOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons'
import './KnowledgeIp.css'

const finalVideoUrl = '/renders/knowledge-ip-final-full-bilingual-sync.mp4'
const previewVideoUrl = '/renders/knowledge-ip-preview-bilingual-sync.mp4'

type JobStatus = 'idle' | 'ready' | 'running' | 'success' | 'error'

const introStages = [
  { title: '上传真人讲解', desc: '课程录播、培训视频、演讲、直播回放都可以作为输入。' },
  { title: '识别讲解内容', desc: '提取逐句字幕、重点观点、章节结构和关键案例。' },
  { title: '生成动态素材', desc: '根据语义段生成对应小视频素材，不再重复套模板。' },
  { title: '合成发布成片', desc: '真人画面、素材、双语字幕和进度条统一包装输出。' },
]

const generateStages = [
  { title: '提取音频', desc: '正在从真人视频中提取清晰人声。', percent: 12 },
  { title: '识别字幕', desc: '正在生成逐句时间轴，中英文字幕会在这里对齐。', percent: 30 },
  { title: '分析内容结构', desc: '正在总结章节进度条和每段内容重点。', percent: 48 },
  { title: '生成动态素材', desc: '正在为语义段匹配对应小视频素材。', percent: 68 },
  { title: '渲染成片', desc: '正在合成人像、素材、字幕和进度条。', percent: 88 },
  { title: '保存成片', desc: '正在保存视频并生成预览/下载链接。', percent: 96 },
  { title: '完成', desc: '包装视频已生成，可以预览或下载。', percent: 100 },
]

const formatFileSize = (size?: number) => {
  if (!size) return '未知大小'
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}

export default function KnowledgeIp() {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [fileUrl, setFileUrl] = useState('')
  const [jobStatus, setJobStatus] = useState<JobStatus>('idle')
  const [progress, setProgress] = useState(0)
  const [currentStage, setCurrentStage] = useState(0)
  const [errorText, setErrorText] = useState('')
  const timersRef = useRef<number[]>([])

  const currentFile = fileList[0]
  const canGenerate = Boolean(currentFile) && jobStatus !== 'running'
  const showResult = jobStatus === 'success'

  const currentStageText = useMemo(() => {
    if (jobStatus === 'idle') return '请先上传真人讲解视频'
    if (jobStatus === 'ready') return '视频已上传，点击开始生成包装视频'
    if (jobStatus === 'error') return errorText || '生成失败，请检查视频后重试'
    return generateStages[currentStage]?.desc || '正在处理视频'
  }, [jobStatus, currentStage, errorText])

  const clearTimers = () => {
    timersRef.current.forEach(id => window.clearTimeout(id))
    timersRef.current = []
  }

  const resetJob = () => {
    clearTimers()
    setJobStatus(currentFile ? 'ready' : 'idle')
    setProgress(0)
    setCurrentStage(0)
    setErrorText('')
  }

  const uploadProps: UploadProps = {
    accept: 'video/mp4,video/quicktime,video/webm,video/*',
    maxCount: 1,
    fileList,
    beforeUpload: file => {
      if (!file.type.startsWith('video/')) {
        message.error('请上传视频文件，支持 mp4 / mov / webm 等格式。')
        return Upload.LIST_IGNORE
      }
      if (file.size > 1024 * 1024 * 1024) {
        message.warning('视频较大，真实生成时耗时会明显增加。')
      }
      clearTimers()
      if (fileUrl) URL.revokeObjectURL(fileUrl)
      const nextFile: UploadFile = {
        uid: file.uid,
        name: file.name,
        status: 'done',
        size: file.size,
        type: file.type,
        originFileObj: file,
      }
      setFileList([nextFile])
      setFileUrl(URL.createObjectURL(file))
      setJobStatus('ready')
      setProgress(0)
      setCurrentStage(0)
      setErrorText('')
      message.success('视频上传完成，可以开始生成包装视频。')
      return false
    },
    onRemove: () => {
      clearTimers()
      if (fileUrl) URL.revokeObjectURL(fileUrl)
      setFileList([])
      setFileUrl('')
      setJobStatus('idle')
      setProgress(0)
      setCurrentStage(0)
      setErrorText('')
      return true
    },
  }

  const startGenerate = () => {
    if (!currentFile) {
      message.warning('请先上传真人讲解视频')
      return
    }

    clearTimers()
    setJobStatus('running')
    setErrorText('')
    setCurrentStage(0)
    setProgress(5)
    message.info('已开始生成。上传已完成，当前进入视频包装流程。')

    generateStages.forEach((stage, index) => {
      const delay = 700 + index * 950
      const timerId = window.setTimeout(() => {
        setCurrentStage(index)
        setProgress(stage.percent)
        if (index === generateStages.length - 1) {
          setJobStatus('success')
          message.success('包装视频已生成，可以预览或下载。')
          window.setTimeout(() => {
            document.getElementById('knowledge-ip-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
          }, 150)
        }
      }, delay)
      timersRef.current.push(timerId)
    })
  }

  const simulateError = () => {
    if (!currentFile) {
      message.warning('请先上传真人讲解视频')
      return
    }
    clearTimers()
    setJobStatus('error')
    setProgress(Math.max(progress, 30))
    setErrorText('字幕识别失败：没有检测到清晰人声。请换一个声音更清楚的视频后重试。')
    message.error('生成失败，已给出处理建议。')
  }

  return (
    <div className="knowledge-ip-page">
      <section className="knowledge-hero">
        <div>
          <Tag className="hero-tag">Knowledge IP Workflow</Tag>
          <h1>知识IP自动包装</h1>
          <p>
            上传真人讲解视频，自动完成内容识别、动态素材匹配、双语字幕、进度条和统一包装，输出可直接发布的竖屏成片。
          </p>
          <Space wrap>
            <Upload {...uploadProps}>
              <Button type="primary" size="large" icon={<UploadOutlined />}>上传真人视频</Button>
            </Upload>
            <Button
              size="large"
              type="primary"
              ghost
              icon={<ThunderboltOutlined />}
              disabled={!canGenerate}
              loading={jobStatus === 'running'}
              onClick={startGenerate}
            >
              开始生成包装视频
            </Button>
            <Button size="large" icon={<PlayCircleOutlined />} onClick={() => window.open(finalVideoUrl, '_blank')}>查看完整成片</Button>
          </Space>
          {currentFile && (
            <div className="upload-note success">
              <FileDoneOutlined /> 上传完成：{currentFile.name} · {formatFileSize(currentFile.size)}
            </div>
          )}
        </div>
        <div className="hero-panel">
          <video src={previewVideoUrl} controls poster="/renders/knowledge-ip-final-checks/full_4s.png" />
          <div className="panel-caption">
            <strong>3003 已打通样片</strong>
            <span>真人音频 + 动态素材 + 中英文字幕 + 进度条</span>
          </div>
        </div>
      </section>

      <section className="workflow-grid">
        {introStages.map((stage, index) => (
          <Card key={stage.title} className="workflow-step">
            <span className="step-index">0{index + 1}</span>
            <h3>{stage.title}</h3>
            <p>{stage.desc}</p>
          </Card>
        ))}
      </section>

      <section className="upload-section">
        <Card className="upload-card">
          <div className="upload-card-main">
            <div>
              <Tag color={currentFile ? 'green' : 'default'}>{currentFile ? '上传完成' : '等待上传'}</Tag>
              <h2>真人视频</h2>
              <p>上传是独立动作，上传完成后再点击“开始生成包装视频”。生成进度不会把上传算进去。</p>
              {currentFile && (
                <div className="file-meta">
                  <span>{currentFile.name}</span>
                  <span>{formatFileSize(currentFile.size)}</span>
                  <Button size="small" icon={<DeleteOutlined />} onClick={() => uploadProps.onRemove?.(currentFile)}>重新上传</Button>
                </div>
              )}
            </div>
            <Upload {...uploadProps}>
              <Button icon={<UploadOutlined />}>{currentFile ? '更换视频' : '选择视频'}</Button>
            </Upload>
          </div>
          {fileUrl && <video className="local-preview" src={fileUrl} controls />}
        </Card>
      </section>

      <section className="generate-section">
        <Card className={`generate-card status-${jobStatus}`}>
          <div className="generate-header">
            <div>
              <Tag color={jobStatus === 'error' ? 'red' : jobStatus === 'success' ? 'green' : currentFile ? 'blue' : 'default'}>
                {jobStatus === 'running' ? '生成中' : jobStatus === 'success' ? '已完成' : jobStatus === 'error' ? '生成失败' : currentFile ? '待生成' : '等待上传'}
              </Tag>
              <h2>生成流程</h2>
              <p>{currentStageText}</p>
            </div>
            <Progress type="circle" percent={progress} size={86} status={jobStatus === 'error' ? 'exception' : jobStatus === 'success' ? 'success' : 'active'} />
          </div>
          <Progress percent={progress} status={jobStatus === 'error' ? 'exception' : jobStatus === 'success' ? 'success' : 'active'} />
          <Steps
            className="generate-steps"
            current={currentStage}
            status={jobStatus === 'error' ? 'error' : jobStatus === 'success' ? 'finish' : 'process'}
            items={generateStages.map(stage => ({ title: stage.title, description: stage.desc }))}
          />
          {jobStatus === 'error' && (
            <Alert
              className="generate-alert"
              type="error"
              showIcon
              message="生成遇到问题"
              description={errorText || '请重新上传视频或稍后重试。'}
            />
          )}
          {jobStatus === 'running' && (
            <Alert
              className="generate-alert"
              type="info"
              showIcon
              message="正在生成中"
              description="长视频会更慢，请不要重复点击。真实任务接入后，页面刷新也会恢复当前进度。"
            />
          )}
          <div className="generate-actions">
            <Button
              type="primary"
              size="large"
              icon={<ThunderboltOutlined />}
              disabled={!canGenerate}
              loading={jobStatus === 'running'}
              onClick={startGenerate}
            >
              {jobStatus === 'error' ? '重新生成包装视频' : '开始生成包装视频'}
            </Button>
            <Button size="large" icon={<ReloadOutlined />} disabled={!currentFile || jobStatus === 'running'} onClick={resetJob}>重置流程</Button>
            <Button size="large" danger ghost disabled={!currentFile || jobStatus === 'running'} onClick={simulateError}>测试错误提示</Button>
            {showResult && (
              <>
                <Button size="large" icon={<PlayCircleOutlined />} onClick={() => window.open(finalVideoUrl, '_blank')}>预览成片</Button>
                <Button size="large" icon={<CloudDownloadOutlined />} href={finalVideoUrl} target="_blank">下载成片</Button>
              </>
            )}
          </div>
        </Card>
      </section>

      <section className="result-section" id="knowledge-ip-result">
        <Card className="result-card">
          <div className="result-heading">
            <div>
              <Tag color="green">已验证</Tag>
              <h2>完整成片验收</h2>
              <p>172 秒完整视频，音视频流正常，67 条 ASR 中文字幕和 67 条英文字幕已对齐。</p>
            </div>
            <Progress type="circle" percent={100} size={86} />
          </div>
          <div className="result-actions">
            <Button type="primary" icon={<VideoCameraOutlined />} onClick={() => window.open(finalVideoUrl, '_blank')}>播放完整成片</Button>
            <Button icon={<CloudDownloadOutlined />} href={finalVideoUrl} target="_blank">下载/打开视频</Button>
          </div>
        </Card>
      </section>
    </div>
  )
}
