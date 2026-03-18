import { useState, useEffect } from 'react'
import { Table, Card, Select, Tag, Button } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { adminApi, AuditLog } from '../../services/admin'

const { Option } = Select

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
    if (action.includes('SUCCESS') || action.includes('CREATE') || action.includes('ENABLE')) return 'green'
    if (action.includes('FAILED') || action.includes('DELETE') || action.includes('DISABLE')) return 'red'
    if (action.includes('UPDATE')) return 'blue'
    if (action.includes('REGISTER')) return 'cyan'
    return 'default'
  }

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => (
        <span className="text-sm">{new Date(date).toLocaleString('zh-CN')}</span>
      ),
    },
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      width: 120,
      render: (name: string) => name || <span className="text-gray">系统</span>,
    },
    {
      title: '操作类型',
      dataIndex: 'action',
      key: 'action',
      width: 150,
      render: (action: string) => (
        <Tag color={getActionColor(action)}>{action}</Tag>
      ),
    },
    {
      title: '操作详情',
      dataIndex: 'details',
      key: 'details',
      ellipsis: true,
    },
    {
      title: 'IP 地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 140,
      render: (ip: string) => ip || '-',
    },
  ]

  const filteredLogs = actionFilter
    ? logs.filter(log => log.action.includes(actionFilter))
    : logs

  return (
    <div>
      <Card className="admin-card mb-4">
        <div className="flex flex-wrap gap-3 items-center">
          <Select
            placeholder="筛选操作类型"
            value={actionFilter || undefined}
            onChange={setActionFilter}
            allowClear
            style={{ width: 160 }}
            className="flex-1 min-w-[120px]"
          >
            <Option value="LOGIN_SUCCESS">登录成功</Option>
            <Option value="LOGIN_FAILED">登录失败</Option>
            <Option value="LOGOUT">登出</Option>
            <Option value="USER_REGISTER">用户注册</Option>
            <Option value="USER_UPDATE">用户更新</Option>
            <Option value="USER_ENABLE">用户启用</Option>
            <Option value="USER_DISABLE">用户禁用</Option>
            <Option value="USER_DELETE">用户删除</Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={fetchLogs}>
            刷新
          </Button>
        </div>
      </Card>

      <Card className="admin-card">
        <Table
          columns={columns}
          dataSource={filteredLogs}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 15, showSizeChanger: true }}
          className="admin-table"
          scroll={{ x: 800 }}
        />
      </Card>
    </div>
  )
}
