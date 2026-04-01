import { useState, useEffect, useMemo } from 'react'
import { Table, Card, Select, Tag, Button, Space, Row, Col, Statistic, DatePicker } from 'antd'
import { ReloadOutlined, FileTextOutlined, UserOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import dayjs from 'dayjs'
import { adminApi, AuditLog } from '../../services/admin'

const COLORS = ['#10b981', '#ef4444', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

export default function AdminLogs() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(false)
  const [actionFilter, setActionFilter] = useState<string>('')
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null)

  useEffect(() => {
    fetchLogs()
  }, [])

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const res = await adminApi.getAuditLogs({ limit: 100 })
      setLogs(res.data)
    } catch (err) {
      console.error('Failed to fetch logs:', err)
    } finally {
      setLoading(false)
    }
  }

  const getActionColor = (action: string) => {
    if (action.includes('SUCCESS') || action.includes('CREATE') || action.includes('ENABLE')) return 'success'
    if (action.includes('FAILED') || action.includes('DELETE') || action.includes('DISABLE')) return 'error'
    if (action.includes('UPDATE')) return 'processing'
    if (action.includes('REGISTER')) return 'cyan'
    return 'default'
  }

  const getActionLabel = (action: string) => {
    const labels: Record<string, string> = {
      'LOGIN_SUCCESS': '登录成功',
      'LOGIN_FAILED': '登录失败',
      'LOGOUT': '登出',
      'USER_REGISTER': '注册',
      'USER_UPDATE': '更新',
      'USER_ENABLE': '启用',
      'USER_DISABLE': '禁用',
      'USER_DELETE': '删除',
    }
    return labels[action] || action
  }

  const stats = useMemo(() => {
    const today = dayjs().startOf('day')
    const todayLogs = logs.filter(log => dayjs(log.created_at).isAfter(today))
    
    const actionCounts: Record<string, number> = {}
    logs.forEach(log => {
      const type = log.action.includes('LOGIN') ? '登录相关' :
                   log.action.includes('USER') ? '用户管理' : '其他'
      actionCounts[type] = (actionCounts[type] || 0) + 1
    })

    const pieData = Object.entries(actionCounts).map(([name, value]) => ({ name, value }))
    
    return {
      total: logs.length,
      todayCount: todayLogs.length,
      successCount: logs.filter(l => l.action.includes('SUCCESS') || l.action.includes('ENABLE')).length,
      failCount: logs.filter(l => l.action.includes('FAILED') || l.action.includes('DISABLE')).length,
      pieData
    }
  }, [logs])

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => (
        <span className="text-sm font-mono">{new Date(date).toLocaleString('zh-CN')}</span>
      ),
    },
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      width: 120,
      render: (name: string) => (
        <span className={name ? '' : 'text-gray-400'}>
          {name || '系统'}
        </span>
      ),
    },
    {
      title: '操作类型',
      dataIndex: 'action',
      key: 'action',
      width: 120,
      render: (action: string) => (
        <Tag color={getActionColor(action)}>{getActionLabel(action)}</Tag>
      ),
    },
    {
      title: '操作详情',
      dataIndex: 'details',
      key: 'details',
      ellipsis: true,
      render: (details: string) => (
        <span className="text-gray-600">{details || '-'}</span>
      ),
    },
    {
      title: 'IP 地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 140,
      render: (ip: string) => (
        <code className="text-sm bg-gray-100 px-2 py-1 rounded">{ip || '-'}</code>
      ),
    },
  ]

  const filteredLogs = useMemo(() => {
    let result = logs
    if (actionFilter) {
      result = result.filter(log => log.action.includes(actionFilter))
    }
    if (dateRange && dateRange[0] && dateRange[1]) {
      result = result.filter(log => {
        const logDate = dayjs(log.created_at)
        return logDate.isAfter(dateRange[0].startOf('day')) && 
               logDate.isBefore(dateRange[1].endOf('day'))
      })
    }
    return result
  }, [logs, actionFilter, dateRange])

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold">审计日志</h2>
        <p className="text-gray-500 mt-1">查看系统操作记录</p>
      </div>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card className="hover-lift" style={{ borderRadius: '12px' }}>
            <Statistic
              title="日志总数"
              value={stats.total}
              prefix={<FileTextOutlined className="text-blue-500" />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="hover-lift" style={{ borderRadius: '12px' }}>
            <Statistic
              title="今日记录"
              value={stats.todayCount}
              prefix={<UserOutlined className="text-green-500" />}
              valueStyle={{ color: '#10b981' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="hover-lift" style={{ borderRadius: '12px' }}>
            <Statistic
              title="成功操作"
              value={stats.successCount}
              prefix={<CheckCircleOutlined className="text-emerald-500" />}
              valueStyle={{ color: '#10b981' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="hover-lift" style={{ borderRadius: '12px' }}>
            <Statistic
              title="失败/禁用"
              value={stats.failCount}
              prefix={<WarningOutlined className="text-red-500" />}
              valueStyle={{ color: '#ef4444' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} lg={16}>
          <Card className="hover-lift" style={{ borderRadius: '16px' }}>
            <Space wrap>
              <Select
                placeholder="筛选操作类型"
                value={actionFilter || undefined}
                onChange={setActionFilter}
                allowClear
                style={{ width: 150 }}
              >
                <Select.Option value="LOGIN_SUCCESS">登录成功</Select.Option>
                <Select.Option value="LOGIN_FAILED">登录失败</Select.Option>
                <Select.Option value="LOGOUT">登出</Select.Option>
                <Select.Option value="USER_REGISTER">用户注册</Select.Option>
                <Select.Option value="USER_UPDATE">用户更新</Select.Option>
                <Select.Option value="USER_ENABLE">用户启用</Select.Option>
                <Select.Option value="USER_DISABLE">用户禁用</Select.Option>
                <Select.Option value="USER_DELETE">用户删除</Select.Option>
              </Select>
              <DatePicker.RangePicker 
                value={dateRange as [dayjs.Dayjs, dayjs.Dayjs]}
                onChange={(dates) => setDateRange(dates)}
                placeholder={['开始日期', '结束日期']}
              />
              <Button icon={<ReloadOutlined />} onClick={fetchLogs}>
                刷新日志
              </Button>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card className="hover-lift" style={{ borderRadius: '16px', height: '100%' }}>
            <div className="text-center text-gray-500 text-sm mb-2">操作类型分布</div>
            <ResponsiveContainer width="100%" height={150}>
              <PieChart>
                <Pie
                  data={stats.pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={60}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {stats.pieData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Card className="hover-lift" style={{ borderRadius: '16px' }}>
        <Table
          columns={columns}
          dataSource={filteredLogs}
          rowKey="id"
          loading={loading}
          pagination={{ 
            pageSize: 15, 
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`
          }}
          scroll={{ x: 800 }}
        />
      </Card>
    </div>
  )
}
