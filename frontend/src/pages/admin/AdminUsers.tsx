import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Table, Card, Input, Button, Space, Tag, Popconfirm,
  Modal, message, Row, Col, Avatar, Badge, Radio, InputNumber
} from 'antd'
import {
  ReloadOutlined, DeleteOutlined, SearchOutlined,
  LockOutlined, UnlockOutlined, EyeOutlined, UserOutlined,
  CheckCircleOutlined, CloseCircleOutlined,
  ClockCircleOutlined, VideoCameraOutlined
} from '@ant-design/icons'
import { adminApi, User } from '../../services/admin'

const formatDateTime = (dateStr: string | null | undefined, showTime: boolean = true) => {
    if (!dateStr) return '-'
    try {
      const date = new Date(dateStr.endsWith('Z') ? dateStr : dateStr + 'Z')
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      const hours = String(date.getHours()).padStart(2, '0')
      const minutes = String(date.getMinutes()).padStart(2, '0')
      const seconds = String(date.getSeconds()).padStart(2, '0')
      if (showTime) {
        return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
      }
      return `${year}-${month}-${day}`
    } catch {
      return '-'
    }
  }

export default function AdminUsers() {
  const navigate = useNavigate()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [durationModalVisible, setDurationModalVisible] = useState(false)
  const [durationUser, setDurationUser] = useState<User | null>(null)
  const [durationType, setDurationType] = useState<string>('1m')
  const [customDays, setCustomDays] = useState<number>(30)
  const [durationLoading, setDurationLoading] = useState(false)
  const [videoLimitModalVisible, setVideoLimitModalVisible] = useState(false)
  const [videoLimitUser, setVideoLimitUser] = useState<User | null>(null)
  const [videoLimitValue, setVideoLimitValue] = useState<number>(5)
  const [videoLimitLoading, setVideoLimitLoading] = useState(false)

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

  const handleApproveUser = (user: User) => {
    setDurationUser(user)
    setDurationType('1m')
    setCustomDays(30)
    setDurationModalVisible(true)
  }

  const handleRejectUser = async (userId: number) => {
    try {
      await adminApi.rejectUser(userId)
      message.success('用户已拒绝')
      fetchUsers()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '操作失败')
    }
  }

  const handleExtendUser = (user: User) => {
    setDurationUser(user)
    setDurationType('1m')
    setCustomDays(30)
    setDurationModalVisible(true)
  }

  const getDurationDays = (type: string): number => {
    switch (type) {
      case '30min': return 30 / 1440
      case '1h': return 60 / 1440
      case '1w': return 7
      case '1m': return 30
      case '3m': return 90
      case '6m': return 180
      case '1y': return 365
      case 'custom': return customDays
      default: return 30
    }
  }

  const handleSetDuration = async () => {
    if (!durationUser) return
    setDurationLoading(true)
    try {
      const days = getDurationDays(durationType)
      if (!durationUser.is_approved) {
        await adminApi.approveUser(durationUser.id)
      }
      await adminApi.extendUser(durationUser.id, days)
      message.success(`已设置有效期 ${days} 天`)
      setDurationModalVisible(false)
      fetchUsers()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '操作失败')
    } finally {
      setDurationLoading(false)
    }
  }

  const handleVideoLimitUser = (user: User) => {
    setVideoLimitUser(user)
    setVideoLimitValue(user.daily_video_limit || 5)
    setVideoLimitModalVisible(true)
  }

  const handleSetVideoLimit = async () => {
    if (!videoLimitUser) return
    setVideoLimitLoading(true)
    try {
      await adminApi.setVideoLimit(videoLimitUser.id, videoLimitValue)
      message.success(`已设置每日配额为 ${videoLimitValue} 条`)
      setVideoLimitModalVisible(false)
      fetchUsers()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '操作失败')
    } finally {
      setVideoLimitLoading(false)
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
      title: '审核',
      dataIndex: 'is_approved',
      key: 'is_approved',
      width: 100,
      render: (isApproved: boolean) => (
        isApproved 
          ? <Tag color="green">已通过</Tag>
          : <Tag color="orange">待审核</Tag>
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
      title: '每日配额',
      dataIndex: 'daily_video_limit',
      key: 'daily_video_limit',
      width: 100,
      render: (limit: number | undefined, record: User) => (
        record.is_admin 
          ? <Tag color="blue">无限制</Tag>
          : <span>{limit || 5} 条/天</span>
      ),
    },
    {
      title: '有效期',
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 170,
      render: (expiresAt: string) => formatDateTime(expiresAt),
    },
    {
      title: '注册时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => formatDateTime(date),
    },
    {
      title: '操作',
      key: 'action',
      width: 320,
      render: (_: any, record: User) => (
        <Space wrap>
          {!record.is_approved && (
            <>
              <Button
                type="primary"
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={() => handleApproveUser(record)}
              >
                通过
              </Button>
              <Button
                danger
                size="small"
                icon={<CloseCircleOutlined />}
                onClick={() => handleRejectUser(record.id)}
              >
                拒绝
              </Button>
            </>
          )}
          {record.is_approved && (
            <Button
              size="small"
              icon={<ClockCircleOutlined />}
              onClick={() => handleExtendUser(record)}
            >
              设置时长
            </Button>
          )}
          {record.is_approved && !record.is_admin && (
            <Button
              size="small"
              icon={<VideoCameraOutlined />}
              onClick={() => handleVideoLimitUser(record)}
            >
              配额
            </Button>
          )}
          <Button 
            type="primary" 
            ghost
            size="small"
            icon={<EyeOutlined />} 
            onClick={() => navigate(`/admin/users/${record.id}`)}
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

      <Modal
        title={durationUser?.is_approved ? "设置使用时长" : "审核通过并设置时长"}
        open={durationModalVisible}
        onCancel={() => setDurationModalVisible(false)}
        onOk={handleSetDuration}
        confirmLoading={durationLoading}
        okText="确认"
        cancelText="取消"
      >
        <div className="py-4">
          <p className="mb-4">为用户 <strong>{durationUser?.username}</strong> 设置账号有效期：</p>
          <Radio.Group 
            value={durationType} 
            onChange={(e) => setDurationType(e.target.value)}
            className="w-full"
          >
            <Space direction="vertical" className="w-full">
              <Radio value="30min">30 分钟</Radio>
              <Radio value="1h">1 小时</Radio>
              <Radio value="1w">1 周</Radio>
              <Radio value="1m">1 个月（推荐）</Radio>
              <Radio value="3m">3 个月</Radio>
              <Radio value="6m">6 个月</Radio>
              <Radio value="1y">1 年</Radio>
              <Radio value="custom">自定义天数</Radio>
            </Space>
          </Radio.Group>
          {durationType === 'custom' && (
            <div className="mt-4">
              <InputNumber
                value={customDays}
                onChange={(v: number | null) => setCustomDays(v || 1)}
                min={1}
                max={3650}
                addonAfter="天"
                style={{ width: '100%' }}
              />
            </div>
          )}
          {durationUser?.expires_at && (
            <p className="text-xs text-gray-500 mt-4">
              当前有效期至：{formatDateTime(durationUser.expires_at, false)}
            </p>
          )}
        </div>
      </Modal>

      <Modal
        title="设置每日视频配额"
        open={videoLimitModalVisible}
        onCancel={() => setVideoLimitModalVisible(false)}
        onOk={handleSetVideoLimit}
        confirmLoading={videoLimitLoading}
        okText="确认"
        cancelText="取消"
      >
        <div className="py-4">
          <p className="mb-4">为用户 <strong>{videoLimitUser?.username}</strong> 设置每日视频生成配额：</p>
          <InputNumber
            value={videoLimitValue}
            onChange={(v: number | null) => setVideoLimitValue(v || 5)}
            min={5}
            max={20}
            addonAfter="条/天"
            style={{ width: '100%' }}
          />
          <p className="text-xs text-gray-500 mt-2">
            配额范围：5-20 条/天
          </p>
        </div>
      </Modal>
    </div>
  )
}
