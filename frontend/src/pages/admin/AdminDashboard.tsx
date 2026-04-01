import { useState, useEffect } from 'react'
import { Row, Col, Card, Space, Tag, Progress, Spin, Empty } from 'antd'
import {
  UserOutlined, ProjectOutlined, VideoCameraOutlined,
  TeamOutlined, LockOutlined, EyeOutlined,
  SafetyCertificateOutlined, ThunderboltOutlined, ClockCircleOutlined, RiseOutlined, FireOutlined
} from '@ant-design/icons'
import { PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, AreaChart, Area } from 'recharts'
import { adminApi, SystemStats } from '../../services/admin'
import { useNavigate } from 'react-router-dom'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

export default function AdminDashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [trend, setTrend] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [statsRes, trendRes] = await Promise.all([
        adminApi.getSystemStats(),
        adminApi.getStatisticsTrend('week')
      ])
      setStats(statsRes.data)
      setTrend(trendRes.data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    } finally {
      setLoading(false)
    }
  }

  const getUsageColor = (usage: number) => {
    if (usage >= 90) return '#ef4444'
    if (usage >= 70) return '#f59e0b'
    return '#10b981'
  }

  const getUsageStatus = (usage: number) => {
    if (usage >= 90) return 'danger'
    if (usage >= 70) return 'warning'
    return 'normal'
  }

  const renderCircularProgress = (value: number, label: string, icon: React.ReactNode) => {
    const color = getUsageColor(value)
    const size = 120
    const strokeWidth = 8
    const radius = (size - strokeWidth) / 2
    const circumference = radius * 2 * Math.PI
    const offset = circumference - (value / 100) * circumference

    return (
      <div className="flex flex-col items-center">
        <div className="relative" style={{ width: size, height: size }}>
          <svg width={size} height={size} className="transform -rotate-90">
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke="#e5e7eb"
              strokeWidth={strokeWidth}
              fill="none"
            />
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke={color}
              strokeWidth={strokeWidth}
              fill="none"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              className="transition-all duration-500"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold" style={{ color }}>{value.toFixed(1)}%</span>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2">
          {icon}
          <span className="text-gray-600 font-medium">{label}</span>
        </div>
      </div>
    )
  }

  const getTrendChartData = () => {
    return trend.slice(-7).map((item, index) => ({
      ...item,
      date: item.date.slice(5),
      fullDate: item.date
    }))
  }

  const chartData = getTrendChartData()

  const statCards = [
    { 
      icon: <UserOutlined />, 
      title: '总用户数', 
      value: stats?.total_users || 0, 
      suffix: '人',
      color: '#6366f1',
      bg: 'from-indigo-500 to-purple-500',
      light: 'bg-indigo-50'
    },
    { 
      icon: <TeamOutlined />, 
      title: '活跃用户', 
      value: stats?.active_users || 0, 
      suffix: '人',
      color: '#10b981',
      bg: 'from-emerald-500 to-teal-500',
      light: 'bg-emerald-50'
    },
    { 
      icon: <ProjectOutlined />, 
      title: '总项目数', 
      value: stats?.total_projects || 0, 
      suffix: '个',
      color: '#8b5cf6',
      bg: 'from-violet-500 to-purple-500',
      light: 'bg-violet-50'
    },
    { 
      icon: <VideoCameraOutlined />, 
      title: '生成视频', 
      value: stats?.total_videos || 0, 
      suffix: '个',
      color: '#f59e0b',
      bg: 'from-amber-500 to-orange-500',
      light: 'bg-amber-50'
    },
  ]

  const quickActions = [
    { icon: <TeamOutlined />, title: '用户管理', desc: '管理平台用户', path: '/admin/users', color: '#6366f1', bg: 'bg-indigo-500' },
    { icon: <EyeOutlined />, title: '操作日志', desc: '查看系统日志', path: '/admin/logs', color: '#8b5cf6', bg: 'bg-violet-500' },
    { icon: <LockOutlined />, title: '安全设置', desc: '系统安全配置', path: '/admin/settings', color: '#f59e0b', bg: 'bg-amber-500' },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            管理控制台
          </h1>
          <p className="text-gray-500 mt-1">欢迎回来，管理员</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <ClockCircleOutlined />
          <span>{new Date().toLocaleDateString('zh-CN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</span>
        </div>
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
                        {stat.value}
                      </span>
                      <span className="text-gray-400 text-sm">{stat.suffix}</span>
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
        <Col xs={24} lg={12}>
          <Card 
            title={
              <div className="flex items-center gap-2">
                <ThunderboltOutlined className="text-yellow-500" />
                <span className="font-bold">系统资源监控</span>
              </div>
            }
            className="shadow-sm"
          >
            {!stats ? (
              <Empty description="暂无数据" />
            ) : (
              <div className="grid grid-cols-3 gap-8">
                {renderCircularProgress(
                  stats.cpu_usage || 0,
                  'CPU 使用率',
                  <FireOutlined style={{ color: getUsageColor(stats.cpu_usage || 0) }} />
                )}
                {renderCircularProgress(
                  stats.memory_usage || 0,
                  '内存使用率',
                  <ProjectOutlined style={{ color: getUsageColor(stats.memory_usage || 0) }} />
                )}
                {renderCircularProgress(
                  stats.disk_usage || 0,
                  '磁盘使用率',
                  <VideoCameraOutlined style={{ color: getUsageColor(stats.disk_usage || 0) }} />
                )}
              </div>
            )}
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card 
            title={
              <div className="flex items-center gap-2">
                <RiseOutlined className="text-green-500" />
                <span className="font-bold">快捷操作</span>
              </div>
            }
            className="shadow-sm h-full"
          >
            <Row gutter={[16, 16]}>
              {quickActions.map((action, index) => (
                <Col span={8} key={index}>
                  <div 
                    onClick={() => navigate(action.path)}
                    className="text-center p-6 rounded-xl cursor-pointer transition-all hover:shadow-md hover:-translate-y-1 bg-gray-50 hover:bg-white"
                  >
                    <div className={`w-14 h-14 rounded-xl ${action.bg} flex items-center justify-center mx-auto mb-3 shadow-lg`}>
                      <span className="text-2xl text-white">{action.icon}</span>
                    </div>
                    <div className="font-semibold text-gray-800 mb-1">{action.title}</div>
                    <div className="text-xs text-gray-500">{action.desc}</div>
                  </div>
                </Col>
              ))}
            </Row>
            
            <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <SafetyCertificateOutlined className="text-green-500 text-lg" />
                  <span className="text-gray-600 font-medium">系统状态</span>
                </div>
                <Tag color="success" className="px-3 py-1 text-sm font-medium">
                  运行正常
                </Tag>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      <Card 
        title={
          <div className="flex items-center gap-2">
            <ClockCircleOutlined className="text-blue-500" />
            <span className="font-bold">近 7 天趋势</span>
          </div>
        }
        className="shadow-sm"
      >
        {trend.length === 0 ? (
          <Empty description="暂无趋势数据" />
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorVideos" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                </linearGradient>
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
                formatter={(value: any) => [value, '']}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="videos_count"
                name="视频生成"
                stroke="#8b5cf6"
                strokeWidth={2}
                fill="url(#colorVideos)"
              />
              <Area
                type="monotone"
                dataKey="projects_count"
                name="项目创建"
                stroke="#f59e0b"
                strokeWidth={2}
                fill="url(#colorProjects)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card className="shadow-sm">
            <div className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
                  <ThunderboltOutlined className="text-white" />
                </div>
                <div>
                  <div className="font-bold text-gray-800">API 调用统计</div>
                  <div className="text-sm text-gray-500">今日调用次数</div>
                </div>
              </div>
              <div className="text-4xl font-bold text-blue-600 mb-2">
                {stats?.api_calls_today || 0}
              </div>
              <Progress 
                percent={Math.min((stats?.api_calls_today || 0) / 1000 * 100, 100)} 
                strokeColor="#3b82f6"
                showInfo={false}
                size="small"
              />
              <p className="text-xs text-gray-400 mt-2">目标: 1000 次/天</p>
            </div>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card className="shadow-sm">
            <div className="p-4 bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center">
                  <RiseOutlined className="text-white" />
                </div>
                <div>
                  <div className="font-bold text-gray-800">数据统计</div>
                  <div className="text-sm text-gray-500">本周活跃度</div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4 mt-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">{stats?.total_users || 0}</div>
                  <div className="text-xs text-gray-500">用户</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-pink-600">{stats?.total_projects || 0}</div>
                  <div className="text-xs text-gray-500">项目</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-indigo-600">{stats?.total_videos || 0}</div>
                  <div className="text-xs text-gray-500">视频</div>
                </div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}