import { useState, useEffect, useMemo } from 'react'
import {
  Table, Card, Input, Button, Space, Tag, Popconfirm,
  Modal, Descriptions, message, Row, Col, Avatar, Badge, Radio, InputNumber, Statistic, Switch, Select
} from 'antd'
import {
  ReloadOutlined, DeleteOutlined, SearchOutlined,
  LockOutlined, UnlockOutlined, EyeOutlined, UserOutlined,
  ProjectOutlined, CheckCircleOutlined, CloseCircleOutlined,
  EditOutlined, ClockCircleOutlined, TeamOutlined, CrownOutlined, HourglassOutlined, SettingOutlined
} from '@ant-design/icons'
import { adminApi, User, UserStats } from '../../services/admin'
import { useIsMobile } from '@/hooks/useIsMobile'

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
  const isMobile = useIsMobile()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [userStats, setUserStats] = useState<UserStats | null>(null)
  const [resetPasswordModalVisible, setResetPasswordModalVisible] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [resetLoading, setResetLoading] = useState(false)
  const [durationModalVisible, setDurationModalVisible] = useState(false)
  const [durationUser, setDurationUser] = useState<User | null>(null)
  const [durationType, setDurationType] = useState<string>('1m')
  const [customDays, setCustomDays] = useState<number>(30)
  const [durationLoading, setDurationLoading] = useState(false)
  const [videoLimitModalVisible, setVideoLimitModalVisible] = useState(false)
  const [videoLimitUser, setVideoLimitUser] = useState<User | null>(null)
  const [videoLimitValue, setVideoLimitValue] = useState<number>(5)
  const [videoLimitLoading, setVideoLimitLoading] = useState(false)
  const [batchFrontendVersion, setBatchFrontendVersion] = useState<'legacy' | 'v2'>('v2')
  const [batchVersionLoading, setBatchVersionLoading] = useState(false)
  const [batchVisualLimitModalVisible, setBatchVisualLimitModalVisible] = useState(false)
  const [batchVisualLimitValue, setBatchVisualLimitValue] = useState<number>(5)
  const [batchVisualLimitLoading, setBatchVisualLimitLoading] = useState(false)
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([])
  const [permissionModalVisible, setPermissionModalVisible] = useState(false)
  const [permissionUser, setPermissionUser] = useState<User | null>(null)
  const [permissionDraft, setPermissionDraft] = useState<Record<string, any>>({})
  const [permissionLoading, setPermissionLoading] = useState(false)
  const [batchPermissionModalVisible, setBatchPermissionModalVisible] = useState(false)
  const [batchPermissionApply, setBatchPermissionApply] = useState<Record<string, boolean>>({ visual: false, stickman_legacy: false, stickman_v2: false, explainer: false, article: false })
  const selectableUserKeys = useMemo(() => users.filter((user) => !user.is_admin).map((user) => user.id), [users])

  const getVisualLimitValue = (user?: User | null) => {
    const visualLimit = user?.module_permissions?.visual?.daily_limit
    if (typeof visualLimit === 'number' && visualLimit > 0) return visualLimit
    return user?.daily_video_limit || 5
  }

  const defaultPermissions = (user?: User | null) => user?.module_permissions || {
    visual: { enabled: true, daily_limit: getVisualLimitValue(user), used_today: 0, period: 'daily' },
    stickman_legacy: { enabled: false, daily_limit: 30, used_today: 0, period: 'monthly' },
    stickman_v2: { enabled: false, daily_limit: 30, used_today: 0, period: 'monthly' },
    explainer: { enabled: false, daily_limit: 30, used_today: 0, period: 'monthly' },
    article: { enabled: false, daily_limit: 45, used_today: 0, period: 'monthly' },
  }

  const permissionTemplates: Record<string, Record<string, any>> = {
    article_only: {
      visual: { enabled: false, daily_limit: 0, period: 'daily' },
      stickman_legacy: { enabled: false, daily_limit: 0, period: 'monthly' },
      stickman_v2: { enabled: false, daily_limit: 0, period: 'monthly' },
      explainer: { enabled: false, daily_limit: 0, period: 'monthly' },
      article: { enabled: true, daily_limit: 45, period: 'monthly' },
    },
    video_only: {
      visual: { enabled: true, daily_limit: 5, period: 'daily' },
      stickman_legacy: { enabled: true, daily_limit: 30, period: 'monthly' },
      stickman_v2: { enabled: true, daily_limit: 30, period: 'monthly' },
      explainer: { enabled: true, daily_limit: 30, period: 'monthly' },
      article: { enabled: false, daily_limit: 0, period: 'monthly' },
    },
    all_enabled: {
      visual: { enabled: true, daily_limit: 8, period: 'daily' },
      stickman_legacy: { enabled: true, daily_limit: 30, period: 'monthly' },
      stickman_v2: { enabled: true, daily_limit: 30, period: 'monthly' },
      explainer: { enabled: true, daily_limit: 30, period: 'monthly' },
      article: { enabled: true, daily_limit: 45, period: 'monthly' },
    },
    trial: {
      visual: { enabled: true, daily_limit: 2, period: 'daily' },
      stickman_legacy: { enabled: true, daily_limit: 2, period: 'monthly' },
      stickman_v2: { enabled: true, daily_limit: 2, period: 'monthly' },
      explainer: { enabled: true, daily_limit: 2, period: 'monthly' },
      article: { enabled: true, daily_limit: 2, period: 'monthly' },
    },
    enterprise: {
      visual: { enabled: true, daily_limit: 50, period: 'daily' },
      stickman_legacy: { enabled: true, daily_limit: 30, period: 'monthly' },
      stickman_v2: { enabled: true, daily_limit: 30, period: 'monthly' },
      explainer: { enabled: true, daily_limit: 30, period: 'monthly' },
      article: { enabled: true, daily_limit: 45, period: 'monthly' },
    },
  }

  const applyPermissionTemplate = (templateKey: keyof typeof permissionTemplates) => {
    const template = permissionTemplates[templateKey]
    setPermissionDraft((prev) => {
      const next = { ...prev }
      Object.entries(template).forEach(([moduleKey, value]) => {
        next[moduleKey] = { ...(next[moduleKey] || {}), ...value }
      })
      return next
    })
    if (batchPermissionModalVisible) {
      setBatchPermissionApply((prev) => {
        const next = { ...prev }
        Object.keys(template).forEach((moduleKey) => {
          next[moduleKey] = true
        })
        return next
      })
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  useEffect(() => {
    setSelectedRowKeys((prev) => prev.filter((key) => selectableUserKeys.includes(key)))
  }, [selectableUserKeys])

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
      const payload: any = res.data
      setUsers(Array.isArray(payload) ? payload : (payload?.users || []))
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

  const handleFrontendVersionChange = async (userId: number, frontendVersion: 'legacy' | 'v2') => {
    try {
      await adminApi.updateUser(userId, { frontend_version: frontendVersion })
      message.success(`已切换为${frontendVersion === 'v2' ? '新版本' : '老版本'}`)
      fetchUsers()
      if (selectedUser?.id === userId) {
        const detailRes = await adminApi.getUserDetail(userId)
        setSelectedUser(detailRes.data)
      }
    } catch (err: any) {
      message.error(err.response?.data?.detail || '切换版本失败')
    }
  }

  const handleBatchFrontendVersionChange = async () => {
    if (!selectedRowKeys.length) return
    setBatchVersionLoading(true)
    try {
      const res = await adminApi.batchUpdateFrontendVersion(selectedRowKeys as number[], batchFrontendVersion)
      message.success(res.data.message || `已批量切换为${batchFrontendVersion === 'v2' ? '新版本' : '老版本'}`)
      fetchUsers()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '批量切换版本失败')
    } finally {
      setBatchVersionLoading(false)
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
      case '30m': return 0.0208
      case '1h': return 0.0417
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

  const handleViewUser = async (user: User) => {
    setSelectedUser(user)
    try {
      const [statsRes, detailRes] = await Promise.all([
        adminApi.getUserStats(user.id),
        adminApi.getUserDetail(user.id),
      ])
      setUserStats(statsRes.data)
      setSelectedUser(detailRes.data)
    } catch (err) {
      setUserStats(null)
    }
  }

  const getPermissionTag = (record: User, moduleKey: 'visual' | 'stickman_legacy' | 'stickman_v2' | 'explainer' | 'article') => {
    const permission: any = defaultPermissions(record)[moduleKey]
    const labelMap = {
      visual: '思维可视化',
      stickman_legacy: '标准讲解',
      stickman_v2: '增强讲解',
      explainer: '讲解视频',
      article: '公众号',
    }
    const colorMap = {
      visual: 'green',
      stickman_legacy: 'orange',
      stickman_v2: 'gold',
      explainer: 'blue',
      article: 'purple',
    } as const
    const period = permission?.period || (moduleKey === 'visual' ? 'daily' : 'monthly')
    const label = period === 'monthly' ? '本月' : '今日'
    if (record.is_admin) return <Tag color="blue">{labelMap[moduleKey]}: 无限</Tag>
    if (!permission?.enabled) return <Tag>{labelMap[moduleKey]}: 关闭</Tag>
    return <Tag color={colorMap[moduleKey]}>{labelMap[moduleKey]}: {label} {permission.used_today || 0}/{permission.daily_limit}</Tag>
  }

  const renderUserActions = (record: User, compact = false) => (
    <Space wrap size={compact ? 4 : 8}>
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
        <Button size="small" icon={<ClockCircleOutlined />} onClick={() => handleExtendUser(record)}>
          时长
        </Button>
      )}
      {record.is_approved && !record.is_admin && (
        <Button size="small" icon={<SettingOutlined />} onClick={() => handleVideoLimitUser(record)}>
          配额
        </Button>
      )}
      <Button size="small" icon={<SettingOutlined />} onClick={() => openPermissionModal(record)}>
        权限
      </Button>
      <Button type="primary" ghost size="small" icon={<EyeOutlined />} onClick={() => handleViewUser(record)}>
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
  )

  const handleVideoLimitUser = (user: User) => {
    setVideoLimitUser(user)
    setVideoLimitValue(getVisualLimitValue(user))
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

  const handleBatchSetVisualLimit = async () => {
    if (!selectedRowKeys.length) return
    setBatchVisualLimitLoading(true)
    try {
      const res = await adminApi.batchSetVisualLimit(selectedRowKeys as number[], batchVisualLimitValue)
      message.success(res.data.message || `已批量设置每日配额为 ${batchVisualLimitValue} 条`)
      setBatchVisualLimitModalVisible(false)
      fetchUsers()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '批量设置失败')
    } finally {
      setBatchVisualLimitLoading(false)
    }
  }

  const openPermissionModal = (user: User) => {
    setPermissionUser(user)
    setPermissionDraft(defaultPermissions(user))
    setPermissionModalVisible(true)
  }

  const updatePermissionDraft = (moduleKey: string, patch: Record<string, any>) => {
    setPermissionDraft((prev) => ({
      ...prev,
      [moduleKey]: { ...(prev[moduleKey] || {}), ...patch },
    }))
  }

  const updateBatchPermissionApply = (moduleKey: string, checked: boolean) => {
    setBatchPermissionApply((prev) => ({
      ...prev,
      [moduleKey]: checked,
    }))
  }

  const handleSavePermissions = async () => {
    if (!permissionUser) return
    setPermissionLoading(true)
    try {
      await adminApi.updateUserModulePermissions(permissionUser.id, permissionDraft)
      message.success('模块权限已更新')
      setPermissionModalVisible(false)
      fetchUsers()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '更新失败')
    } finally {
      setPermissionLoading(false)
    }
  }

  const handleBatchPermissions = async () => {
    if (!selectedRowKeys.length) return
    const selectedModules = Object.entries(permissionDraft).reduce<Record<string, any>>((acc, [moduleKey, value]) => {
      if (batchPermissionApply[moduleKey]) {
        acc[moduleKey] = value
      }
      return acc
    }, {})
    if (!Object.keys(selectedModules).length) {
      message.warning('请至少选择一个要应用的模块')
      return
    }
    setPermissionLoading(true)
    try {
      await adminApi.batchUpdateUserModulePermissions(selectedRowKeys as number[], selectedModules)
      message.success('批量模块权限已更新')
      setBatchPermissionModalVisible(false)
      fetchUsers()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '批量更新失败')
    } finally {
      setPermissionLoading(false)
    }
  }

  const userStatsSummary = useMemo(() => {
    const total = users.length
    const active = users.filter(u => u.is_active).length
    const pending = users.filter(u => !u.is_approved).length
    const admins = users.filter(u => u.is_admin).length
    return { total, active, pending, admins }
  }, [users])

  const columns = [
    {
      title: '用户',
      key: 'user',
      width: 220,
      render: (_: any, record: User) => (
        <div className="flex items-center gap-3">
          <Avatar 
            style={{ backgroundColor: record.is_admin ? '#f59e0b' : '#6366f1' }}
            icon={record.is_admin ? <UserOutlined /> : <UserOutlined />}
            size={40}
          />
            <div>
              <div className="font-medium">{record.username}</div>
              <div className="text-gray-500 text-sm">{record.phone || record.email}</div>
            </div>
        </div>
      ),
    },
    {
      title: '账号状态',
      key: 'account_state',
      width: 190,
      render: (_: any, record: User) => (
        <Space size={[4, 6]} wrap>
          <Badge status={record.is_active ? 'success' : 'error'} text={record.is_active ? '正常' : '已禁用'} />
          {record.is_approved ? <Tag color="green">已通过</Tag> : <Tag color="orange">待审核</Tag>}
          {record.is_admin ? <Tag color="gold">管理员</Tag> : <Tag color="default">用户</Tag>}
        </Space>
      ),
    },
    {
      title: '使用配置',
      key: 'usage_config',
      width: 230,
      render: (_: any, record: User) => (
        <div>
          <div className="mb-2">
            <Select
              size="small"
              style={{ width: 110 }}
              value={record.frontend_version || 'legacy'}
              onChange={(value) => handleFrontendVersionChange(record.id, value as 'legacy' | 'v2')}
              options={[
                { label: '老版本', value: 'legacy' },
                { label: '新版本', value: 'v2' },
              ]}
            />
          </div>
          <Space size={[4, 6]} wrap>
            {getPermissionTag(record, 'visual')}
            {getPermissionTag(record, 'stickman_legacy')}
            {getPermissionTag(record, 'stickman_v2')}
            {getPermissionTag(record, 'explainer')}
            {getPermissionTag(record, 'article')}
          </Space>
        </div>
      ),
    },
    {
      title: '时间信息',
      key: 'time_info',
      width: 200,
      render: (_: any, record: User) => (
        <div className="text-sm leading-6">
          <div><span className="text-gray-500">有效期：</span>{formatDateTime(record.expires_at)}</div>
          <div><span className="text-gray-500">注册时间：</span>{formatDateTime(record.created_at)}</div>
        </div>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 260,
      render: (_: any, record: User) => renderUserActions(record),
    },
  ]

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold">用户管理</h2>
        <p className="text-gray-500 mt-1">管理平台用户账户</p>
      </div>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card className="hover-lift" style={{ borderRadius: '12px' }}>
            <Statistic
              title="用户总数"
              value={userStatsSummary.total}
              prefix={<TeamOutlined className="text-blue-500" />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="hover-lift" style={{ borderRadius: '12px' }}>
            <Statistic
              title="活跃用户"
              value={userStatsSummary.active}
              prefix={<CheckCircleOutlined className="text-green-500" />}
              valueStyle={{ color: '#10b981' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="hover-lift" style={{ borderRadius: '12px' }}>
            <Statistic
              title="待审核"
              value={userStatsSummary.pending}
              prefix={<HourglassOutlined className="text-orange-500" />}
              valueStyle={{ color: '#f59e0b' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="hover-lift" style={{ borderRadius: '12px' }}>
            <Statistic
              title="管理员"
              value={userStatsSummary.admins}
              prefix={<CrownOutlined className="text-purple-500" />}
              valueStyle={{ color: '#8b5cf6' }}
            />
          </Card>
        </Col>
      </Row>

      <Card className="mb-4 hover-lift" style={{ borderRadius: '16px' }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Input.Search
              placeholder="搜索用户名、手机号或邮箱..."
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
          <Col>
            <Space>
              <Button onClick={() => setSelectedRowKeys(selectableUserKeys)} disabled={!selectableUserKeys.length}>
                全选普通用户
              </Button>
              <Button onClick={() => setSelectedRowKeys([])} disabled={!selectedRowKeys.length}>
                清空选择
              </Button>
            </Space>
          </Col>
          <Col>
          <Button
              icon={<TeamOutlined />}
              disabled={!selectedRowKeys.length}
              onClick={() => {
                setPermissionDraft(defaultPermissions(null))
                setBatchPermissionApply({ visual: false, stickman_legacy: false, stickman_v2: false, explainer: false, article: false })
                setBatchPermissionModalVisible(true)
              }}
            >
              批量模块权限
            </Button>
          </Col>
          <Col>
            <Space.Compact>
              <Select
                value={batchFrontendVersion}
                onChange={(value) => setBatchFrontendVersion(value as 'legacy' | 'v2')}
                style={{ width: 120 }}
                disabled={!selectedRowKeys.length}
                options={[
                  { label: '切到老版本', value: 'legacy' },
                  { label: '切到新版本', value: 'v2' },
                ]}
              />
              <Button loading={batchVersionLoading} disabled={!selectedRowKeys.length} onClick={handleBatchFrontendVersionChange}>
                批量切版本
              </Button>
            </Space.Compact>
          </Col>
          <Col>
            <Button disabled={!selectedRowKeys.length} onClick={() => setBatchVisualLimitModalVisible(true)}>
              批量思维配额
            </Button>
          </Col>
        </Row>
      </Card>

      <Card className="hover-lift" style={{ borderRadius: '16px' }}>
        {isMobile ? (
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            {users.map((record) => (
              <Card key={record.id} size="small" style={{ borderRadius: '12px' }}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <Avatar style={{ backgroundColor: record.is_admin ? '#f59e0b' : '#6366f1' }} icon={<UserOutlined />} size={40} />
                    <div className="min-w-0">
                      <div className="font-medium truncate">{record.username}</div>
                      <div className="text-gray-500 text-sm break-all">{record.phone || record.email}</div>
                    </div>
                  </div>
                  <Tag color={record.is_admin ? 'gold' : 'default'}>{record.is_admin ? '管理员' : '用户'}</Tag>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge status={record.is_active ? 'success' : 'error'} text={record.is_active ? '正常' : '已禁用'} />
                  {record.is_approved ? <Tag color="green">已通过</Tag> : <Tag color="orange">待审核</Tag>}
                  <Select
                    size="small"
                    style={{ width: 108 }}
                    value={record.frontend_version || 'legacy'}
                    onChange={(value) => handleFrontendVersionChange(record.id, value as 'legacy' | 'v2')}
                    options={[
                      { label: '老版本', value: 'legacy' },
                      { label: '新版本', value: 'v2' },
                    ]}
                  />
                </div>
                <div className="mt-3 text-sm text-gray-600 space-y-1">
                  <div>有效期：{formatDateTime(record.expires_at)}</div>
                  <div>注册时间：{formatDateTime(record.created_at)}</div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {getPermissionTag(record, 'visual')}
                  {getPermissionTag(record, 'stickman_legacy')}
                  {getPermissionTag(record, 'stickman_v2')}
                  {getPermissionTag(record, 'explainer')}
                  {getPermissionTag(record, 'article')}
                </div>
                <div className="mt-3">
                  {renderUserActions(record, true)}
                </div>
              </Card>
            ))}
            {!users.length && !loading && <div className="text-center text-gray-400 py-8">暂无用户</div>}
          </Space>
        ) : (
          <Table
            columns={columns}
            dataSource={users}
            rowKey="id"
            rowSelection={{
              selectedRowKeys,
              onChange: (keys) => setSelectedRowKeys((keys as number[]).filter((key) => selectableUserKeys.includes(key))),
              getCheckboxProps: (record) => ({ disabled: !!record.is_admin }),
              selections: [
                {
                  key: 'select-all-normal-users',
                  text: '全选普通用户',
                  onSelect: () => setSelectedRowKeys(selectableUserKeys),
                },
                {
                  key: 'clear-all',
                  text: '清空选择',
                  onSelect: () => setSelectedRowKeys([]),
                },
              ],
            }}
            loading={loading}
            pagination={{ 
              pageSize: 10, 
              showSizeChanger: true, 
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 个用户`
            }}
          />
        )}
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
                <Descriptions.Item label="手机号">{selectedUser.phone || '-'}</Descriptions.Item>
                <Descriptions.Item label="邮箱">{selectedUser.email}</Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Badge status={selectedUser.is_active ? 'success' : 'error'} text={selectedUser.is_active ? '正常' : '已禁用'} />
                </Descriptions.Item>
                <Descriptions.Item label="角色">
                  {selectedUser.is_admin ? <Tag color="gold">管理员</Tag> : <Tag color="default">普通用户</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="前端版本">
                  <Tag color={(selectedUser.frontend_version || 'legacy') === 'v2' ? 'green' : 'default'}>
                    {(selectedUser.frontend_version || 'legacy') === 'v2' ? '新版本' : '老版本'}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="注册时间">
                  {new Date(selectedUser.created_at).toLocaleString('zh-CN')}
                </Descriptions.Item>
                <Descriptions.Item label="模块权限">
                  <Space wrap>
                    {Object.entries(selectedUser.module_permissions || {}).map(([moduleKey, permission]) => {
                       const labels: Record<string, string> = { visual: '思维可视化', stickman_legacy: '标准讲解', stickman_v2: '增强讲解', explainer: '讲解型视频', article: '公众号文章' }
                      return (
                        <Tag key={moduleKey} color={permission.enabled ? 'green' : 'default'}>
                          {labels[moduleKey] || moduleKey}: {permission.enabled ? `${permission.used_today || 0}/${permission.daily_limit}` : '关闭'}
                        </Tag>
                      )
                    })}
                  </Space>
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
                    <div className="text-gray-500 text-sm">视频项目</div>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card size="small" className="text-center" style={{ borderRadius: '12px' }}>
                    <EditOutlined style={{ fontSize: '24px', color: '#8b5cf6' }} />
                    <div className="text-2xl font-bold mt-2" style={{ color: '#8b5cf6' }}>{selectedUser.total_articles || 0}</div>
                    <div className="text-gray-500 text-sm">公众号文章</div>
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

            <Row gutter={[12, 12]} className="mt-4">
              <Col span={12}>
                <Card size="small" title="最近视频作品" style={{ borderRadius: '12px' }}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {(selectedUser.recent_projects || []).length ? (selectedUser.recent_projects || []).map((project) => (
                      <div key={project.id} className="flex items-center justify-between">
                        <div>
                          <div className="font-medium">{project.title}</div>
                          <div className="text-xs text-gray-500">{project.status_text}</div>
                        </div>
                        <div className="text-xs text-gray-400">{formatDateTime(project.created_at, false)}</div>
                      </div>
                    )) : <div className="text-gray-400 text-sm">暂无视频作品</div>}
                  </Space>
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="最近公众号文章" style={{ borderRadius: '12px' }}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {(selectedUser.recent_articles || []).length ? (selectedUser.recent_articles || []).map((article) => (
                      <div key={article.id} className="flex items-center justify-between">
                        <div>
                          <div className="font-medium">{article.title}</div>
                          <div className="text-xs text-gray-500">{article.status_text}</div>
                        </div>
                        <div className="text-xs text-gray-400">{formatDateTime(article.created_at, false)}</div>
                      </div>
                    )) : <div className="text-gray-400 text-sm">暂无公众号文章</div>}
                  </Space>
                </Card>
              </Col>
            </Row>

            {selectedUser.latest_task && (
              <Card size="small" className="mt-4" title="最近任务日志" style={{ borderRadius: '12px' }}>
                <div className="font-medium mb-2">{selectedUser.latest_task.project_title}</div>
                <div className="text-sm text-gray-500 mb-2">状态：{selectedUser.latest_task.status}</div>
                {selectedUser.latest_task.error_message && <div className="text-red-500 text-sm mb-2">{selectedUser.latest_task.error_message}</div>}
                {selectedUser.latest_task.log && <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, maxHeight: 180, overflow: 'auto' }}>{selectedUser.latest_task.log}</pre>}
              </Card>
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
              <Radio value="30m">30 分钟</Radio>
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
            onChange={(v) => setVideoLimitValue(v || 5)}
            min={5}
            max={20}
            addonAfter="条/天"
            style={{ width: '100%' }}
          />
          <p className="text-xs text-gray-500 mt-2">配额范围：5-20 条/天</p>
        </div>
      </Modal>

      <Modal
        title={`批量设置每日思维可视化配额（已选 ${selectedRowKeys.length} 个用户）`}
        open={batchVisualLimitModalVisible}
        onCancel={() => setBatchVisualLimitModalVisible(false)}
        onOk={handleBatchSetVisualLimit}
        confirmLoading={batchVisualLimitLoading}
        okText="确认"
        cancelText="取消"
      >
        <div className="py-4">
          <InputNumber
            value={batchVisualLimitValue}
            onChange={(v) => setBatchVisualLimitValue(v || 5)}
            min={1}
            max={999}
            addonAfter="条/天"
            style={{ width: '100%' }}
          />
          <p className="text-xs text-gray-500 mt-2">批量设置时会自动跳过管理员账号。</p>
        </div>
      </Modal>

      <Modal
        title={`模块权限设置 - ${permissionUser?.username || ''}`}
        open={permissionModalVisible}
        onCancel={() => setPermissionModalVisible(false)}
        onOk={handleSavePermissions}
        confirmLoading={permissionLoading}
        width={720}
      >
        <div className="mb-4">
          <p className="text-gray-500 mb-2">快捷模板</p>
          <Space wrap>
            <Button onClick={() => applyPermissionTemplate('article_only')}>仅公众号</Button>
            <Button onClick={() => applyPermissionTemplate('video_only')}>仅视频</Button>
            <Button onClick={() => applyPermissionTemplate('all_enabled')}>三模块全开</Button>
            <Button onClick={() => applyPermissionTemplate('trial')}>体验版</Button>
            <Button type="primary" ghost onClick={() => applyPermissionTemplate('enterprise')}>企业版</Button>
          </Space>
        </div>
        <div className="mb-3 text-gray-500 text-sm">管理员账号默认无限制，批量设置时将自动跳过管理员。</div>
        {['visual', 'stickman_legacy', 'stickman_v2', 'explainer', 'article'].map((moduleKey) => {
          const labels: Record<string, string> = { visual: '思维可视化', stickman_legacy: '标准讲解', stickman_v2: '增强讲解', explainer: '讲解型视频', article: '公众号文章' }
          const current: any = permissionDraft[moduleKey] || { enabled: false, daily_limit: 0, used_today: 0, period: moduleKey === 'visual' ? 'daily' : 'monthly' }
          const period = current.period || (moduleKey === 'visual' ? 'daily' : 'monthly')
          return (
            <Card key={moduleKey} size="small" className="mb-3" title={labels[moduleKey]}>
              <Space align="center" wrap>
                <span>启用</span>
                <Switch checked={!!current.enabled} onChange={(checked) => updatePermissionDraft(moduleKey, { enabled: checked })} />
                <span>次数限制</span>
                <InputNumber min={0} max={999} value={current.daily_limit} onChange={(value) => updatePermissionDraft(moduleKey, { daily_limit: value || 0 })} />
                <span>周期</span>
                <Select
                  value={period}
                  onChange={(value: string) => updatePermissionDraft(moduleKey, { period: value })}
                  options={[
                    { label: '每日', value: 'daily' },
                    { label: '每月', value: 'monthly' },
                  ]}
                  style={{ width: 100 }}
                />
                <span>当前已用</span>
                <InputNumber min={0} max={999} value={current.used_today || 0} onChange={(value) => updatePermissionDraft(moduleKey, { used_today: value || 0 })} disabled />
              </Space>
            </Card>
          )
        })}
      </Modal>

      <Modal
        title={`批量模块权限设置（已选 ${selectedRowKeys.length} 个用户）`}
        open={batchPermissionModalVisible}
        onCancel={() => setBatchPermissionModalVisible(false)}
        onOk={handleBatchPermissions}
        confirmLoading={permissionLoading}
        width={720}
      >
        <div className="mb-4">
          <p className="text-gray-500 mb-2">批量套用模板</p>
          <Space wrap>
            <Button onClick={() => applyPermissionTemplate('article_only')}>仅公众号</Button>
            <Button onClick={() => applyPermissionTemplate('video_only')}>仅视频</Button>
            <Button onClick={() => applyPermissionTemplate('all_enabled')}>三模块全开</Button>
            <Button onClick={() => applyPermissionTemplate('trial')}>体验版</Button>
            <Button type="primary" ghost onClick={() => applyPermissionTemplate('enterprise')}>企业版</Button>
          </Space>
        </div>
        <div className="mb-3 text-gray-500 text-sm">批量设置时会自动排除管理员账号，仅作用于普通用户。仅修改本次勾选的模块，未勾选模块保持不变。</div>
        {['visual', 'stickman_legacy', 'stickman_v2', 'explainer', 'article'].map((moduleKey) => {
          const labels: Record<string, string> = { visual: '思维可视化', stickman_legacy: '标准讲解', stickman_v2: '增强讲解', explainer: '讲解型视频', article: '公众号文章' }
          const current: any = permissionDraft[moduleKey] || { enabled: true, daily_limit: moduleKey === 'article' ? 45 : moduleKey === 'explainer' || moduleKey === 'stickman_legacy' || moduleKey === 'stickman_v2' ? 30 : 5, period: moduleKey === 'visual' ? 'daily' : 'monthly' }
          const period = current.period || (moduleKey === 'visual' ? 'daily' : 'monthly')
          const applyThisModule = !!batchPermissionApply[moduleKey]
          return (
            <Card key={moduleKey} size="small" className="mb-3" title={labels[moduleKey]}>
              <Space align="center" wrap>
                <span>应用此模块</span>
                <Switch checked={applyThisModule} onChange={(checked) => updateBatchPermissionApply(moduleKey, checked)} />
                <span>启用</span>
                <Switch checked={!!current.enabled} onChange={(checked) => updatePermissionDraft(moduleKey, { enabled: checked })} disabled={!applyThisModule} />
                <span>次数限制</span>
                <InputNumber min={0} max={999} value={current.daily_limit} onChange={(value) => updatePermissionDraft(moduleKey, { daily_limit: value || 0 })} disabled={!applyThisModule} />
                <span>周期</span>
                <Select
                  value={period}
                  onChange={(value: string) => updatePermissionDraft(moduleKey, { period: value })}
                  options={[
                    { label: '每日', value: 'daily' },
                    { label: '每月', value: 'monthly' },
                  ]}
                  style={{ width: 100 }}
                  disabled={!applyThisModule}
                />
              </Space>
            </Card>
          )
        })}
      </Modal>
    </div>
  )
}
