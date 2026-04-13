import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card, Input, Button, Select, Space, Typography, message,
  Row, Col, Image, Divider, Alert, Spin, Empty, Radio
} from 'antd'
import {
  DownloadOutlined, ReloadOutlined, PictureOutlined,
  HistoryOutlined, SettingOutlined
} from '@ant-design/icons'
import { coverApi, CoverStyle, Cover as CoverItem } from '@/services/cover'
import './Cover.css'

const { Title, Text } = Typography
const { TextArea } = Input

export default function CoverPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [styles, setStyles] = useState<CoverStyle[]>([])
  const [selectedStyleId, setSelectedStyleId] = useState<number | null>(null)
  const [titleLine1, setTitleLine1] = useState('')
  const [titleLine2, setTitleLine2] = useState('')
  const [topic, setTopic] = useState('')
  const [fontStyle, setFontStyle] = useState('黑体')
  const [fontColor, setFontColor] = useState('#333333')
  const [currentCover, setCurrentCover] = useState<CoverItem | null>(null)
  const [history, setHistory] = useState<CoverItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)

  useEffect(() => {
    loadStyles()
    loadHistory()
  }, [])

  const loadStyles = async () => {
    try {
      const { data } = await coverApi.getStyles()
      setStyles(data)
      if (data.length > 0) {
        setSelectedStyleId(data[0].id)
      }
    } catch (err) {
      message.error('加载风格列表失败')
    }
  }

  const loadHistory = async () => {
    setHistoryLoading(true)
    try {
      const { data } = await coverApi.getHistory()
      setHistory(data)
    } catch (err) {
      console.error('加载历史失败:', err)
    } finally {
      setHistoryLoading(false)
    }
  }

  const handleGenerate = async () => {
    if (!titleLine1.trim()) {
      message.warning('请输入第一行标题')
      return
    }
    if (!topic.trim()) {
      message.warning('请输入封面主题')
      return
    }

    setLoading(true)
    try {
      const { data } = await coverApi.create({
        style_id: selectedStyleId,
        title_line1: titleLine1,
        title_line2: titleLine2 || undefined,
        topic,
        font_style: fontStyle,
        font_color: fontColor,
      })
      setCurrentCover(data)
      message.success('封面生成成功')
      loadHistory()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRegenerate = async () => {
    if (!currentCover) return
    setLoading(true)
    try {
      const { data } = await coverApi.regenerate(currentCover.id)
      setCurrentCover(data)
      message.success('重新生成成功')
      loadHistory()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '重新生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = () => {
    if (!currentCover?.local_url) return
    const link = window.document.createElement('a')
    link.href = `/api${currentCover.local_url}`
    link.download = `cover_${currentCover.id}.png`
    link.click()
  }

  const handleSelectHistory = (cover: CoverItem) => {
    setCurrentCover(cover)
    setTitleLine1(cover.title_line1)
    setTitleLine2(cover.title_line2 || '')
    setTopic(cover.topic)
    setFontStyle(cover.font_style || '黑体')
    setFontColor(cover.font_color || '#333333')
    setSelectedStyleId(cover.style_id)
  }

  const selectedStyle = styles.find(s => s.id === selectedStyleId)

  return (
    <div className="cover-page">
      <Title level={2} style={{ marginBottom: 24 }}>
        <PictureOutlined /> 封面设计
      </Title>

      <Row gutter={24}>
        <Col span={16}>
          <Card title="封面设置" style={{ marginBottom: 24 }}>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Alert type="info" message="封面尺寸为 9:16 竖版，适合公众号封面或短视频封面。" showIcon />

              <Divider>风格选择</Divider>
              <Select
                value={selectedStyleId}
                onChange={setSelectedStyleId}
                style={{ width: '100%' }}
                placeholder="选择封面风格"
              >
                {styles.map(style => (
                  <Select.Option key={style.id} value={style.id}>
                    {style.name} - {style.description}
                  </Select.Option>
                ))}
              </Select>

              {selectedStyle && (
                <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 8 }}>
                  <Text type="secondary">推荐字体：{selectedStyle.font_recommendation || '黑体'}</Text>
                  <br />
                  <Text type="secondary">推荐颜色：{selectedStyle.color_recommendation || '#333333'}</Text>
                </div>
              )}

              <Divider>标题设置</Divider>
              <Input
                value={topic}
                onChange={e => setTopic(e.target.value)}
                placeholder="封面主题（如：如何提升工作效率）"
              />
              <Input
                value={titleLine1}
                onChange={e => setTitleLine1(e.target.value)}
                placeholder="第一行标题（主标题，字体较大）"
              />
              <Input
                value={titleLine2}
                onChange={e => setTitleLine2(e.target.value)}
                placeholder="第二行标题（副标题，可选）"
              />

              <Divider>字体配置</Divider>
              <Row gutter={16}>
                <Col span={12}>
                  <Text type="secondary">字体样式</Text>
                  <Select value={fontStyle} onChange={setFontStyle} style={{ width: '100%' }}>
                    <Select.Option value="黑体">黑体</Select.Option>
                    <Select.Option value="宋体">宋体</Select.Option>
                    <Select.Option value="微软雅黑">微软雅黑</Select.Option>
                    <Select.Option value="楷体">楷体</Select.Option>
                  </Select>
                </Col>
                <Col span={12}>
                  <Text type="secondary">字体颜色</Text>
                  <Select value={fontColor} onChange={setFontColor} style={{ width: '100%' }}>
                    <Select.Option value="#333333">黑色</Select.Option>
                    <Select.Option value="#FFFFFF">白色</Select.Option>
                    <Select.Option value="#1E90FF">蓝色</Select.Option>
                    <Select.Option value="#FF6B6B">红色</Select.Option>
                    <Select.Option value="#2C3E50">深灰</Select.Option>
                  </Select>
                </Col>
              </Row>

              <Button
                type="primary"
                size="large"
                icon={<PictureOutlined />}
                onClick={handleGenerate}
                loading={loading}
                block
              >
                生成封面
              </Button>
            </Space>
          </Card>

          <Card title="封面预览">
            {loading ? (
              <div style={{ textAlign: 'center', padding: 60 }}>
                <Spin size="large" />
                <Text type="secondary" style={{ marginTop: 16, display: 'block' }}>
                  正在生成封面...
                </Text>
              </div>
            ) : currentCover ? (
              <div className="cover-preview">
                <Image
                  src={currentCover.local_url ? `/api${currentCover.local_url}` : currentCover.image_url}
                  alt="封面预览"
                  style={{ maxWidth: '100%', borderRadius: 12 }}
                />
                <Space style={{ marginTop: 16 }}>
                  <Button icon={<ReloadOutlined />} onClick={handleRegenerate} loading={loading}>
                    重新生成
                  </Button>
                  <Button icon={<DownloadOutlined />} onClick={handleDownload}>
                    下载封面
                  </Button>
                </Space>
              </div>
            ) : (
              <Empty description="请先生成封面" />
            )}
          </Card>
        </Col>

        <Col span={8}>
          <Card title={<><HistoryOutlined /> 历史封面</>} extra={<Button size="small" onClick={loadHistory}>刷新</Button>}>
            {historyLoading ? (
              <Spin />
            ) : history.length > 0 ? (
              <div className="history-list">
                {history.map(cover => (
                  <Card
                    key={cover.id}
                    size="small"
                    hoverable
                    onClick={() => handleSelectHistory(cover)}
                    style={{ marginBottom: 12 }}
                  >
                    <Image
                      src={cover.local_url ? `/api${cover.local_url}` : cover.image_url}
                      alt={`封面 ${cover.id}`}
                      width="100%"
                      style={{ borderRadius: 8 }}
                    />
                    <Text ellipsis style={{ marginTop: 8 }}>{cover.title_line1}</Text>
                  </Card>
                ))}
              </div>
            ) : (
              <Empty description="暂无历史封面" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}