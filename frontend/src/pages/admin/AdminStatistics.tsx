import { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Select, Spin, Empty } from 'antd'
import { UserOutlined, VideoCameraOutlined, MessageOutlined, ProjectOutlined } from '@ant-design/icons'
import { adminApi } from '@/services/admin'

interface OverviewData {
  conversations_count: number
  api_calls_count: number
  videos_count: number
  projects_count: number
  active_users: number
}

interface TrendItem {
  date: string
  conversations_count: number
  api_calls_count: number
  videos_count: number
  projects_count: number
}

export default function AdminStatistics() {
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState('day')
  const [overview, setOverview] = useState<OverviewData | null>(null)
  const [trend, setTrend] = useState<TrendItem[]>([])

  useEffect(() => {
    fetchData()
  }, [period])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [overviewRes, trendRes] = await Promise.all([
        adminApi.getStatisticsOverview(period),
        adminApi.getStatisticsTrend(period)
      ])
      setOverview(overviewRes.data)
      setTrend(trendRes.data)
    } catch (error) {
      console.error('获取统计数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const getMaxValue = (key: keyof TrendItem) => {
    if (!trend.length) return 100
    return Math.max(...trend.map(t => t[key] as number), 1)
  }

  const renderTrendBar = (value: number, max: number, color: string) => {
    const percent = max > 0 ? (value / max) * 100 : 0
    return (
      <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2 mt-1">
        <div 
          className="h-2 rounded-full transition-all duration-300" 
          style={{ width: `${percent}%`, backgroundColor: color }}
        />
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">数据统计</h2>
          <p className="text-gray-500 mt-1">查看平台运营数据</p>
        </div>
        <Select
          value={period}
          onChange={setPeriod}
          style={{ width: 120 }}
          options={[
            { label: '今日', value: 'day' },
            { label: '本周', value: 'week' },
            { label: '本月', value: 'month' }
          ]}
        />
      </div>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活跃用户"
              value={overview?.active_users || 0}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#3b82f6' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="对话次数"
              value={overview?.conversations_count || 0}
              prefix={<MessageOutlined />}
              valueStyle={{ color: '#10b981' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="生成视频"
              value={overview?.videos_count || 0}
              prefix={<VideoCameraOutlined />}
              valueStyle={{ color: '#8b5cf6' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="创建项目"
              value={overview?.projects_count || 0}
              prefix={<ProjectOutlined />}
              valueStyle={{ color: '#f59e0b' }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="趋势数据">
        {trend.length === 0 ? (
          <Empty description="暂无数据" />
        ) : (
          <div className="space-y-4">
            <div className="text-sm text-gray-500 mb-4">对话趋势</div>
            {trend.slice(-7).map((item, index) => (
              <div key={index} className="flex items-center gap-4">
                <div className="w-20 text-xs text-gray-400">{item.date.slice(5)}</div>
                <div className="flex-1">
                  {renderTrendBar(item.conversations_count, getMaxValue('conversations_count'), '#10b981')}
                </div>
                <div className="w-16 text-right text-sm">{item.conversations_count}</div>
              </div>
            ))}

            <div className="text-sm text-gray-500 mb-4 mt-6">视频生成趋势</div>
            {trend.slice(-7).map((item, index) => (
              <div key={index} className="flex items-center gap-4">
                <div className="w-20 text-xs text-gray-400">{item.date.slice(5)}</div>
                <div className="flex-1">
                  {renderTrendBar(item.videos_count, getMaxValue('videos_count'), '#8b5cf6')}
                </div>
                <div className="w-16 text-right text-sm">{item.videos_count}</div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}