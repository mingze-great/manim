import { useState, useEffect } from 'react'
import {
  Table, Card, Input, Button, Space, Tag, Popconfirm,
  Modal, Descriptions, message, Row, Col, Avatar, Badge, List, InputNumber
} from 'antd'
import {
  ReloadOutlined, DeleteOutlined, SearchOutlined,
  LockOutlined, UnlockOutlined, EyeOutlined, UserOutlined,
  ProjectOutlined, VideoCameraOutlined, CheckCircleOutlined, CloseCircleOutlined,
  PlusOutlined, CopyOutlined, KeyOutlined, EditOutlined
} from '@ant-design/icons'
import { adminApi, User, UserStats, InvitationCode } from '../../services/admin'

export default function AdminUsers() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [userStats, setUserStats] = useState<UserStats | null>(null)
  const [invitationCodes, setInvitationCodes] = useState<InvitationCode[]>([])
  const [generateCount, setGenerateCount] = useState(1)
  const [resetPasswordModalVisible, setResetPasswordModalVisible] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [resetLoading, setResetLoading] = useState(false)

  useEffect(() => {
    fetchUsers()
    fetchInvitationCodes()
  }, [])

  const fetchInvitationCodes = async () => {
    try {
      const res = await adminApi.getInvitationCodes()
      setInvitationCodes(res.data as any)
    } catch (err) {
      console.error('获取邀请码失败', err)
    }
  }

  const handleGenerateCodes = async () => {
    try {
      const res = await adminApi.generateInvitationCodes(generateCount)
      message.success(`成功生成 ${res.data.codes.length} 个邀请码`)
      fetchInvitationCodes()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '生成失败')
    }
  }

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code)
    message.success('已复制到剪贴板')
  }

  const handleResetPassword = async () => {
    if (!selectedUser || !newPassword) return
    setResetLoading(true)
    try {
      await (adminApi as any).resetPassword(selectedUser.id, newPassword)
      message.success('密码重置成功')
      setResetPasswordModalVisible(false)
      setNewPassword('')
    } catch (err: any) {
      message.error(err.response?.data?.detail || '重置失败')
    } finally {
      setResetLoading(false)
    }
  }

  const openResetPassword = (user: User) => {
    setSelectedUser(user)
    setResetPasswordModalVisible(true)
  }

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
      title: '用户',
      key: 'user',
      render: (_: any, record: User) => (
        <div className="flex items-center gap-3">
          <Avatar 
            style={{ backgroundColor: record.is_admin ? '#f59e0b' : '#6366f1' }}
            icon={record.is_admin ? <UserOutlined /> : <UserOutlined />}
            size={40}
          />
          <div>
            <div className="font-medium">{record.username}</div>
            <div className="text-gray-500 text-sm">{record.email}</div>
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
        <Badge status={isActive ? 'success' : 'error'} text={isActive ? '正常' : '已禁用'} />
      ),
    },
    {
      title: '角色',
      dataIndex: 'is_admin',
      key: 'is_admin',
      width: 100,
      render: (isAdmin: boolean) => (
        isAdmin ? <Tag color="gold">管理员</Tag> : <Tag color="default">用户</Tag>
      ),
    },
    {
      title: '注册时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_: any, record: User) => (
        <Space>
          <Button 
            type="primary" 
            ghost
            size="small"
            icon={<EyeOutlined />} 
            onClick={() => handleViewUser(record)}
          >
            详情
          </Button>
          <Button
            size="small"
            type={record.is_active ? 'default' : 'primary'}
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
            <Button type="text" danger size="small" icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Card className="mb-4 hover-lift" style={{ borderRadius: '16px' }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Input.Search
              placeholder="搜索用户名或邮箱..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={() => fetchUsers()}
              style={{ maxWidth: '300px' }}
              allowClear
              prefix={<SearchOutlined className="text-gray-400" />}
            />
          </Col>
          <Col>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={() => fetchUsers()}
              className="hover-lift"
            >
              刷新列表
            </Button>
          </Col>
        </Row>
      </Card>

      <Card className="hover-lift" style={{ borderRadius: '16px' }}>
        <Table
          columns={columns}
          dataSource={users}
          rowKey="id"
          loading={loading}
          pagination={{ 
            pageSize: 10, 
            showSizeChanger: true, 
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个用户`
          }}
          scroll={{ x: 800 }}
        />
      </Card>

      <Card className="mt-4 hover-lift" style={{ borderRadius: '16px' }}>
        <Row gutter={16} align="middle" className="mb-4">
          <Col>
            <Space>
              <KeyOutlined style={{ fontSize: '20px', color: '#6366f1' }} />
              <span className="text-lg font-semibold">邀请码管理</span>
            </Space>
          </Col>
          <Col flex="auto" />
          <Col>
            <Space>
              <InputNumber 
                min={1} 
                max={20} 
                value={generateCount} 
                onChange={(v) => setGenerateCount(v || 1)}
                style={{ width: 80 }}
              />
              <Button 
                type="primary" 
                icon={<PlusOutlined />}
                onClick={handleGenerateCodes}
              >
                生成邀请码
              </Button>
            </Space>
          </Col>
        </Row>
        <List
          grid={{ gutter: 12, xs: 1, sm: 2, md: 3, lg: 4 }}
          dataSource={invitationCodes}
          renderItem={(item) => (
            <List.Item>
              <Card 
                size="small" 
                className="text-center hover-lift"
                style={{ 
                  borderRadius: '12px',
                  background: item.is_used ? '#f3f4f6' : '#f0fdf4'
                }}
                bodyStyle={{ padding: '12px' }}
              >
                <div className="font-mono text-lg font-bold mb-1" style={{ color: item.is_used ? '#9ca3af' : '#10b981' }}>
                  {item.code}
                </div>
                <div className="text-xs text-gray-500">
                  {item.is_used ? '已使用' : '未使用'}
                </div>
                {!item.is_used && (
                  <Button 
                    type="link" 
                    size="small" 
                    icon={<CopyOutlined />}
                    onClick={() => handleCopyCode(item.code)}
                    className="mt-1"
                  >
                    复制
                  </Button>
                )}
              </Card>
            </List.Item>
          )}
          locale={{ emptyText: '暂无邀请码，点击上方按钮生成' }}
        />
      </Card>

      <Modal
        title={
          <Space>
            <Avatar style={{ backgroundColor: '#6366f1' }} icon={<UserOutlined />} />
            <span>用户详情</span>
          </Space>
        }
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
          <>
            <Card size="small" className="mb-4" style={{ background: '#f9fafb', borderRadius: '12px' }}>
              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="用户ID">{selectedUser.id}</Descriptions.Item>
                <Descriptions.Item label="用户名">{selectedUser.username}</Descriptions.Item>
                <Descriptions.Item label="邮箱">{selectedUser.email}</Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Badge status={selectedUser.is_active ? 'success' : 'error'} text={selectedUser.is_active ? '正常' : '已禁用'} />
                </Descriptions.Item>
                <Descriptions.Item label="角色">
                  {selectedUser.is_admin ? <Tag color="gold">管理员</Tag> : <Tag color="default">普通用户</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="注册时间">
                  {new Date(selectedUser.created_at).toLocaleString('zh-CN')}
                </Descriptions.Item>
                <Descriptions.Item label="操作">
                  <Button 
                    size="small" 
                    icon={<EditOutlined />}
                    onClick={() => openResetPassword(selectedUser)}
                  >
                    重置密码
                  </Button>
                </Descriptions.Item>
              </Descriptions>
            </Card>
            
            {userStats && (
              <Row gutter={[12, 12]}>
                <Col span={6}>
                  <Card size="small" className="text-center" style={{ borderRadius: '12px' }}>
                    <ProjectOutlined style={{ fontSize: '24px', color: '#6366f1' }} />
                    <div className="text-2xl font-bold mt-2" style={{ color: '#6366f1' }}>{userStats.total_projects}</div>
                    <div className="text-gray-500 text-sm">项目数</div>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card size="small" className="text-center" style={{ borderRadius: '12px' }}>
                    <VideoCameraOutlined style={{ fontSize: '24px', color: '#8b5cf6' }} />
                    <div className="text-2xl font-bold mt-2" style={{ color: '#8b5cf6' }}>{userStats.total_tasks}</div>
                    <div className="text-gray-500 text-sm">任务数</div>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card size="small" className="text-center" style={{ borderRadius: '12px' }}>
                    <CheckCircleOutlined style={{ fontSize: '24px', color: '#10b981' }} />
                    <div className="text-2xl font-bold mt-2" style={{ color: '#10b981' }}>{userStats.completed_tasks}</div>
                    <div className="text-gray-500 text-sm">成功</div>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card size="small" className="text-center" style={{ borderRadius: '12px' }}>
                    <CloseCircleOutlined style={{ fontSize: '24px', color: '#ef4444' }} />
                    <div className="text-2xl font-bold mt-2" style={{ color: '#ef4444' }}>{userStats.failed_tasks}</div>
                    <div className="text-gray-500 text-sm">失败</div>
                  </Card>
                </Col>
              </Row>
            )}
          </>
        )}
      </Modal>

      <Modal
        title="重置密码"
        open={resetPasswordModalVisible}
        onCancel={() => {
          setResetPasswordModalVisible(false)
          setNewPassword('')
        }}
        onOk={handleResetPassword}
        confirmLoading={resetLoading}
        okText="确认重置"
        cancelText="取消"
      >
        <div className="py-4">
          <p className="mb-4">为用户 <strong>{selectedUser?.username}</strong> 设置新密码：</p>
          <Input.Password
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="输入新密码"
            minLength={8}
          />
          <p className="text-xs text-gray-500 mt-2">密码至少8位，需包含字母和数字</p>
        </div>
      </Modal>
    </div>
  )
}
