import { useState, useEffect } from 'react'
import { Card, Table, Row, Col, Spin, Button, Radio, Progress, Tag, Empty } from 'antd'
import { ReloadOutlined, MessageOutlined, CodeOutlined, ThunderboltOutlined, TrophyOutlined } from '@ant-design/icons'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { adminApi, TokenUsageResponse } from '@/services/admin'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

const formatNumber = (num: number) => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(2) + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toLocaleString('zh-CN')
}

const formatFullNumber = (num: number) => {
  return num.toLocaleString('zh-CN')
}

export default function AdminTokenUsage() {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<TokenUsageResponse | null>(null)
  const [period, setPeriod] = useState<'day' | 'week' | 'month'>('day')

  const fetchTokenUsage = async () => {
    setLoading(true)
    try {
      const { data: res } = await adminApi.getTokenUsage(period)
      setData(res)
    } catch (error) {
      console.error('获取 Token 统计失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTokenUsage()
  }, [period])

  const getPieData = () => {
    if (!data) return []
    return [
      { name: '对话 Token', value: data.total_chat_tokens, color: '#3b82f6' },
      { name: '代码 Token', value: data.total_code_tokens, color: '#10b981' }
    ]
  }

  const getTopUsersChartData = () => {
    if (!data?.users) return []
    return data.users.slice(0, 10).map((user, index) => ({
      name: user.username.slice(0, 6),
      fullName: user.username,
      对话: user.chat_token_usage,
      代码: user.code_token_usage,
      color: COLORS[index % COLORS.length]
    }))
  }

  const columns = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 60,
      render: (rank: number) => {
        if (rank === 1) return <Tag color="gold" className="flex items-center gap-1"><TrophyOutlined /> 1</Tag>
        if (rank === 2) return <Tag color="silver">2</Tag>
        if (rank === 3) return <Tag color="#cd7f32">3</Tag>
        return <span className="text-gray-500">{rank}</span>
      }
    },
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      render: (username: string) => (
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-xs font-bold">
            {username[0].toUpperCase()}
          </div>
          <span className="font-medium">{username}</span>
        </div>
      )
    },
    {
      title: '对话 Token',
      dataIndex: 'chat_token_usage',
      key: 'chat_token_usage',
      render: (val: number) => (
        <div className="flex items-center gap-2">
          <Progress 
            percent={data ? (val / (data.total_chat_tokens || 1)) * 100 : 0} 
            size="small" 
            showInfo={false}
            strokeColor="#3b82f6"
            className="w-16"
          />
          <span className="text-blue-600 font-mono">{formatNumber(val)}</span>
        </div>
      )
    },
    {
      title: '代码 Token',
      dataIndex: 'code_token_usage',
      key: 'code_token_usage',
      render: (val: number) => (
        <div className="flex items-center gap-2">
          <Progress 
            percent={data ? (val / (data.total_code_tokens || 1)) * 100 : 0} 
            size="small" 
            showInfo={false}
            strokeColor="#10b981"
            className="w-16"
          />
          <span className="text-green-600 font-mono">{formatNumber(val)}</span>
        </div>
      )
    },
    {
      title: '总计',
      dataIndex: 'total_token_usage',
      key: 'total_token_usage',
      render: (val: number) => (
        <Tag color="purple" className="font-mono text-sm px-3 py-1">
          {formatNumber(val)}
        </Tag>
      )
    }
  ]

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <Spin size="large" />
      </div>
    )
  }

  const totalTokens = data?.total_tokens || 0
  const chatPercent = data ? ((data.total_chat_tokens / (totalTokens || 1)) * 100).toFixed(1) : '0'
  const codePercent = data ? ((data.total_code_tokens / (totalTokens || 1)) * 100).toFixed(1) : '0'

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Token 使用统计
          </h2>
          <p className="text-gray-500 mt-1">查看平台 Token 消耗详情</p>
        </div>
        <div className="flex items-center gap-4">
          <Radio.Group value={period} onChange={e => setPeriod(e.target.value)} buttonStyle="solid">
            <Radio.Button value="day">今天</Radio.Button>
            <Radio.Button value="week">近一周</Radio.Button>
            <Radio.Button value="month">近一月</Radio.Button>
          </Radio.Group>
          <Button icon={<ReloadOutlined />} onClick={fetchTokenUsage}>
            刷新
          </Button>
        </div>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card className="overflow-hidden relative h-full">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-blue-400" />
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 mb-1">对话 Token</p>
                <p className="text-2xl font-bold text-blue-600">{formatNumber(data?.total_chat_tokens || 0)}</p>
                <p className="text-xs text-gray-400 mt-1">{chatPercent}% 占比</p>
              </div>
              <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                <MessageOutlined className="text-2xl text-blue-500" />
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card className="overflow-hidden relative h-full">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-green-500 to-green-400" />
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 mb-1">代码 Token</p>
                <p className="text-2xl font-bold text-green-600">{formatNumber(data?.total_code_tokens || 0)}</p>
                <p className="text-xs text-gray-400 mt-1">{codePercent}% 占比</p>
              </div>
              <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                <CodeOutlined className="text-2xl text-green-500" />
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card className="overflow-hidden relative h-full">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-purple-400" />
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 mb-1">Token 总计</p>
                <p className="text-2xl font-bold text-purple-600">{formatNumber(totalTokens)}</p>
                <p className="text-xs text-gray-400 mt-1">{data?.users?.length || 0} 位用户</p>
              </div>
              <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center">
                <ThunderboltOutlined className="text-2xl text-purple-500" />
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card title={<span className="font-bold text-gray-700">📊 Token 分布</span>} className="h-full shadow-sm">
            {!data || totalTokens === 0 ? (
              <Empty description="暂无数据" className="py-8" />
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={getPieData()}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={5}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {getPieData().map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    formatter={(value) => formatFullNumber(value as number)}
                    contentStyle={{ borderRadius: '8px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card title={<span className="font-bold text-gray-700">🏆 TOP 10 用户 Token 消耗</span>} className="h-full shadow-sm">
            {!data || data.users.length === 0 ? (
              <Empty description="暂无数据" className="py-8" />
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={getTopUsersChartData()} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={true} vertical={false} />
                  <XAxis type="number" stroke="#9ca3af" fontSize={11} tickLine={false} />
                  <YAxis 
                    dataKey="name" 
                    type="category" 
                    stroke="#9ca3af" 
                    fontSize={11} 
                    tickLine={false}
                    width={60}
                  />
                  <Tooltip 
                    formatter={(value) => formatFullNumber(value as number)}
                    labelFormatter={(label) => {
                      const item = getTopUsersChartData().find(d => d.name === label)
                      return item?.fullName || label
                    }}
                    contentStyle={{ borderRadius: '8px' }}
                  />
                  <Legend />
                  <Bar dataKey="对话" stackId="a" fill="#3b82f6" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="代码" stackId="a" fill="#10b981" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
      </Row>

      <Card title={<span className="font-bold text-gray-700">📋 用户 Token 详细排行</span>} className="shadow-sm">
        <Table
          dataSource={data?.users || []}
          columns={columns}
          rowKey="id"
          pagination={{ pageSize: 10, showSizeChanger: false }}
          locale={{ emptyText: '暂无 Token 使用记录' }}
          className="overflow-x-auto"
        />
      </Card>
    </div>
  )
}