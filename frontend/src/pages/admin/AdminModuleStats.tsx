import { useEffect, useState } from 'react'
import { Card, Col, Progress, Row, Spin, Statistic, Tag } from 'antd'
import { FileTextOutlined, HighlightOutlined, VideoCameraOutlined } from '@ant-design/icons'
import { adminApi, ModuleStatsResponse } from '@/services/admin'

export default function AdminModuleStats() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<ModuleStatsResponse | null>(null)

  useEffect(() => {
    const run = async () => {
      setLoading(true)
      try {
        const { data } = await adminApi.getModuleStats()
        setStats(data)
      } finally {
        setLoading(false)
      }
    }
    run()
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Spin size="large" /></div>
  }

  const items = [
    { key: 'visual', title: '思维可视化', icon: <HighlightOutlined />, color: '#2563eb', data: stats?.visual },
    { key: 'stickman', title: '火柴人视频', icon: <VideoCameraOutlined />, color: '#f59e0b', data: stats?.stickman },
    { key: 'article', title: '公众号文章', icon: <FileTextOutlined />, color: '#7c3aed', data: stats?.article },
  ]

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold">模块统计看板</h2>
        <p className="text-gray-500 mt-1">查看思维可视化、火柴人视频和公众号文章三个模块的运营情况</p>
      </div>
      <Row gutter={[16, 16]}>
        {items.map((item) => (
          <Col xs={24} lg={8} key={item.key}>
            <Card>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-lg font-semibold">
                  <span style={{ color: item.color }}>{item.icon}</span>
                  <span>{item.title}</span>
                </div>
                <Tag color="blue">成功率 {item.data?.success_rate || 0}%</Tag>
              </div>
              <Row gutter={[12, 12]}>
                <Col span={12}><Statistic title="累计作品" value={item.data?.total || 0} /></Col>
                <Col span={12}><Statistic title="今日新增" value={item.data?.today || 0} /></Col>
                <Col span={12}><Statistic title="成功数" value={item.data?.success || 0} valueStyle={{ color: '#16a34a' }} /></Col>
                <Col span={12}><Statistic title="失败数" value={item.data?.failed || 0} valueStyle={{ color: '#dc2626' }} /></Col>
              </Row>
              <div className="mt-4">
                <div className="text-sm text-gray-500 mb-2">模块成功率</div>
                <Progress percent={item.data?.success_rate || 0} strokeColor={item.color} />
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  )
}
