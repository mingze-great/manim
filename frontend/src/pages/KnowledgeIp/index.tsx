import { useState } from 'react'
import { Button, Card, Progress, Space, Tag, Upload, message } from 'antd'
import type { UploadProps } from 'antd'
import {
  CloudDownloadOutlined,
  PlayCircleOutlined,
  UploadOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons'
import './KnowledgeIp.css'

const finalVideoUrl = '/renders/knowledge-ip-final-full-bilingual-sync.mp4'
const previewVideoUrl = '/renders/knowledge-ip-preview-bilingual-sync.mp4'

const stages = [
  { title: '上传真人讲解', desc: '课程录播、培训视频、演讲、直播回放都可以作为输入。' },
  { title: '识别讲解内容', desc: '提取逐句字幕、重点观点、章节结构和关键案例。' },
  { title: '生成动态素材', desc: '根据语义段生成对应小视频素材，不再重复套模板。' },
  { title: '合成发布成片', desc: '真人画面、素材、双语字幕和进度条统一包装输出。' },
]

export default function KnowledgeIp() {
  const [fileName, setFileName] = useState('')

  const uploadProps: UploadProps = {
    accept: 'video/*',
    maxCount: 1,
    beforeUpload: file => {
      setFileName(file.name)
      message.info('上传入口已就位，下一步会接入自动任务队列。当前页面先用于验收 3003 已打通的完整成片链路。')
      return false
    },
    onRemove: () => setFileName(''),
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
              <Button type="primary" size="large" icon={<UploadOutlined />}>上传讲解视频</Button>
            </Upload>
            <Button size="large" icon={<PlayCircleOutlined />} onClick={() => window.open(finalVideoUrl, '_blank')}>查看完整成片</Button>
          </Space>
          {fileName && <div className="upload-note">已选择：{fileName}</div>}
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
        {stages.map((stage, index) => (
          <Card key={stage.title} className="workflow-step">
            <span className="step-index">0{index + 1}</span>
            <h3>{stage.title}</h3>
            <p>{stage.desc}</p>
          </Card>
        ))}
      </section>

      <section className="result-section">
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
