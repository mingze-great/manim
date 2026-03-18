import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Table, Card, Statistic, Row, Col, Tag, Button, Input, Space,
  Modal, Descriptions, message, Popconfirm, Tabs, Badge
} from 'antd'
import {
  UserOutlined, ProjectOutlined, VideoCameraOutlined,
  SafetyOutlined, SearchOutlined, DeleteOutlined,
  LockOutlined, UnlockOutlined, EyeOutlined
} from '@ant-design/icons'
import { adminApi, User, AuditLog, SystemStats } from '../services/admin'
import { useAuthStore } from '../stores/authStore'

const { TabPane } = Tabs

export default function Admin() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [userStats, setUserStats] = useState<any>(null)
  const [searchText, setSearchText] = useState('')

  useEffect(() => {
    if (!user?.is_admin) {
      message.error('需要管理员权限')
      navigate('/')
      return
    }
    fetchStats()
    fetchUsers()
    fetchAuditLogs()
  }, [])

  const fetchStats = async () => {
    try {
      const res = await adminApi.getSystemStats()
      setStats(res.data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  const fetchUsers = async (search?: string) => {
    setLoading(true)
    try {
      const res = await adminApi.getUsers({ search: search || searchText, limit: 50 })
      setUsers(res.data as any)
    } catch (err) {
      message.error('获取用户列表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchAuditLogs = async () => {
    try {
      const res = await adminApi.getAuditLogs({ limit: 50 })
      setAuditLogs(res.data)
    } catch (err) {
      console.error('Failed to fetch audit logs:', err)
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
      fetchStats()
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

  const handleSearch = () => {
    fetchUsers(searchText)
  }

  const getActionColor = (action: string) => {
    if (action.includes('SUCCESS') || action.includes('CREATE')) return 'green'
    if (action.includes('FAILED') || action.includes('DELETE')) return 'red'
    if (action.includes('UPDATE') || action.includes('ENABLE') || action.includes('DISABLE')) return 'blue'
    return 'default'
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Badge status={isActive ? 'success' : 'error'} text={isActive ? '正常' : '已禁用'} />
      ),
    },
    {
      title: '角色',
      dataIndex: 'is_admin',
      key: 'is_admin',
      render: (isAdmin: boolean) => (
        isAdmin ? <Tag color="gold">管理员</Tag> : <Tag>用户</Tag>
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
      render: (_: any, record: User) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewUser(record)}
          >
            详情
          </Button>
          <Button
            type="link"
            icon={record.is_active ? <LockOutlined /> : <UnlockOutlined />}
            onClick={() => handleToggleActive(record.id)}
          >
            {record.is_active ? '禁用' : '启用'}
          </Button>
          <Popconfirm
            title="确定删除此用户？"
            description="删除后无法恢复，所有相关数据将被删除"
            onConfirm={() => handleDeleteUser(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const auditColumns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      render: (name: string) => name || '系统',
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      render: (action: string) => <Tag color={getActionColor(action)}>{action}</Tag>,
    },
    {
      title: '详情',
      dataIndex: 'details',
      key: 'details',
    },
    {
      title: 'IP',
      dataIndex: 'ip_address',
      key: 'ip_address',
    },
  ]

  return (
    <div className="p-4">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <SafetyOutlined /> 管理后台
        </h1>
        
        <Row gutter={16} className="mb-4">
          <Col span={6}>
            <Card>
              <Statistic
                title="总用户数"
                value={stats?.total_users || 0}
                prefix={<UserOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="活跃用户"
                value={stats?.active_users || 0}
                valueStyle={{ color: '#3f8600' }}
                prefix={<UserOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="总项目数"
                value={stats?.total_projects || 0}
                prefix={<ProjectOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="生成视频数"
                value={stats?.total_videos || 0}
                prefix={<VideoCameraOutlined />}
              />
            </Card>
          </Col>
        </Row>
      </div>

      <Card>
        <Tabs defaultActiveKey="users">
          <TabPane tab="用户管理" key="users">
            <div className="mb-4 flex gap-2">
              <Input.Search
                placeholder="搜索用户名或邮箱"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                onSearch={handleSearch}
                style={{ width: 300 }}
                allowClear
              />
              <Button icon={<SearchOutlined />} onClick={() => fetchUsers()}>
                刷新
              </Button>
            </div>
            
            <Table
              columns={columns}
              dataSource={users}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </TabPane>
          
          <TabPane tab="操作日志" key="logs">
            <Table
              columns={auditColumns}
              dataSource={auditLogs}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </TabPane>
        </Tabs>
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
        width={600}
      >
        {selectedUser && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="ID">{selectedUser.id}</Descriptions.Item>
            <Descriptions.Item label="用户名">{selectedUser.username}</Descriptions.Item>
            <Descriptions.Item label="邮箱">{selectedUser.email}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Badge status={selectedUser.is_active ? 'success' : 'error'} 
                     text={selectedUser.is_active ? '正常' : '已禁用'} />
            </Descriptions.Item>
            <Descriptions.Item label="角色">
              {selectedUser.is_admin ? '管理员' : '普通用户'}
            </Descriptions.Item>
            <Descriptions.Item label="注册时间">
              {new Date(selectedUser.created_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
          </Descriptions>
        )}
        
        {userStats && (
          <div className="mt-4">
            <h3 className="font-bold mb-2">使用统计</h3>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="项目数" value={userStats.total_projects} />
              </Col>
              <Col span={6}>
                <Statistic title="任务数" value={userStats.total_tasks} />
              </Col>
              <Col span={6}>
                <Statistic 
                  title="成功" 
                  value={userStats.completed_tasks} 
                  valueStyle={{ color: '#3f8600' }}
                />
              </Col>
              <Col span={6}>
                <Statistic 
                  title="失败" 
                  value={userStats.failed_tasks} 
                  valueStyle={{ color: '#cf1322' }}
                />
              </Col>
            </Row>
          </div>
        )}
      </Modal>
    </div>
  )
}
