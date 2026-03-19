import { useState, useEffect } from 'react'
import { Table, Card, Select, Tag, Button, Space } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { adminApi, AuditLog } from '../../services/admin'

export default function AdminLogs() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(false)
  const [actionFilter, setActionFilter] = useState<string>('')

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

  const filteredLogs = actionFilter
    ? logs.filter(log => log.action.includes(actionFilter))
    : logs

  return (
    <div>
      <Card className="mb-4 hover-lift" style={{ borderRadius: '16px' }}>
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
          <Button icon={<ReloadOutlined />} onClick={fetchLogs}>
            刷新日志
          </Button>
        </Space>
      </Card>

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
