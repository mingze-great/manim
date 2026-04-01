import { useState, useEffect } from 'react'
import { Card, Row, Col, Radio, Spin, Empty, Progress, Tag } from 'antd'
import {
  UserOutlined, VideoCameraOutlined, MessageOutlined, ProjectOutlined,
  RiseOutlined, ThunderboltOutlined, LineChartOutlined, BarChartOutlined
} from '@ant-design/icons'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
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

const formatNumber = (num: number) => {
  if (num >= 1000000) return (num / 1000000).toFixed(2) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toLocaleString('zh-CN')
}

export default function AdminStatistics() {
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState<'day' | 'week' | 'month'>('day')
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

  const getChartData = () => {
    return trend.slice(-7).map(item => ({
      ...item,
      date: item.date.slice(5),
      fullDate: item.date
    }))
  }

  const chartData = getChartData()

  const statCards = [
    {
      icon: <UserOutlined />,
      title: '活跃用户',
      value: overview?.active_users || 0,
      color: '#6366f1',
      bg: 'from-indigo-500 to-purple-500',
      light: 'bg-indigo-50'
    },
    {
      icon: <MessageOutlined />,
      title: '对话次数',
      value: overview?.conversations_count || 0,
      color: '#10b981',
      bg: 'from-emerald-500 to-teal-500',
      light: 'bg-emerald-50'
    },
    {
      icon: <VideoCameraOutlined />,
      title: '生成视频',
      value: overview?.videos_count || 0,
      color: '#8b5cf6',
      bg: 'from-violet-500 to-purple-500',
      light: 'bg-violet-50'
    },
    {
      icon: <ProjectOutlined />,
      title: '创建项目',
      value: overview?.projects_count || 0,
      color: '#f59e0b',
      bg: 'from-amber-500 to-orange-500',
      light: 'bg-amber-50'
    }
  ]

  const getTotal = () => {
    if (!overview) return 1
    return overview.conversations_count + overview.videos_count + overview.projects_count || 1
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            数据统计
          </h2>
          <p className="text-gray-500 mt-1">查看平台运营数据与趋势分析</p>
        </div>
        <Radio.Group value={period} onChange={e => setPeriod(e.target.value)} buttonStyle="solid">
          <Radio.Button value="day">今天</Radio.Button>
          <Radio.Button value="week">近一周</Radio.Button>
          <Radio.Button value="month">近一月</Radio.Button>
        </Radio.Group>
      </div>

      <Row gutter={[16, 16]}>
        {statCards.map((stat, index) => (
          <Col xs={24} sm={12} lg={6} key={index}>
            <Card 
              className="overflow-hidden shadow-sm hover:shadow-lg transition-shadow"
              bodyStyle={{ padding: 0 }}
            >
              <div className={`h-1 bg-gradient-to-r ${stat.bg}`} />
              <div className="p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-gray-500 mb-1">{stat.title}</p>
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl font-bold" style={{ color: stat.color }}>
                        {formatNumber(stat.value)}
                      </span>
                    </div>
                  </div>
                  <div className={`w-12 h-12 rounded-xl ${stat.light} flex items-center justify-center`}>
                    <span style={{ color: stat.color, fontSize: '20px' }}>{stat.icon}</span>
                  </div>
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card className="shadow-sm h-full">
            <div className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl h-full">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
                  <BarChartOutlined className="text-white" />
                </div>
                <div>
                  <div className="font-bold text-gray-800">活动占比分析</div>
                  <div className="text-sm text-gray-500">各类活动占比</div>
                </div>
              </div>
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-600">对话次数</span>
                    <span className="text-sm font-medium text-emerald-600">
                      {((overview?.conversations_count || 0) / getTotal() * 100).toFixed(1)}%
                    </span>
                  </div>
                  <Progress 
                    percent={(overview?.conversations_count || 0) / getTotal() * 100}
                    strokeColor="#10b981"
                    showInfo={false}
                    size="small"
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-600">视频生成</span>
                    <span className="text-sm font-medium text-violet-600">
                      {((overview?.videos_count || 0) / getTotal() * 100).toFixed(1)}%
                    </span>
                  </div>
                  <Progress 
                    percent={(overview?.videos_count || 0) / getTotal() * 100}
                    strokeColor="#8b5cf6"
                    showInfo={false}
                    size="small"
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-600">项目创建</span>
                    <span className="text-sm font-medium text-amber-600">
                      {((overview?.projects_count || 0) / getTotal() * 100).toFixed(1)}%
                    </span>
                  </div>
                  <Progress 
                    percent={(overview?.projects_count || 0) / getTotal() * 100}
                    strokeColor="#f59e0b"
                    showInfo={false}
                    size="small"
                  />
                </div>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} md={16}>
          <Card 
            title={
              <div className="flex items-center gap-2">
                <LineChartOutlined className="text-blue-500" />
                <span className="font-bold">对话趋势</span>
              </div>
            }
            className="shadow-sm h-full"
          >
            {trend.length === 0 ? (
              <Empty description="暂无数据" className="py-8" />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorConversations" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis 
                    dataKey="date" 
                    stroke="#9ca3af" 
                    fontSize={12}
                    tickLine={false}
                  />
                  <YAxis 
                    stroke="#9ca3af" 
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px' }}
                    labelFormatter={(label) => {
                      const item = chartData.find(d => d.date === label)
                      return item?.fullDate || label
                    }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="conversations_count"
                    name="对话次数"
                    stroke="#10b981"
                    strokeWidth={2}
                    fill="url(#colorConversations)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card 
            title={
              <div className="flex items-center gap-2">
                <VideoCameraOutlined className="text-violet-500" />
                <span className="font-bold">视频生成趋势</span>
              </div>
            }
            className="shadow-sm"
          >
            {trend.length === 0 ? (
              <Empty description="暂无数据" className="py-8" />
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                  <XAxis 
                    dataKey="date" 
                    stroke="#9ca3af" 
                    fontSize={12}
                    tickLine={false}
                  />
                  <YAxis 
                    stroke="#9ca3af" 
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px' }}
                    labelFormatter={(label) => {
                      const item = chartData.find(d => d.date === label)
                      return item?.fullDate || label
                    }}
                  />
                  <Legend />
                  <Bar 
                    dataKey="videos_count" 
                    name="视频数量" 
                    fill="#8b5cf6" 
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card 
            title={
              <div className="flex items-center gap-2">
                <ProjectOutlined className="text-amber-500" />
                <span className="font-bold">项目创建趋势</span>
              </div>
            }
            className="shadow-sm"
          >
            {trend.length === 0 ? (
              <Empty description="暂无数据" className="py-8" />
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorProjects" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis 
                    dataKey="date" 
                    stroke="#9ca3af" 
                    fontSize={12}
                    tickLine={false}
                  />
                  <YAxis 
                    stroke="#9ca3af" 
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px' }}
                    labelFormatter={(label) => {
                      const item = chartData.find(d => d.date === label)
                      return item?.fullDate || label
                    }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="projects_count"
                    name="项目数量"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    fill="url(#colorProjects)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
      </Row>

      <Card className="shadow-sm">
        <div className="p-4 bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center">
              <ThunderboltOutlined className="text-white" />
            </div>
            <div>
              <div className="font-bold text-gray-800">API 调用统计</div>
              <div className="text-sm text-gray-500">统计周期内的 API 请求次数</div>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div>
                <div className="text-3xl font-bold text-purple-600">
                  {formatNumber(overview?.api_calls_count || 0)}
                </div>
                <div className="text-sm text-gray-500">API 调用次数</div>
              </div>
              <Tag color="purple" className="px-4 py-2 text-sm">
                <RiseOutlined /> {period === 'day' ? '今日' : period === 'week' ? '本周' : '本月'}
              </Tag>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-500">平均每用户</div>
              <div className="text-lg font-medium text-gray-700">
                {overview?.active_users ? formatNumber(Math.round((overview?.api_calls_count || 0) / overview.active_users)) : 0} 次
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}