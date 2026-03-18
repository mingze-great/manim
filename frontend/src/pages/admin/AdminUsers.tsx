import { useState, useEffect } from 'react'
import {
  Table, Card, Input, Button, Space, Tag, Popconfirm,
  Modal, Descriptions, message, Row, Col
} from 'antd'
import {
  ReloadOutlined, DeleteOutlined,
  LockOutlined, UnlockOutlined, EyeOutlined, UserOutlined
} from '@ant-design/icons'
import { adminApi, User, UserStats } from '../../services/admin'

export default function AdminUsers() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [userStats, setUserStats] = useState<UserStats | null>(null)

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async (search?: string) => {
    setLoading(true)
    try {
      const res = await adminApi.getUsers({ search: search || searchText, limit: 100 })
      setUsers(res.data as any)
    } catch (err) {
      message.error('获取用户列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleActive = async (userId: number) => {
    try {
      const res = await adminApi.toggleUserActive(userId)
      message.success(res.data.is_active ? '用户已启用' : '用户已禁用')
      fetchUsers()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '操作失败')
    }
  }

  const handleDeleteUser = async (userId: number) => {
    try {
      await adminApi.deleteUser(userId)
      message.success('用户已删除')
      fetchUsers()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '删除失败')
    }
  }

  const handleViewUser = async (user: User) => {
    setSelectedUser(user)
    try {
      const res = await adminApi.getUserStats(user.id)
      setUserStats(res.data)
    } catch (err) {
      setUserStats(null)
    }
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '用户',
      key: 'user',
      render: (_: any, record: User) => (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
            <UserOutlined className="text-blue" />
          </div>
          <div>
            <div className="font-medium">{record.username}</div>
            <div className="text-gray text-sm">{record.email}</div>
          </div>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive: boolean) => (
        <span className={isActive ? 'status-active' : 'status-inactive'}>
          {isActive ? '正常' : '已禁用'}
        </span>
      ),
    },
    {
      title: '角色',
      dataIndex: 'is_admin',
      key: 'is_admin',
      width: 100,
      render: (isAdmin: boolean) => (
        isAdmin ? <span className="status-admin">管理员</span> : <Tag>用户</Tag>
      ),
    },
    {
      title: '注册时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: User) => (
        <Space>
          <Button type="text" icon={<EyeOutlined />} onClick={() => handleViewUser(record)}>
            详情
          </Button>
          <Button
            type="text"
            icon={record.is_active ? <LockOutlined /> : <UnlockOutlined />}
            onClick={() => handleToggleActive(record.id)}
          >
            {record.is_active ? '禁用' : '启用'}
          </Button>
          <Popconfirm
            title="确定删除此用户？"
            description="删除后无法恢复"
            onConfirm={() => handleDeleteUser(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Card className="admin-card mb-4">
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Input.Search
              placeholder="搜索用户名或邮箱"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={() => fetchUsers()}
              className="max-w-xs"
              allowClear
            />
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={() => fetchUsers()}>
              刷新
            </Button>
          </Col>
        </Row>
      </Card>

      <Card className="admin-card">
        <Table
          columns={columns}
          dataSource={users}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10, showSizeChanger: true, showQuickJumper: true }}
          className="admin-table"
          scroll={{ x: 800 }}
        />
      </Card>

      <Modal
        title="用户详情"
        open={!!selectedUser}
        onCancel={() => setSelectedUser(null)}
        footer={[
          <Button key="close" onClick={() => setSelectedUser(null)}>
            关闭
          </Button>
        ]}
        width="90vw"
        style={{ maxWidth: 600 }}
      >
        {selectedUser && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="ID">{selectedUser.id}</Descriptions.Item>
            <Descriptions.Item label="用户名">{selectedUser.username}</Descriptions.Item>
            <Descriptions.Item label="邮箱">{selectedUser.email}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <span className={selectedUser.is_active ? 'status-active' : 'status-inactive'}>
                {selectedUser.is_active ? '正常' : '已禁用'}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="角色">
              {selectedUser.is_admin ? <span className="status-admin">管理员</span> : '普通用户'}
            </Descriptions.Item>
            <Descriptions.Item label="注册时间">
              {new Date(selectedUser.created_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
          </Descriptions>
        )}
        
        {userStats && (
          <Row gutter={[8, 8]} className="mt-4">
            <Col span={6}>
              <Card size="small">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue">{userStats.total_projects}</div>
                  <div className="text-gray text-sm">项目数</div>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green">{userStats.total_tasks}</div>
                  <div className="text-gray text-sm">任务数</div>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green">{userStats.completed_tasks}</div>
                  <div className="text-gray text-sm">成功</div>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <div className="text-center">
                  <div className="text-2xl font-bold text-red">{userStats.failed_tasks}</div>
                  <div className="text-gray text-sm">失败</div>
                </div>
              </Card>
            </Col>
          </Row>
        )}
      </Modal>
    </div>
  )
}
