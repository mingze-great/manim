import { useState, useEffect } from 'react'
import { Card, Table, Statistic, Row, Col, Spin, Button, Radio } from 'antd'
import { ReloadOutlined, MessageOutlined, CodeOutlined, DollarOutlined } from '@ant-design/icons'
import { adminApi, TokenUsageResponse } from '@/services/admin'

const formatNumber = (num: number) => {
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

  const columns = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 60,
      render: (rank: number) => {
        const colors = ['#ffd700', '#c0c0c0', '#cd7f32']
        return (
          <span style={{ 
            color: rank <= 3 ? colors[rank - 1] : '#666',
            fontWeight: rank <= 3 ? 'bold' : 'normal'
          }}>
            {rank}
          </span>
        )
      }
    },
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '对话 Token',
      dataIndex: 'chat_token_usage',
      key: 'chat_token_usage',
      render: (val: number) => formatNumber(val)
    },
    {
      title: '代码 Token',
      dataIndex: 'code_token_usage',
      key: 'code_token_usage',
      render: (val: number) => formatNumber(val)
    },
    {
      title: '总计',
      dataIndex: 'total_token_usage',
      key: 'total_token_usage',
      render: (val: number) => <strong>{formatNumber(val)}</strong>
    }
  ]

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div className="p-6">
      <Card 
        title="Token 使用统计" 
        extra={
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
        }
        className="mb-4"
      >
        <Row gutter={24}>
          <Col span={8}>
            <Statistic 
              title="对话 Token 总量" 
              value={data?.total_chat_tokens || 0}
              formatter={(val) => formatNumber(val as number)}
              prefix={<MessageOutlined style={{ color: '#1890ff' }} />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col span={8}>
            <Statistic 
              title="代码 Token 总量" 
              value={data?.total_code_tokens || 0}
              formatter={(val) => formatNumber(val as number)}
              prefix={<CodeOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col span={8}>
            <Statistic 
              title="Token 总计" 
              value={data?.total_tokens || 0}
              formatter={(val) => formatNumber(val as number)}
              prefix={<DollarOutlined style={{ color: '#722ed1' }} />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Col>
        </Row>
      </Card>

      <Card title="用户 Token 排行">
        <Table
          dataSource={data?.users || []}
          columns={columns}
          rowKey="id"
          pagination={{ pageSize: 20 }}
          locale={{ emptyText: '暂无 Token 使用记录' }}
        />
      </Card>
    </div>
  )
}